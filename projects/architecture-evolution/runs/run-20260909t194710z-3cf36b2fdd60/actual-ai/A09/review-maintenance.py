"""Submit the actual AI's post-reading, item-specific maintenance decisions.

The five declared reviewed refs correspond to the complete material task pack
that was actually displayed and read before writing this script. Protected plan
metadata and the delivery receipt are preserved byte-for-byte in the request.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
import capture as c

NEW_BOUNDARY = r"""## 新饱和输入的目标可达性（合成代数检查）

新固定输入给出 $q_{max}=0.15\,\mathrm{m^3/s}$、$h_r=2\,\mathrm{m}$，沿用 $c=0.1\,\mathrm{m^2/s}$ 与 $A=2\,\mathrm{m^2}$。目标平衡需要

$$
q_{req}=c h_r=0.20\,\mathrm{m^3/s}>q_{max}.
$$

因此该参数下不存在维持目标的可用入流。持续饱和分支的平衡为

$$
h_{sat}=\frac{q_{max}}{c}=1.5\,\mathrm{m},\qquad h_r-h_{sat}=0.5\,\mathrm{m}.
$$

$q_{req}$ 是维持目标所需流量，$h_{sat}$ 是持续最大流量时的合成平衡液位。仅增大 $K$ 不能突破泵上限；不能在该目标下沿用未饱和指数式来保证误差归零。原线性段推导保留其条件成立的适用范围，没有被整体撤回。

这是基于新旧固定文字前提的代数分析，不是泵实测、仿真运行或科学复核。其他目标、泵能力、延迟和非线性条件仍需独立检查。
"""


def main():
    target = c.attempt()
    envelope = json.loads((target / "outcomes/maintenance-plan.json").read_text(encoding="utf-8"))["result"]
    original = envelope["value"]
    proposed = deepcopy(original)
    model = json.loads((target / "initial-owner-inspection.json").read_text(encoding="utf-8"))["tank"]["records"][c.F3["refs"]["tank_model"]["id"]]
    fields = ("schema_version", "owner_id", "kind", "title", "body_markdown", "keywords", "payload", "sources", "provenance_gap", "record_reason", "discovery", "sensitivity")
    draft = {key: deepcopy(model[key]) for key in fields}
    draft["change_reason"] = "实际AI阅读无旧边新饱和输入后补充特定参数的不可达条件；保留原未饱和推导与旧修订"
    draft["payload"]["blocks"][0]["markdown"] = draft["payload"]["blocks"][0]["markdown"].replace(
        "尚未测量延迟、噪声与出流非线性，也未验证目标流量是否可达。", "尚未测量延迟、噪声与出流非线性；本次新参数的目标可达性检查见后续边界块。")
    draft["payload"]["blocks"].append({"block_id": "saturation_boundary", "role": "limitations", "markdown": NEW_BOUNDARY, "requires_block_ids": ["model"]})
    description = draft["payload"]["retrieval_description"]
    description["key_findings"].append("新给定泵上限0.15 m³/s、目标2 m时，所需0.20 m³/s超出上限，不能保证目标误差归零")
    description["limitations"] = ["仅检查给定合成参数的代数可达性；其他目标、泵能力、延迟与非线性仍未验证；没有现实实验"]
    description["not_applicable"].append("不得把该线性段解用于新给定的不可达目标")
    new_ref = deepcopy(c.F3["legacy_refs"]["saturation"])
    draft["sources"].append(new_ref)
    draft["payload"]["evidence_refs"].append(deepcopy(new_ref))
    for item in proposed["items"]:
        if item["ref"]["id"] == c.F3["refs"]["tank_model"]["id"]:
            item.update(action="revise", reasons=["实际读取双方定义与公式：0.1×2=0.20大于0.15，特定目标不可达；补充适用边界而非撤回条件成立的线性推导"], draft_json=json.dumps(draft, ensure_ascii=False))
        elif item["ref"]["id"] == c.F3["refs"]["tank_definitions"]["id"]:
            item.update(action="retain", reasons=["变量含义、单位与clip定义仍成立；新材料给出具体q_max，并未改变这份通用变量字典"], draft_json=None)
        else:
            item.update(action="retain", reasons=["新材料是独立合成约束原输入，代数条件已实际核对；保持其固定r1与原件，不改写为实验或科学认可"], draft_json=None)
    proposed.update(semantic_reviewer=c.ACTOR, reviewer_kind="ai",
        review_note="已实际读完任务包5部分：新约束、旧模型、变量定义、两份已登记原件。新参数下目标不可达；保留变量和输入，仅修订模型适用边界。共享词候选不能证明语义影响。此计划仅detail，两份文稿另用公开固定事务维护；未覆盖API、真实系统与未登记来源。没有科学review。",
        reviewed_refs=[deepcopy(ref) for part in original["context_items"] for ref in part["refs"]])
    result = c.call("maintenance-review", "maintenance-review", {"plan": proposed, "expected_digest": original["plan_digest"]})
    c.write(target / "authored-model-r2.json", draft)
    if result.get("value") is None:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    reviewed = result["value"]
    apply_request = {"plan_id": reviewed["plan_id"], "expected_digest": reviewed["plan_digest"], "request_id": str(uuid.uuid4())}
    c.write(target / "ready-apply-request.json", apply_request)
    print(json.dumps({"review_status": result["status"], "warnings": result["warnings"], "plan_id": reviewed["plan_id"],
        "plan_digest": reviewed["plan_digest"], "reviewer_kind": reviewed["reviewer_kind"], "semantic_reviewer": reviewed["semantic_reviewer"],
        "items": [{"id": item["ref"]["id"], "action": item["action"], "reasons": item["reasons"]} for item in reviewed["items"]],
        "apply_request": apply_request}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
