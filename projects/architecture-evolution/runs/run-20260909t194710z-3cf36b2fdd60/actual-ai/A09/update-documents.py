"""Update the actually-read synthetic document pair through public transactions.

The change follows the public impact report: only the affected full and brief
sections, then their independent documents, receive new fixed revisions. Old
versions remain readable. This is explicit AI-authored maintenance, not an
automatic synthesis or a claim that real historical documents were recovered.
"""
from copy import deepcopy
import hashlib
from importlib.util import spec_from_file_location, module_from_spec
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import capture as c


def load_helper(name, filename):
    spec = spec_from_file_location(name, Path(__file__).parent / filename)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


docs = load_helper("a09_prepare_docs", "prepare-documents.py")
projection = load_helper("a09_inspect_docs", "inspect-documents.py")


def revision_draft(record):
    keys = ("schema_version", "owner_id", "kind", "title", "body_markdown", "keywords", "payload", "sources", "provenance_gap", "record_reason", "discovery", "sensitivity")
    result = {key: deepcopy(record[key]) for key in keys}
    result["change_reason"] = "实际阅读新饱和约束、模型r2和公开文稿影响后，局部同步固定章节与适用边界；保留旧r1"
    return result


def main():
    target = c.attempt()
    old_docs = json.loads((target / "baseline-documents.json").read_text(encoding="utf-8"))
    initial = json.loads((target / "initial-owner-inspection.json").read_text(encoding="utf-8"))
    old_section = initial["tank"]["records"][c.F3["refs"]["tank_section"]["id"]]
    model = json.loads((target / "applied-model.json").read_text(encoding="utf-8"))["record"]
    basis = [deepcopy(c.F3["legacy_refs"]["tank_definitions"]), docs.fixed(model), deepcopy(c.F3["legacy_refs"]["saturation"])]
    section = revision_draft(old_section)
    section["sources"] = deepcopy(basis)
    section["payload"]["blocks"] = [
        {"type": "prose", "markdown": "本章保留变量定义与原未饱和推导，补入新饱和输入的目标可达性检查。给定目标2 m需要0.20 m³/s，大于泵上限0.15 m³/s；不能据原线性段解保证该目标误差归零。结论仅属于合成前提，未做现实验证。", "evidence_refs": deepcopy(basis)},
        {"type": "unit", "ref": deepcopy(basis[0])}, {"type": "unit", "ref": deepcopy(basis[1])}]
    new_section = docs.save_record("updated-full-section", section, old_section)
    brief = revision_draft(old_docs["brief_section"])
    brief["title"] = "SYNTHETIC F3 水箱结论与饱和边界"
    brief["sources"] = deepcopy(basis)
    brief["payload"].update(title="水箱结论与饱和边界", blocks=[{"type": "prose", "evidence_refs": deepcopy(basis),
        "markdown": "原未饱和、无延迟模型的误差指数衰减结论保留其适用条件。新固定输入给出目标 $h_r=2\\,\\mathrm{m}$、出流系数 $c=0.1\\,\\mathrm{m^2/s}$、泵流量上限 $q_{max}=0.15\\,\\mathrm{m^3/s}$。所需流量 $q_{req}=ch_r=0.20\\,\\mathrm{m^3/s}>q_{max}$，目标无法维持；持续饱和平衡 $h_{sat}=q_{max}/c=1.5\\,\\mathrm{m}$。$q_{req}$ 为目标所需流量，$h_{sat}$ 为持续最大流量的平衡液位。仅增大增益不能突破泵上限。应先检查可达性，再在相应分段模型中分析；其他目标、延迟、噪声和非线性仍需独立验证。本报告只保存合成代数分析，无实验或科学认可。"}])
    new_brief = docs.save_record("updated-brief-section", brief, old_docs["brief_section"])
    new_docs = {}
    for key, ref, title in (("process", docs.fixed(new_section), "SYNTHETIC F3 水箱完整过程"), ("report", docs.fixed(new_brief), "SYNTHETIC F3 水箱精简报告")):
        draft = revision_draft(old_docs[key])
        draft.update(title=title, sources=deepcopy(basis))
        draft["payload"].update(scope="固定模型r2、定义r1与饱和输入r1；仅合成参数下的代数分析，人工与科学验收未完成",
            common_refs=deepcopy(basis), section_refs=[ref])
        new_docs[key] = docs.save_record("updated-" + key, draft, old_docs[key])
    c.call("documents-final-reconcile", "reconcile", {"owner_id": "RES-F3-TANK", "vector": "off"}, domain="memory")
    readback = {}
    for key, record in new_docs.items():
        fresh = c.call("updated-" + key + "-read", "document", {"owner_id": "RES-F3-TANK", "document_id": record["record_id"], "revision": 2}, domain="memory")
        historical = c.call("historical-" + key + "-read", "document", {"owner_id": "RES-F3-TANK", "document_id": record["record_id"], "revision": 1}, domain="memory")
        impact = c.call("impact-after-" + key, "document-impact", {"owner_id": "RES-F3-TANK", "document_id": record["record_id"], "revision": 2}, domain="memory")
        projection.project_document("updated-" + key, fresh)
        projection.project_document("historical-" + key, historical)
        readback[key] = {"ref": docs.fixed(record), "current_complete": fresh["report"]["complete"], "historical_complete": historical["report"]["complete"],
            "historical_revision": historical["document"]["revision"], "changes_after": impact["changes"],
            "scientific_review": impact["scientific_review"]}
    old_navigation = json.loads((c.RUN / "actual-ai/A08/attempt-827ddd756ca34e78825e4e48c7d98aa4/navigation-result.json").read_text(encoding="utf-8"))["inspected"]["record"]
    navigation = c.call("navigation-after-maintenance", "associations-view", {"owner_id": "RES-F3-RETRY", "record_id": old_navigation["record_id"], "revision": 1}, domain="memory")
    hashes = {key: hashlib.sha256((c.ROOT / source["path"]).read_bytes()).hexdigest() for key, source in c.F3["sources"].items()}
    result = {"documents": readback, "sections": {"full": docs.fixed(new_section), "brief": docs.fixed(new_brief)},
        "original_source_hashes_after": hashes, "navigation_stale": navigation["stale"], "navigation_changed_endpoints": navigation["changed_endpoints"]}
    c.write(target / "document-update-receipt.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
