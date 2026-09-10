"""Save the AI-authored post-reading navigation draft via the public CLI.

This script is an action recorder, not a model or a semantic evaluator. Its
payload was written after the actual full-text reads documented in this attempt.
An INDEX_PENDING response remains evidence of a saved record and pending index.
"""
from pathlib import Path
import json
import os
import sys
import uuid

REPOSITORY = Path.cwd().resolve()
ATTEMPT = Path(__file__).resolve().parent
RUN = ATTEMPT.parents[2]
sys.path.insert(0, str(REPOSITORY / "automation/testing"))
import ai_review

F3 = json.loads((RUN / "f3-inputs/manifest.json").read_text(encoding="utf-8"))
ROOT = Path(F3["root"])
CLI = REPOSITORY / "automation/scripts/workspace_cli.py"
os.environ["PYTHONUTF8"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def call(label, action, request=None, inspect_args=None):
    argv = [sys.executable, "-X", "utf8", str(CLI), "--root", str(ROOT), "memory", action]
    path = ATTEMPT / "authored-requests" / (label + ".json") if request is not None else None
    if path:
        write(path, request)
        argv += ["--request", str(path)]
    if inspect_args:
        argv += inspect_args
    folder, receipt = ai_review.capture_call(ATTEMPT, argv, path, cwd=ROOT)
    result = json.loads((folder / "stdout.txt").read_bytes())
    return result, {"label": label, "call": str(folder), "exit_code": receipt["exit_code"]}


def main():
    records = []
    before, evidence = call("navigation-before", "inspect", inspect_args=["RES-F3-RETRY"])
    records.append(evidence)
    request = {"request_id": str(uuid.uuid4()), "actor": {"kind": "ai", "id": "Codex /root/retrieval_review actual AI"},
        "owner_id": "RES-F3-RETRY", "expected_head": before["head"]["commit_id"],
        "title": "SYNTHETIC F3 有界动作的条件参考：水箱与重试",
        "reason": "实际阅读固定双方全文后保存导航草案；不是科学支持，人工待审",
        "discovery": "workspace_summary", "sensitivity": "internal",
        "body_markdown": "实际 AI 阅读后判断：可参考按未受限/受限区间分别检查边界的方法；不能把水箱比例增益与重试倍率相等，也不能用连续误差衰减证明 API 稳定或最终成功。API 缺少服务端状态转移和负载模型。下一步须独立检查幂等性、错误分类、超时、次数/总耗时与同步重试情形。未执行该验证；此记录仅为 candidate 导航。",
        "payload": {"from": F3["legacy_refs"]["tank_section"], "to": F3["legacy_refs"]["retry"],
            "relation": "analogous_to", "status": "candidate",
            "explanation": "条件参考：对动作封顶前后分别检查边界行为。不可推广：水箱连续误差方程不能证明 API 重试的稳定、吞吐或成功保证。",
            "shared_structure": "观测后采取调整动作，并区分动作尚未受限与已受限的状态；这一局部结构不建立相同动力学。",
            "transfer_limits": [
                "水箱状态是有单位的液位误差，API 状态是失败序号；没有统一状态方程，不能将 K 与 r 或其数值互换。",
                "只有明确幂等/去重、可重试错误分类、超时和总耗时边界后，才可参考分段检查方法。",
                "须以独立事件序列验证封顶、立即成功、连续失败、不可重试失败和同步重试；本次未运行该实验。",
                "缺少到达率、服务能力、响应延迟与并发策略时，不推断服务端稳定或最优吞吐；导航候选不提供科学支持。"],
            "basis_refs": [F3["legacy_refs"][name] for name in ("tank_section", "tank_definitions", "tank_model", "retry")]}}
    receipt, evidence = call("navigation-save", "associations-decide", request)
    records.append(evidence)
    if receipt.get("save_status") != "committed":
        raise ValueError("Navigation was not committed: " + repr(receipt))
    result = receipt["record_results"][0]
    inspected, evidence = call("navigation-inspect", "inspect", inspect_args=["RES-F3-RETRY", "--record-id", result["record_id"], "--revision", str(result["revision"])])
    records.append(evidence)
    view, evidence = call("navigation-view", "associations-view", {"owner_id": "RES-F3-RETRY", "record_id": result["record_id"], "revision": result["revision"]})
    records.append(evidence)
    reconcile, evidence = call("navigation-reconcile", "reconcile", {"owner_id": "RES-F3-RETRY", "vector": "off"})
    records.append(evidence)
    # Re-read both original records after saving navigation. These observations
    # come from public inspect; no store files or HEAD are read or edited here.
    originals = {}
    for key in ("tank_section", "retry"):
        ref = F3["refs"][key]
        value, evidence = call("after-" + key, "inspect", inspect_args=[F3["record_owners"][key], "--record-id", ref["id"], "--revision", str(ref["revision"])])
        records.append(evidence)
        originals[key] = {"record_id": value["record"]["record_id"], "revision": value["record"]["revision"],
            "record_hash": value["record"]["record_hash"], "owner_id": value["record"]["owner_id"]}
    write(ATTEMPT / "navigation-result.json", {"save": receipt, "inspected": inspected, "view": view,
        "index": reconcile, "originals_after": originals, "calls": records})
    print(json.dumps({"record": inspected["record"], "stale": view["stale"], "save_status": receipt["save_status"],
        "initial_index_status": receipt["index_status"], "reconciled_index_status": reconcile["index_status"],
        "originals_after": originals, "calls": records}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
