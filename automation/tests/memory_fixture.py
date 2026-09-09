"""SYNTHETIC ONLY：冻结配方的隔离物化帮助，不创建正式记忆或复核。

调用方必须给出独立隔离根及其下尚不存在的目标。所有故障只操作返回的
临时副本；原始 fixtures、真实业务对象和来源登记始终只读。
"""
from __future__ import annotations

import copy
import contextlib
import hashlib
import io
import json
import shutil
import sys
import subprocess
import platform
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

REPOSITORY = Path(__file__).resolve().parents[2]
FIXTURES = REPOSITORY / "docs/design/system-memory/fixtures"
sys.path.insert(0, str(REPOSITORY / "automation/scripts"))
import workspace_cli
import evidence


def snapshot(root):
    """完整字节与目录快照，包括空目录；不读取链接指向的外部文件。"""
    root = Path(root).resolve()
    files, directories = {}, []
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError("UNSAFE_PATH: snapshot refuses links")
        name = path.relative_to(root).as_posix()
        if path.is_dir():
            directories.append(name)
        elif path.is_file():
            files[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"files": files, "directories": directories}


class FixedClock:
    """可注入服务时钟，保存时间不会被伪称为真实实验发生时间。"""
    def __init__(self, value="2026-01-01T00:00:00Z"):
        self.value = value

    def __call__(self):
        return self.value


class FixedIds:
    """确定性身份流；耗尽即失败，避免测试意外退回随机身份。"""
    def __init__(self, values):
        self.values = iter(values)

    def __call__(self, *args):
        return next(self.values)


class FaultInjector:
    """由测试明确调用的单次故障点，不修改环境或生产代码。"""
    def __init__(self, point):
        self.point, self.seen, self.fired = point, [], False

    def __call__(self, point):
        self.seen.append(point)
        if point == self.point and not self.fired:
            self.fired = True
            raise OSError("SYNTHETIC ONLY injected fault: " + point)


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


@dataclass
class MaterializedFixture:
    root: Path
    owners: dict
    sources: dict
    drafts: list
    clock: FixedClock
    limitations: list

    def source_ref(self, source_id, relation="background", locator="完整合成记录"):
        source = self.sources[source_id]
        return dict(target_kind="file", target_id=source_id, revision=None,
                    sha256=source["sha256"], locator=locator, relation=relation)

    def request(self, record_ids, *, expected_head=None, reference_ids=None):
        """将选定同 owner 配方转成真实 CommitRequest，不预先伪造服务字段。

        同批引用使用 client_key；外部已提交 MEM 引用由调用者提供回执映射。
        未提供的旧配方引用保留原 ID，让服务明确拒绝缺失，不猜测提交次序。
        """
        selected = [copy.deepcopy(next(x for x in self.drafts if x["record_id"] == rid)) for rid in record_ids]
        if not selected or len({x["owner_id"] for x in selected}) != 1:
            raise ValueError("A request requires records belonging to exactly one owner")
        owner = selected[0]["owner_id"]
        reference_ids = reference_ids or {}
        def replace(value):
            if isinstance(value, list):
                return [replace(x) for x in value]
            if not isinstance(value, dict):
                return value
            if value.get("target_kind") == "record":
                result = dict(value)
                tid = result["target_id"]
                if tid in record_ids:
                    result["client_key"] = result.pop("target_id")
                elif tid in reference_ids:
                    result["target_id"] = reference_ids[tid]
                return result
            return {key: replace(item) for key, item in value.items()}
        operations = []
        for draft in selected:
            rid = draft.pop("record_id")
            draft.pop("actor", None)
            operations.append(dict(op="put_record", client_key=rid, draft=replace(draft)))
        return dict(schema_version=1, request_id=str(uuid.uuid5(uuid.NAMESPACE_URL, owner + ":" + ",".join(record_ids))),
                    actor={"kind": "workflow", "id": "synthetic-fixture-only"}, owner_id=owner,
                    expected_head=expected_head, operations=operations)


def build_verified_legacy(target, *, isolation_root):
    """执行既有合成线性计算，并通过正式 evidence 入口复核/封存。

    有 Git 时核对真实提交；发行源码无 Git 时固定生成器源码 SHA-256，
    version_kind 明确区别快照与 Git。dirty=false 仅指固定生成器，
    不声称整个开发工作区干净。真实执行输出和
    环境摘要均写隔离目录。此正例不是八主题配方的现实实验复核。
    """
    import local_test_data
    boundary, root = Path(isolation_root).resolve(), Path(target).resolve()
    if root.exists() or root == boundary or not root.is_relative_to(boundary):
        raise ValueError("UNSAFE_PATH: requires a new isolated child")
    if root.is_relative_to(REPOSITORY) and not any(root.is_relative_to(REPOSITORY / p) for p in (".local", "tmp")):
        raise ValueError("UNSAFE_PATH: business directories are not test targets")
    current = (REPOSITORY / "automation/scripts/local_test_data.py").read_bytes()
    source_hash = hashlib.sha256(current).hexdigest()
    git_commit = None
    # A source release has neither .git nor a required Git installation. The old
    # Run contract calls its fixed code-version field 'commit' but accepts SHA256;
    # record version_kind/git_commit explicitly so a source hash is never passed
    # off as a real Git revision. No repository is initialized or committed here.
    if (REPOSITORY / ".git").exists() and shutil.which("git"):
        git = ["git", "-c", "safe.directory=" + REPOSITORY.as_posix()]
        try:
            candidate = subprocess.check_output(git + ["rev-parse", "HEAD"], cwd=REPOSITORY, text=True, stderr=subprocess.PIPE).strip()
            tracked = subprocess.check_output(git + ["show", candidate + ":automation/scripts/local_test_data.py"], cwd=REPOSITORY, stderr=subprocess.PIPE)
            # Git may normalize CRLF at checkout; compare newline bytes only.
            if tracked.replace(b"\r\n", b"\n") == current.replace(b"\r\n", b"\n"):
                git_commit = candidate
        except (OSError, subprocess.CalledProcessError):
            pass  # A readable source snapshot remains a truthful fixed version.
    version = dict(commit=git_commit or source_hash, git_commit=git_commit, dirty=False,
        version_kind="git" if git_commit else "source-snapshot-sha256",
        scope="Exact local_test_data.py source snapshot only; source SHA256 is not a Git commit and cannot be used for Release tags",
        generator_sha256=source_hash)
    local_test_data.build(root)
    (root / "SYNTHETIC_ONLY.txt").write_text("SYNTHETIC ONLY software execution\n", encoding="utf-8")
    script = root / "core-algorithms/synthetic-drift/code/drift.py"
    execution = subprocess.run([sys.executable, "-c",
        "import runpy,json,sys; m=runpy.run_path(sys.argv[1]); v=m['offset'](30); assert abs(v-1.4)<1e-12; print(json.dumps({'temperature_C':30,'offset_ms':v,'synthetic_only':True}))",
        str(script)], capture_output=True, text=True, check=True)
    result = root / "runs/synthetic-base/result.txt"
    result.write_text(execution.stdout, encoding="utf-8")
    environment = dict(python=platform.python_version(), executable=sys.executable, platform=platform.platform(),
                       script_sha256=evidence.sha256(script), generator_sha256=hashlib.sha256(current).hexdigest(),
                       python_image_sha256=evidence.sha256(Path(sys.executable)))
    environment_path = root / "runs/synthetic-base/environment.json"
    _write(environment_path, environment)
    manifest = root / "runs/synthetic-base/run.json"
    raw = evidence.read(manifest)
    raw.update(status="succeeded", code=version,
        # 这里执行纯标准库计算；摘要绑定实际解释器可执行映像，而不是将
        # 一份观察日志的哈希冒充依赖锁。完整环境另存可阅 JSON。
        environment={**environment, "lock_or_image_digest": environment["python_image_sha256"]},
        quality_results=[{"check": "SYNTHETIC ONLY: executed offset(30) equals 1.4 ms within 1e-12", "required": True, "status": "passed"}])
    raw["artifacts"] = [{"path": result.relative_to(root).as_posix(), "sha256": evidence.sha256(result)}]
    raw["inputs"].append({"path": script.relative_to(root).as_posix(), "sha256": evidence.sha256(script)})
    _write(manifest, raw)
    review = evidence.review_claim(root, "CLM-SYNTHETIC", "accepted", "synthetic-authorized-software-workflow",
        "SYNTHETIC ONLY: real subprocess calculation and numeric assertion passed; no business validation",
        evidence="runs/synthetic-base/result.txt", scope="synthetic:only")
    seal = evidence.finalize_run(root, "RUN-SYNTHETIC", "synthetic:only")
    if not seal["finalized"]:
        raise AssertionError(seal)
    receipt = dict(synthetic_only=True, root=str(root), command=execution.args, exit_code=execution.returncode,
                   stdout=execution.stdout, stderr=execution.stderr, review=review, finalization=seal)
    _write(root / "synthetic-execution-receipt.json", receipt)
    return receipt


def materialize(target, *, isolation_root):
    """在显式空白目标生成八类旧对象及草案，绝不自动提交或 accepted。

    隔离根可以是系统 TemporaryDirectory 或仓库 .local/tmp 下的专用目录；
    不能把正式业务目录包装成隔离根。拒绝覆盖，因而失败残留可直接审查。
    """
    boundary, root = Path(isolation_root).resolve(), Path(target).resolve()
    local = REPOSITORY / ".local"
    temporary = REPOSITORY / "tmp"
    if boundary == REPOSITORY or (boundary.is_relative_to(REPOSITORY)
                                  and not any(boundary.is_relative_to(p) for p in (local, temporary))):
        raise ValueError("UNSAFE_PATH: isolation root is a business workspace")
    if root == boundary or not root.is_relative_to(boundary) or root.exists():
        raise ValueError("UNSAFE_PATH: target must be a new child of isolation_root")
    if REPOSITORY.is_relative_to(root):
        raise ValueError("UNSAFE_PATH: target contains repository")
    recipes = json.loads((FIXTURES / "records.json").read_text(encoding="utf-8"))
    if recipes.get("synthetic_only") is not True:
        raise ValueError("Only explicitly synthetic fixtures are accepted")
    root.mkdir(parents=True)
    (root / "SYNTHETIC_ONLY.txt").write_text("SYNTHETIC ONLY — software tests, no business evidence.\n", encoding="utf-8")
    _write(root / "workspace.json", {"schema_version": 1, "required_paths": []})
    _write(root / "tools/registry.json", {"schema_version": 1, "tools": []})
    for area in ("projects", "research", "core-algorithms"):
        shutil.copytree(REPOSITORY / area / "_template", root / area / "_template")
    owners, sources = {}, {}
    clock = FixedClock(recipes["fixed_clock"])
    for seed in recipes["sources"]:
        source = FIXTURES / seed["path"]
        destination = root / "synthetic-sources" / source.name
        destination.parent.mkdir(exist_ok=True)
        shutil.copyfile(source, destination)
        sources[seed["source_id"]] = dict(source_id=seed["source_id"],
            path=destination.relative_to(root).as_posix(), enabled=True, sensitivity="internal",
            sha256=hashlib.sha256(destination.read_bytes()).hexdigest(), note="SYNTHETIC ONLY")
    _write(root / "retrieval/sources.json", {"schema_version": 1, "sources": list(sources.values())})
    for number, seed in enumerate(recipes["owners"]):
        kind, oid = seed["owner_type"], seed["owner_id"]
        native = seed["native_ref"].split("#", 1)[0]
        path = root / native
        title = "SYNTHETIC ONLY: " + seed["title"]
        moment = datetime.fromisoformat(clock().replace("Z", "+00:00"))
        with patch.object(workspace_cli, "now_utc", return_value=moment), contextlib.redirect_stdout(io.StringIO()):
            if kind in ("project", "research", "core-algorithm"):
                fn = {"project": workspace_cli.create_project, "research": workspace_cli.create_research,
                      "core-algorithm": workspace_cli.create_module}[kind]
                kwargs = {"source_document": seed["source_document"]} if kind == "core-algorithm" else {}
                generated = fn(root, f"synthetic-{number}", title, **kwargs)
                generated.rename(path.parent)
                raw = json.loads(path.read_text(encoding="utf-8"))
                raw[{"project": "project_id", "research": "research_id", "core-algorithm": "module_id"}[kind]] = oid
            elif kind == "run":
                # 注入 UUID 使模板附属 README 中的创建身份也可重复；随后统一
                # 替换配方固定 Run ID，避免正文导航与 manifest 不一致。
                with patch.object(workspace_cli.uuid, "uuid4", return_value=uuid.UUID(int=number + 1)):
                    generated = workspace_cli.create_run(root, None, title)
                generated.rename(path.parent)
                raw = json.loads(path.read_text(encoding="utf-8"))
                old_id = raw["run_id"]
                raw["run_id"] = oid
                readme = path.parent / "README.md"
                readme.write_text(readme.read_text(encoding="utf-8").replace(old_id, oid), encoding="utf-8")
                # 仅物化输入和待执行 Run。配方中的 succeeded/finalized 需后续
                # 验证流程真实执行，不能把描述字符串冒充验证证据。
                legacy = next(x for x in recipes["legacy_runs"] if x["run_id"] == oid)
                raw.update(question=legacy["question"], parameters=legacy["parameters"],
                           related_research_ids=[legacy["research_id"]], limitations=["SYNTHETIC ONLY: not executed"])
                raw["claims"] = [dict(claim_id=legacy["claim_id"], statement=legacy["statement"],
                    kind="calculation", scope=legacy["claim_scope"], review={"status": "not-reviewed"},
                    review_history=[], evidence_refs=[dict(target=sources[sid]["path"],
                        sha256=sources[sid]["sha256"], relation="supports", locator="完整合成记录")
                        for sid in legacy["inputs"]])]
            elif kind == "knowledge":
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(f"# {title}\n\nSYNTHETIC ONLY\n", encoding="utf-8")
                owners[oid] = {**seed, "path": native}
                continue
            elif kind == "report":
                raw = json.loads((REPOSITORY / "reports/manifests/report_manifest.example.json").read_text(encoding="utf-8"))
                raw.update(report_id=oid, title=title, status="draft")
            elif kind == "data":
                raw = json.loads((REPOSITORY / "data/catalog/example.dataset.json").read_text(encoding="utf-8"))
                raw.update(dataset_id=oid, name=title, status="draft", purpose="SYNTHETIC ONLY")
            else:
                entry = root / "tools/synthetic-tool"
                entry.mkdir()
                raw = {"schema_version": 1, "tools": [dict(tool_id=oid, title=title,
                       entrypoint="tools/synthetic-tool", status="active")]}
        # 模板默认 restricted 面向未知真实材料；本函数只创建新合成对象，
        # 分类必须来自冻结配方，未指定时与合成来源/草案一致为 internal。
        # 不据此改写任何已有对象，也不降低真实来源的权限。
        if kind == "tool":
            raw["tools"][0]["sensitivity"] = seed.get("sensitivity", "internal")
        else:
            raw["sensitivity"] = seed.get("sensitivity", "internal")
        _write(path, raw)
        owners[oid] = {**seed, "path": native}
    fixture = MaterializedFixture(root, owners, sources, [], clock, [
        "Legacy run execution/review/finalize recipes are not executed; all claims remain not-reviewed.",
        "Drafts are conversion inputs, not committed records; scenario HEAD bindings require the store."])
    graph = evidence.EvidenceGraph(root)
    def convert(value):
        if isinstance(value, list):
            return [convert(item) for item in value]
        if not isinstance(value, dict):
            return value
        if "target_id" in value:
            tid = value["target_id"]
            ref = dict(target_kind="record" if tid.startswith("MEM-") else "claim" if tid.startswith("CLM-") else "file" if tid in sources else "owner",
                       target_id=tid, revision=value.get("revision"), sha256=None,
                       locator=value.get("locator", ""), relation=value.get("relation", "background"))
            if tid in sources:
                ref["sha256"] = sources[tid]["sha256"]
            elif tid in graph.nodes:
                ref["sha256"] = graph.nodes[tid]["fingerprint"]
            elif tid in owners:
                ref["sha256"] = hashlib.sha256((root / owners[tid]["path"]).read_bytes()).hexdigest()
            elif not tid.startswith("MEM-"):
                raise ValueError("Unresolved positive recipe: " + tid)
            return ref
        return {key: convert(item) for key, item in value.items()}
    for seed in recipes["records"]:
        draft = copy.deepcopy(seed)
        # These frozen recipes describe the original v1 L0–L3 taxonomy. New
        # unversioned user drafts default to v2; pin this historical fixture at
        # the conversion boundary without rewriting its frozen source bytes.
        draft.setdefault("schema_version", 1)
        draft.pop("occurred_at", None)
        draft["keywords"] = draft["payload"].pop("keywords", [])
        if draft["kind"] == "source":
            draft["payload"]["source_ref"] = fixture.source_ref(draft["payload"].pop("source_id"))
        fixture.drafts.append(convert(draft))
    return fixture
