"""Archive the executing AI's explicit, post-reading A09 observations.

This script only stores declarations and existing captures. It does not decide
whether an expectation passes, generate an analysis, or modify F3 records.
"""
from pathlib import Path
import json
import sys

REPOSITORY = Path.cwd().resolve()
RUN = Path(__file__).resolve().parents[2]
ATTEMPT = Path(__file__).resolve().parent / "attempt-6a3c96e965c1408e998f7cfc8de720e7"
sys.path.insert(0, str(REPOSITORY / "automation/testing"))
import ai_review

actor = "Codex /root/retrieval_review actual AI"
observations = {
    "saturation-full": "读完公开 full 返回的新约束全文，核对目标 2 m、c=0.1 m²/s、流量上限 0.15 m³/s 以及该输入没有旧记录边。",
    "maintenance-plan": "实际读完服务器交付的五部分：新约束、模型、定义和两份原件；依据这些正文作出 retain/retain/revise 判断，未把共享 F3 词项当成语义证明。",
    "baseline-process": "读完公开投影的完整过程 r1，确认旧模型固定 r1、新约束未融合，以及明确标为本次新建的旧依据基线。",
    "baseline-report": "读完公开投影的精简报告 r1，核对旧模型与未融合范围；没有把本次创建的基线称为真实历史报告。",
    "updated-process": "读完更新完整过程 r2，核对定义、原推导、新可达性块以及共同依据定义 r1/模型 r2/新约束 r1；complete=true，科学状态未评估。",
    "updated-report": "读完更新简报 r2，核对 0.20>0.15、1.5 m 与残差 0.5 m，以及简报与完整过程的相同固定依据和未验证范围。",
    "historical-process": "读完历史完整过程 r1 投影，确认旧正文和旧引用保留，仅额外提示已有新修订，没有静默更新历史。",
    "historical-report": "读完历史简报 r1 投影，确认保留旧内容和旧固定依据。",
}
authored = ATTEMPT / "authored-review"
authored.mkdir(exist_ok=True)
reads = []
for name, observation in observations.items():
    event = {"actor": actor, "origin": "public material-query and memory CLI",
             "capture_path": str(ATTEMPT / "delivered" / (name + ".md")),
             "locator": "完整公开返回投影，已在工具输出中实际呈现并阅读",
             "coverage": "full", "observation": observation}
    path = authored / ("read-" + name + ".json")
    with path.open("x", encoding="utf-8") as stream:
        json.dump(event, stream, ensure_ascii=False, indent=2)
    reads.append(str(ai_review.record_read(ATTEMPT, path)))

assessment = {
    "actor": actor,
    "comparisons": [
        {"expectation_id": "A09-E1", "status": "meets",
         "observation": "没有旧记录边的新约束仍进入真实维护；读完新约束与五部分维护正文后算出目标不可维持，保留条件推导并补边界。候选存在共享 SYNTHETIC/F3 词项，不能证明语义召回质量。",
         "evidence_refs": ["delivered/saturation-full.md", "delivered/maintenance-plan.md", "AI-ANALYSIS.md", "reads"]},
        {"expectation_id": "A09-E2", "status": "meets",
         "observation": "实际 AI 填写自身 ai 身份、交付固定 refs 和逐项理由，保留 read_receipt、未检查范围；retain 定义与新输入、revise 原模型。没有伪造人工确认或将计算冒充实验。",
         "evidence_refs": ["AI-ANALYSIS.md", "authored-requests", "outcomes/maintenance-review.json"]},
        {"expectation_id": "A09-E3", "status": "meets",
         "observation": "公开 review/apply 使用服务器摘要，真实写出模型 r2；同 request_id 返回相同 COM，HEAD 变化后旧 review 返回 CONFLICT。索引 pending 与随后文本 reconcile 分别记录；两文稿 r2 和历史 r1 均读回。A08 导航 stale 保留待复核。",
         "evidence_refs": ["outcomes/maintenance-apply.json", "outcomes/maintenance-apply-same-id.json", "outcomes/maintenance-stale-review.json", "document-update-receipt.json", "AI-ANALYSIS.md"]},
    ],
    "readable_artifacts": [{"title": "A09 实际反证维护与双文稿读回", "path": str(ATTEMPT / "AI-ANALYSIS.md")}],
    "limitations": ["输入与分析由同一 AI 在连续上下文完成，不是盲测。", "未配置结构模型或向量，文本索引成功不证明模型与科学结论有效。", "双文稿旧依据基线是本次公开新建；没有应撤回的已复核 claim。", "未执行故障注入、跨 owner 部分失败恢复或人工验收；A08 旧导航仍 stale 待复核。"],
    "human_review": "pending", "scientific_review": "not-reviewed",
}
assessment_path = authored / "assessment.json"
with assessment_path.open("x", encoding="utf-8") as stream:
    json.dump(assessment, stream, ensure_ascii=False, indent=2)
saved = ai_review.record_assessment(ATTEMPT, assessment_path)
report = ai_review.render(RUN / "actual-ai")
receipt = {"reads": reads, "assessment": str(saved), "report": str(report)}
with (ATTEMPT / "review-receipt.json").open("x", encoding="utf-8") as stream:
    json.dump(receipt, stream, ensure_ascii=False, indent=2)
print(json.dumps(receipt, ensure_ascii=False, indent=2))
