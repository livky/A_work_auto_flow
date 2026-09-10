"""单 owner 不可变提交。HEAD 的原子替换是唯一可见性边界。

fsync 保证已写文件交给操作系统；本模块不承诺任意文件系统断电无损。
故障钩子和时钟仅供可信 Python 测试注入，CLI 不暴露这些能力。
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import uuid

from .contracts import canonical_hash, content_hash
from .errors import MemoryError
from .owners import safe_path, ensure_owner, _recheck_directory_cache


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def process_identity(pid):
    """返回进程启动标识；None 表示已证明退出，unknown 表示不能判断。

    Windows 使用创建时间区分 PID 复用。拒绝访问不等于进程不存在。
    """
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
        kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return None if ctypes.get_last_error() == 87 else "unknown"
        try:
            exit_code = wintypes.DWORD()
            if not kernel.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                return "unknown"
            if exit_code.value != 259:  # STILL_ACTIVE; an exited process object may still have open handles.
                return None
            times = [wintypes.FILETIME() for _ in range(4)]
            if not kernel.GetProcessTimes(handle, *(ctypes.byref(t) for t in times)):
                return "unknown"
            return str((times[0].dwHighDateTime << 32) | times[0].dwLowDateTime)
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        # Linux starttime is stable for the lifetime of a process. On another
        # platform an alive process remains locked even if no birth time exists.
        stat = Path(f"/proc/{pid}/stat")
        return stat.read_text().rsplit(")", 1)[1].split()[19] if stat.exists() else "unknown"
    except ProcessLookupError:
        return None
    except (OSError, ValueError, IndexError):
        return "unknown"


class MemoryStore:
    def __init__(self, root, *, clock=utc_now, id_factory=None, fault=None):
        self.root = Path(root).resolve()
        self.clock = clock
        self.id_factory = id_factory or (lambda: str(uuid.uuid4()))
        self.fault = fault or (lambda _point: None)

    def path(self, owner, relative="", *, _directory_cache=None):
        # Validate the combined relative locator once; validating the home and
        # then the full locator repeated every ancestor check for every record.
        locator = owner["memory_home"] + ("/" + str(relative) if relative else "")
        return safe_path(self.root, locator, _directory_cache=_directory_cache)

    def read_json(self, path):
        try:
            return json.loads(path.read_text(encoding="utf-8"),
                              parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
        except (OSError, ValueError, UnicodeError) as exc:
            raise MemoryError("INTEGRITY_ERROR", f"无法读取规范 JSON：{path}") from exc

    def write_json(self, path, value):
        """新文件独占创建，避免失误覆盖不可变修订或孤立事务。"""
        raw = encoded(value)
        with path.open("xb") as stream:
            stream.write(raw)
            self.fault("write")
            stream.flush()
            self.fault("flush")
            os.fsync(stream.fileno())

    def read_snapshot(self, owner):
        # This cache has exactly one read lifetime. It cannot leak between HTTP
        # requests, owner reads, or publication checks; links are checked on
        # each leaf lookup; shared parents are rechecked before returning data.
        directory_cache = {}
        head_path = self.path(owner, "HEAD.json", _directory_cache=directory_cache)
        if not head_path.exists():
            _recheck_directory_cache(directory_cache)
            return {"head": None, "manifest": None, "records": {}}
        head = self.read_json(head_path)
        if not isinstance(head, dict) or set(head) != {"commit_id", "generation", "manifest_hash"}:
            raise MemoryError("INTEGRITY_ERROR", "HEAD 结构损坏")
        manifest = self._manifest(owner, head["commit_id"], head["manifest_hash"], _directory_cache=directory_cache)
        if manifest.get("generation") != head["generation"] or manifest.get("owner_id") != owner["owner_id"]:
            raise MemoryError("INTEGRITY_ERROR", "HEAD 与 manifest 的归属或代次不一致")
        records = {rid: self._record(owner, rid, entry, _directory_cache=directory_cache) for rid, entry in manifest["record_heads"].items()}
        _recheck_directory_cache(directory_cache)
        return {"head": head, "manifest": manifest, "records": records}

    @staticmethod
    def _segment(value):
        # All persisted names are server-generated UUID-based IDs; accepting a
        # manifest path from a caller would turn an integrity check into a read API.
        if not isinstance(value, str) or not value or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in value):
            raise MemoryError("UNSAFE_PATH", "规范 ID 不能包含路径或特殊字符")
        return value

    def _manifest(self, owner, commit_id, expected_hash, *, _directory_cache=None):
        path = self.path(owner, f"commits/{self._segment(commit_id)}/manifest.json", _directory_cache=_directory_cache)
        value = self.read_json(path)
        if canonical_hash(value) != expected_hash:
            raise MemoryError("INTEGRITY_ERROR", "提交清单指纹不匹配", {"path": str(path)})
        required = {"schema_version", "commit_id", "generation", "owner_id", "record_heads", "request_ledger", "parent_commit_id", "parent_manifest_hash"}
        if not isinstance(value, dict) or not required <= value.keys() or value["schema_version"] != 1 or value["commit_id"] != commit_id:
            raise MemoryError("INTEGRITY_ERROR", "提交清单结构或版本不受支持")
        if (type(value["generation"]) is not int or value["generation"] < 1
                or not isinstance(value["record_heads"], dict) or not isinstance(value["request_ledger"], dict)
                or value["owner_id"] != owner["owner_id"]):
            raise MemoryError("INTEGRITY_ERROR", "提交清单字段类型或归属损坏")
        return value

    def _record(self, owner, rid, entry, *, _directory_cache=None):
        rid = self._segment(rid)
        if not isinstance(entry, dict) or not {"commit_id", "path", "revision", "record_hash"} <= entry.keys():
            raise MemoryError("INTEGRITY_ERROR", "记录头结构损坏")
        expected_path = f"commits/{self._segment(entry['commit_id'])}/records/{rid}.json"
        if entry.get("path") != expected_path:
            raise MemoryError("INTEGRITY_ERROR", "记录定位与身份不一致")
        value = self.read_json(self.path(owner, expected_path, _directory_cache=_directory_cache))
        from .contracts import CONTENT_FIELDS
        if not isinstance(value, dict) or not set(CONTENT_FIELDS) <= value.keys():
            raise MemoryError("INTEGRITY_ERROR", "记录正文结构损坏")
        if (value.get("record_id") != rid or value.get("owner_id") != owner["owner_id"]
                or value.get("revision") != entry["revision"] or value.get("record_hash") != entry["record_hash"]
                or canonical_hash({k: v for k, v in value.items() if k != "record_hash"}) != entry["record_hash"]
                or content_hash(value) != value.get("content_hash")):
            raise MemoryError("INTEGRITY_ERROR", "记录身份、版本或指纹不匹配", {"record_id": rid})
        return value

    def read_record(self, owner, record_id, revision=None):
        snapshot = self.read_snapshot(owner)
        manifest = snapshot["manifest"]
        visited = set()
        while manifest:
            if manifest["commit_id"] in visited:
                raise MemoryError("INTEGRITY_ERROR", "历史提交出现循环")
            visited.add(manifest["commit_id"])
            entry = manifest["record_heads"].get(record_id)
            if entry and (revision is None or entry["revision"] == revision):
                return self._record(owner, record_id, entry)
            parent = manifest["parent_commit_id"]
            manifest = self._manifest(owner, parent, manifest["parent_manifest_hash"]) if parent else None
        raise MemoryError("NOT_FOUND", "记录或指定修订不存在", {"record_id": record_id, "revision": revision})

    def read_history(self, owner, snapshot=None):
        """一次验证提交链，按固定身份收集各修订，避免逐修订重读当前快照。

        缓存仅限本次读取。每份 manifest 仍核对父指纹，每个唯一记录仍核对
        正文指纹；调用者负责在返回前核对 HEAD，不能把历史缓存当当前事实。
        """
        snapshot = snapshot or self.read_snapshot(owner)
        manifest, seen_commits, records = snapshot['manifest'], set(), {}
        directories = {}
        while manifest:
            cid = manifest['commit_id']
            if cid in seen_commits:
                raise MemoryError('INTEGRITY_ERROR', '历史提交出现循环')
            seen_commits.add(cid)
            for rid, entry in manifest['record_heads'].items():
                key = (rid, entry['revision'])
                if key not in records:
                    latest = snapshot['records'].get(rid)
                    records[key] = (latest if latest and latest['revision'] == entry['revision']
                                    else self._record(owner, rid, entry, _directory_cache=directories))
            parent = manifest['parent_commit_id']
            manifest = self._manifest(owner, parent, manifest['parent_manifest_hash'],
                                      _directory_cache=directories) if parent else None
        _recheck_directory_cache(directories)
        return list(records.values())

    def _receipt(self, owner, snapshot, request_id, request_hash):
        ledger = (snapshot["manifest"] or {}).get("request_ledger", {})
        entry = ledger.get(request_id)
        if entry:
            if not isinstance(entry, dict) or not {"commit_id", "receipt_hash", "request_hash"} <= entry.keys():
                raise MemoryError("INTEGRITY_ERROR", "幂等 ledger 结构损坏")
            path = f"commits/{self._segment(entry['commit_id'])}/receipt.json"
            value = self.read_json(self.path(owner, path))
            if canonical_hash(value) != entry["receipt_hash"]:
                raise MemoryError("INTEGRITY_ERROR", "回执指纹不匹配")
            old_hash = entry["request_hash"]
        else:
            path = self.path(owner, f"request-receipts/{self._segment(request_id)}.json")
            if not path.exists():
                return None
            envelope = self.read_json(path)
            if (not isinstance(envelope, dict) or not {"receipt", "receipt_hash", "request_hash", "envelope_hash"} <= envelope.keys()
                    or canonical_hash({k: v for k, v in envelope.items() if k != "envelope_hash"}) != envelope["envelope_hash"]
                    or canonical_hash(envelope["receipt"]) != envelope["receipt_hash"]):
                raise MemoryError("INTEGRITY_ERROR", "无变化回执损坏")
            value, old_hash = envelope["receipt"], envelope["request_hash"]
        if old_hash != request_hash:
            raise MemoryError("IDEMPOTENCY_CONFLICT", "该请求 ID 已用于不同内容", {"original_receipt": value})
        if not isinstance(value, dict) or value.get("request_id") != request_id or value.get("owner_id") != owner["owner_id"]:
            raise MemoryError("INTEGRITY_ERROR", "回执请求身份或归属不一致")
        return value

    def commit_batch(self, owner, expected_head, request_id, operations, *, actor,
                     request_hash, prepare, prepublish=lambda: None, source_checks=lambda: []):
        """prepare(snapshot) 在持锁、幂等检查后生成新修订与回执映射。

        预检由服务先完成一次；持锁再检查以防并发修改。索引不参与规范提交。
        """
        self._segment(request_id)
        ensure_owner(self.root, owner, actor)
        lock_path = self.path(owner, "write.lock")
        lock = {"pid": os.getpid(), "start_identity": process_identity(os.getpid()),
                "token": str(uuid.uuid4()), "owner_id": owner["owner_id"], "created_at": self.clock()}
        try:
            # No model, network, or subprocess runs in the critical section.
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise MemoryError("LOCKED", "该对象已有写入锁；请检查恢复入口") from exc
        committed = False
        receipt = None
        recovery_ref = None
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(encoded(lock))
                stream.flush()
                os.fsync(stream.fileno())
            snapshot = self.read_snapshot(owner)
            prior = self._receipt(owner, snapshot, request_id, request_hash)
            if prior:
                return prior
            current = snapshot["head"]["commit_id"] if snapshot["head"] else None
            if expected_head != current:
                raise MemoryError("VERSION_CONFLICT", "对象已更新，请比较当前版本", {"expected_head": expected_head, "current_head": snapshot["head"]})
            changed, results = prepare(snapshot)
            generation = (snapshot["head"]["generation"] if snapshot["head"] else 0) + bool(changed)
            commit_id = "COM-" + self._segment(self.id_factory()) if changed else current
            actual_results = [{**item, "status": {"would_create": "created", "would_update": "updated"}.get(item["status"], item["status"])}
                              for item in results]
            receipt = {"request_id": request_id, "owner_id": owner["owner_id"],
                       "commit_id": commit_id, "generation": generation,
                       "save_status": "committed" if changed else "no_change",
                       "record_results": actual_results, "index_status": "pending",
                       "index_details": {"fts": "pending", "vector": "pending", "reason": "W06 索引服务尚未接入"},
                       "warnings": [], "error": {"code": "INDEX_PENDING", "message": "内容已保存；索引尚未接入"},
                       "recovery_ref": None}
            prepublish()
            if not changed:
                folder = self.path(owner, "request-receipts")
                folder.mkdir(exist_ok=True)
                destination = self.path(owner, f"request-receipts/{request_id}.json")
                temporary = self.path(owner, f"request-receipts/{request_id}.{uuid.uuid4().hex}.tmp")
                envelope = {"request_hash": request_hash, "receipt": receipt, "receipt_hash": canonical_hash(receipt)}
                envelope["envelope_hash"] = canonical_hash(envelope)
                self.write_json(temporary, envelope)
                os.replace(temporary, destination)
                return receipt
            staging = self.path(owner, f"staging/{request_id}-{uuid.uuid4().hex}")
            staging.mkdir(parents=True, exist_ok=False)
            recovery_ref = staging.relative_to(self.root).as_posix()
            (staging / "records").mkdir()
            heads = deepcopy((snapshot["manifest"] or {}).get("record_heads", {}))
            for record in changed:
                rid = self._segment(record["record_id"])
                self.write_json(staging / "records" / f"{rid}.json", record)
                heads[rid] = {"commit_id": commit_id, "path": f"commits/{commit_id}/records/{rid}.json",
                              "revision": record["revision"], "record_hash": record["record_hash"]}
            ledger = deepcopy((snapshot["manifest"] or {}).get("request_ledger", {}))
            ledger[request_id] = {"commit_id": commit_id, "request_hash": request_hash, "receipt_hash": canonical_hash(receipt)}
            pointers = deepcopy((snapshot["manifest"] or {}).get("pointers", {"policy": None, "goal": None, "checkpoint": None}))
            for record in changed:
                if record["kind"] in pointers:
                    pointers[record["kind"]] = {"record_id": record["record_id"], "revision": record["revision"]}
            manifest = {"schema_version": 1, "commit_id": commit_id, "parent_commit_id": current,
                        "parent_manifest_hash": snapshot["head"]["manifest_hash"] if snapshot["head"] else None,
                        "generation": generation, "owner_id": owner["owner_id"], "record_heads": heads,
                        "pointers": pointers, "request_ledger": ledger,
                        "changed_ids": [r["record_id"] for r in changed],
                        "source_checks": source_checks(), "index_pending": {"generation": generation, "fts": True, "vector": True}}
            self.write_json(staging / "receipt.json", receipt)
            self.write_json(staging / "manifest.json", manifest)
            # Re-read staged bytes before publication. A faulty write must never
            # become a HEAD-reachable record, even when write() returned normally.
            if canonical_hash(self.read_json(staging / "manifest.json")) != canonical_hash(manifest):
                raise MemoryError("INTEGRITY_ERROR", "暂存清单校验失败")
            for record in changed:
                if self.read_json(staging / "records" / f"{record['record_id']}.json") != record:
                    raise MemoryError("INTEGRITY_ERROR", "暂存记录校验失败")
            prepublish()
            destination = self.path(owner, f"commits/{commit_id}")
            destination.parent.mkdir(exist_ok=True)
            os.rename(staging, destination)
            recovery_ref = destination.relative_to(self.root).as_posix()
            self.fault("after_rename")
            if self.read_json(lock_path) != lock:
                raise MemoryError("LOCKED", "写锁身份变化，拒绝发布")
            observed = self.read_snapshot(owner)["head"]
            if observed != snapshot["head"]:
                raise MemoryError("VERSION_CONFLICT", "发布前 HEAD 变化")
            new_head = {"commit_id": commit_id, "generation": generation, "manifest_hash": canonical_hash(manifest)}
            pending = self.path(owner, f"HEAD-{uuid.uuid4().hex}.tmp")
            self.write_json(pending, new_head)
            self.fault("before_head")
            prepublish()
            os.replace(pending, self.path(owner, "HEAD.json"))
            committed = True
            self.fault("after_head")
            return receipt
        except OSError as exc:
            raise MemoryError("STORAGE_ERROR", str(exc), {"save_status": "committed" if committed else "not_committed",
                              "receipt": receipt if committed else None, "recovery_ref": recovery_ref}) from exc
        finally:
            # Only remove our exact lock. A different token must remain intact.
            # Bounded adapters reserve a small cleanup allowance so cancellation
            # cannot prevent ownership verification and strand our own lock.
            try:
                if self.read_lock_for_cleanup(lock_path) == lock:
                    lock_path.unlink()
            except (MemoryError, OSError):
                pass

    def read_lock_for_cleanup(self, path):
        """Cleanup hook; normal callers keep the original verified JSON read."""
        return self.read_json(path)
