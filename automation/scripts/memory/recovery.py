"""恢复只清理可证明已退出的写锁，不自动发布孤立提交、不删除历史。"""
import os
import uuid

from .errors import MemoryError
from .owners import resolve_owner
from .store import MemoryStore, process_identity, utc_now


def inspect(root, owner_id):
    store = MemoryStore(root)
    owner = resolve_owner(root, owner_id)
    snapshot = store.read_snapshot(owner)
    reachable = set()
    manifest = snapshot["manifest"]
    while manifest:
        cid = manifest["commit_id"]
        if cid in reachable:
            raise MemoryError("INTEGRITY_ERROR", "历史提交形成循环")
        reachable.add(cid)
        parent = manifest["parent_commit_id"]
        manifest = store._manifest(owner, parent, manifest["parent_manifest_hash"]) if parent else None
    lock_path = store.path(owner, "write.lock")
    lock_exists = lock_path.exists()
    lock = store.read_json(lock_path) if lock_exists else None
    state = "absent"
    if lock_exists:
        pid = lock.get("pid") if isinstance(lock, dict) else None
        if type(pid) is not int or pid <= 0 or lock.get("owner_id") != owner_id:
            state = "unknown"
        else:
            identity = process_identity(pid)
            original = lock.get("start_identity")
            if identity is None or (identity != "unknown" and original not in {None, "unknown"} and identity != original):
                state = "exited"
            else:
                state = "active_or_unknown"
    commits = store.path(owner, "commits")
    staging = store.path(owner, "staging")
    orphans = []
    if commits.exists():
        for path in sorted(commits.iterdir()):
            checked = store.path(owner, f"commits/{path.name}")
            if checked.is_dir() and path.name not in reachable:
                orphans.append(path.name)
    staged = []
    if staging.exists():
        for path in sorted(staging.iterdir()):
            checked = store.path(owner, f"staging/{path.name}")
            if checked.is_dir():
                staged.append(path.name)
    return {"owner_id": owner_id, "head": snapshot["head"], "lock": lock,
            "lock_state": state, "uncommitted_staging": staged,
            "unreachable_commits": orphans,
            "action": "inspect_only", "warnings": ["孤立提交不自动接入 HEAD；重试原 request_id 检查幂等结果"]}


def recover(root, owner_id, *, apply=False):
    """检查为默认动作；显式 apply 仅归档退出进程的锁并保留审计回执。

    不进行递归删除。未知进程身份需要人工或下一次已证明退出的证据。
    """
    if not apply:
        return inspect(root, owner_id)
    store = MemoryStore(root)
    owner = resolve_owner(root, owner_id)
    # Serialize recovery itself so two recoverers cannot move each other's newly
    # acquired writer lock after both observed the same stale predecessor.
    home = store.path(owner)
    if not home.exists():
        return {**inspect(root, owner_id), "action": "no_change"}
    guard = store.path(owner, "recovery.lock")
    # An OS advisory byte lock is released even after process termination. The
    # marker remains reusable, so recovery cannot strand another permanent lock.
    stream = guard.open("a+b")
    if guard.stat().st_size == 0:
        stream.write(b"0")
        stream.flush()
    stream.seek(0)
    try:
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        stream.close()
        raise MemoryError("LOCKED", "已有恢复操作；保留现场后重试") from exc
    try:
        return _recover_locked(root, owner_id)
    finally:
        stream.close()


def _recover_locked(root, owner_id):
    result = inspect(root, owner_id)
    if result["lock_state"] not in {"absent", "exited"}:
        raise MemoryError("LOCKED", "无法证明写锁原进程已退出", result)
    if result["lock_state"] == "absent":
        return {**result, "action": "no_change"}
    store = MemoryStore(root)
    owner = resolve_owner(root, owner_id)
    lock_path = store.path(owner, "write.lock")
    # Recheck both process and lock immediately before the single rename. Normal
    # writers cannot acquire this path until this proved-stale lock is moved.
    current = inspect(root, owner_id)
    if current["lock"] != result["lock"] or current["head"] != result["head"] or current["lock_state"] != "exited":
        raise MemoryError("LOCKED", "恢复检查期间锁或 HEAD 已变化")
    folder = store.path(owner, "recovery-receipts")
    folder.mkdir(exist_ok=True)
    recovery_id = str(uuid.uuid4())
    archive = store.path(owner, f"recovery-receipts/{recovery_id}.lock.json")
    os.rename(lock_path, archive)
    receipt = {**result, "action": "archived_exited_lock", "recovered_at": utc_now(),
               "reason": "操作系统进程状态证明原进程已退出或 PID 已复用",
               "lock_archive": archive.relative_to(store.root).as_posix()}
    store.write_json(store.path(owner, f"recovery-receipts/{recovery_id}.json"), receipt)
    return receipt
