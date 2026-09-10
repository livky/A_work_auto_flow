"""准备实际Project文稿的隔离只读QA副本，避免干扰已有工作台进程。

仅复制本Project规范记忆和归属说明；固定来源继续引用已获准的原工作区文件。
不读取企业目录，不修改来源/原Project，不把实际实现记录改称合成业务结论。
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import uuid

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[3]
sys.path.insert(0, str(ROOT / "automation/scripts"))
from memory import index
from memory.evidence_adapter import iter_refs


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    if not (RUN / "implementation-recording-checks.json").exists():
        raise RuntimeError("必须先完成实际Project保存和公共回读")
    marker = RUN / "project-ui-fixture.json"
    if marker.exists():
        raise RuntimeError("QA副本已建立；请复用回执，不覆盖")
    target = (ROOT / ".local/testing" / ("project-document-ui-" + uuid.uuid4().hex)).resolve()
    if not target.is_relative_to(ROOT / ".local/testing") or target.exists():
        raise RuntimeError("隔离目标必须是工作区测试目录下的新路径")
    owner = ROOT / "projects/architecture-evolution"
    copy_owner = target / "projects/architecture-evolution"
    copy_owner.mkdir(parents=True)
    shutil.copytree(owner / "memory", copy_owner / "memory")
    for name in ("project.json", "README.md", "AGENTS.md"):
        shutil.copy2(owner / name, copy_owner / name)
    def put(name, value):
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    put("workspace.json", {"schema_version": 1, "workspace_id": "isolated-project-document-qa", "required_paths": [], "context_policy": {"excluded_directories": [".local"]}})
    put("tools/registry.json", {"tools": []})
    for name in ("config.json", "context-policy.json"):
        config = json.loads((ROOT / "retrieval" / name).read_text(encoding="utf-8"))
        if name == "config.json":
            config.update(vector_store={"provider": None}, ocr_enabled=False)
        put("retrieval/" + name, config)
    put("retrieval/eval.json", {"cases": []})
    ids = set()
    for path in (owner / "memory").rglob("*.json"):
        for ref in iter_refs(json.loads(path.read_text(encoding="utf-8"))):
            if ref.get("target_kind") == "file":
                ids.add(ref["target_id"])
    registry = json.loads((ROOT / "retrieval/sources.json").read_text(encoding="utf-8"))
    sources = []
    for source in registry["sources"]:
        if source["source_id"] not in ids:
            continue
        path = Path(source["path"])
        path = path.resolve() if path.is_absolute() else (ROOT / path).resolve()
        if not path.is_relative_to(ROOT):
            raise RuntimeError("当前QA不扩展到工作区外的已登记来源：" + source["source_id"])
        sources.append({**source, "path": str(path)})
    if ids - {item["source_id"] for item in sources}:
        raise RuntimeError("实际规范来源缺少登记，不能伪造完整QA副本")
    put("retrieval/sources.json", {"sources": sources})
    hashes = {path.relative_to(owner).as_posix(): sha(path) for path in (owner / "memory").rglob("*") if path.is_file()}
    for relative, fingerprint in hashes.items():
        if sha(copy_owner / relative) != fingerprint:
            raise RuntimeError("副本字节核对失败：" + relative)
    result = index.reconcile(target, vector="off")
    receipt = {"root": str(target), "owner_id": "PRJ-ARCHITECTURE-EVOLUTION", "original": str(owner),
               "fixed_memory_hashes": hashes, "sources": [item["source_id"] for item in sources], "index_result": result,
               "scope": "actual project canonical records copied for UI inspection; original sources read-only; no original workspace server interrupted"}
    marker.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"root": str(target), "records_files": len(hashes), "sources": len(sources), "receipt": str(marker)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
