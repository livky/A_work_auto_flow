"""Project returned fixed document bodies and inspect update impacts read-only."""
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import capture as c


def project_document(label, result):
    report = result["report"]
    text = ["# " + report["title"], "", "公开 document 返回的完整正文投影；不是新撰写的文稿。", "",
        "```json", json.dumps({key: result.get(key) for key in ("document", "missing", "report_coverage", "report_version_hints", "basis_heads")}, ensure_ascii=False, indent=2), "```",
        "", "complete=" + str(report["complete"]), ""]
    for section in report["sections"]:
        text += ["## " + section["title"], "", "固定章节：`" + json.dumps(section["ref"], ensure_ascii=False) + "`", ""]
        for block in section["blocks"]:
            if block["type"] == "prose":
                text += [block["markdown"], "", "依据：`" + json.dumps(block.get("evidence_refs", []), ensure_ascii=False) + "`", ""]
            else:
                text += ["固定单元：`" + json.dumps(block["ref"], ensure_ascii=False) + "`", ""]
                text += [part["markdown"] + "\n" for part in block.get("resolved_blocks", [])]
    c.write(c.attempt() / "delivered" / (label + ".md"), "\n".join(text))


def main():
    records = json.loads((c.attempt() / "baseline-documents.json").read_text(encoding="utf-8"))
    for key in ("process", "report"):
        saved = json.loads((c.attempt() / "outcomes" / ("baseline-" + key + "-read.json")).read_text(encoding="utf-8"))["result"]
        project_document("baseline-" + key, saved)
        impact = c.call("impact-before-" + key, "document-impact", {"owner_id": "RES-F3-TANK", "document_id": records[key]["record_id"], "revision": 1}, domain="memory")
        print(json.dumps({"document": key, "impact": impact}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
