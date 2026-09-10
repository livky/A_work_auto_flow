"""Archive the assistant's explicit observations after actual reading and UI review.

No result is inferred from exit codes. Prose below was authored by the assistant
after inspecting the public outputs and screenshots; human review remains pending.
"""
import hashlib
import json
from pathlib import Path
import sys

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[3]
sys.path.insert(0, str(ROOT / "automation/testing"))
import ai_review

attempts = json.loads((RUN / "project-recording-attempts.json").read_text(encoding="utf-8"))
calls = {row["label"]: Path(row["call"]) / "stdout.txt" for row in map(json.loads, (RUN / "project-recording-calls.jsonl").read_text(encoding="utf-8").splitlines())}
readings = [
    ("A01", calls["implementation-documents-map-inspect"], "partial", "三个新增技术单元、事件和经验的归属及固定修订", "归属 PRJ-ARCHITECTURE-EVOLUTION；未知 Run/发生时间留空；未生成 accepted 科学认可。"),
    ("A01", calls["implementation-fixed-expand"], "partial", "context_text 中 U1 正文与 SRC-ARCH-IMPLEMENTATION-20260910-1 原文", "真实展开包含完整范围公式、资源公式和固定来源指纹；manifest complete，缺失为空。"),
    ("A03", calls["implementation-selected-section"], "partial", "所选实现章节、scope 必需定义、方法正文和 manifest", "选块包含 scope 定义及两处完整公式；其余共同依据以描述补充，没有冒充全文。"),
    ("A04", calls["MEM-3264fce7-c63f-504e-bdb5-3aaa1169eb7b-document"], "partial", "r5 目录、三个新增实现章节和覆盖元数据", "过程稿按旧八章加新三章排列；共同依据 11 单元，缺失为空。"),
    ("A04", calls["MEM-ef137680-afa6-59b8-a263-f2bb33d256c4-document"], "partial", "r5 当前实现简报及覆盖元数据", "简报先显示实际实现和验证边界，再保留两章历史；与过程稿固定共同依据一致。"),
    ("A04", RUN / "project-ui-attempt-01/process-formula.png", "full", "1440×1000 过程稿第9章截图", "实际看到目录跳到第9章，集合交集/排除公式和累计资源求和公式排版完整，正文及必要定义可读。"),
    ("A04", RUN / "project-ui-attempt-01/brief-desktop.png", "full", "1440×1000 简报首章截图", "目录三章、当前结果及失败/补测表可读；三个 scope 句重复是编辑冗余，不影响含义。"),
    ("A04", RUN / "project-ui-attempt-01/brief-mobile.png", "full", "390×844 简报截图", "窄屏正常换行，侧栏收窄，正文不截断；没有本轮插图，未虚构图像验收。"),
]
saved = {}
for number, (scenario, source, coverage, locator, observation) in enumerate(readings, 1):
    path = RUN / f"project-read-{number:02d}.json"
    ai_review.write_new(path, {"actor": "Codex主任务助手", "origin": "public-cli" if source.suffix == ".txt" else "actual-browser-screenshot",
        "capture_path": str(source), "locator": locator, "coverage": coverage, "observation": observation})
    saved.setdefault(scenario, []).append(str(ai_review.record_read(attempts[scenario], path)))
observations = {
 "A01": ["归属准确，L1/L2/L3 保留未知时间和 Run 引用；实现说明引用固定验证报告。", "已公开预检/提交后 inspect；按真实固定引用 expand 了 U1 和原文来源，正文及 SHA 一致。", "保存/indexed 与科学状态分开；没有 claims accepted 或人工认可。"],
 "A03": ["技术描述明确方法、发现、适用与禁用范围，完整块独立保存。", "实际 section-context 读出所选 implementation、validation 和必需 scope；公式及变量定义完整。", "run_ref=null，未把软件说明伪造为实验；record r1/SHA 和来源指纹可回读。"],
 "A04": ["过程稿11章、简报3章独立保存到r5，公开回读完整，旧r4可读。", "两稿共用11个固定技术单元；简版写明B01、补测、人工/科学/规模与模型边界。", "实际浏览器目录跳转成功，两处公式、正文、验证表及390px窄屏可读，无横向溢出或pageerror；本轮没有插图，旧图支持另由已有Edge用例验证。"],
}
for scenario, values in observations.items():
    path = RUN / ("project-assessment-" + scenario + ".json")
    ai_review.write_new(path, {"actor": "Codex主任务助手", "comparisons": [
        {"expectation_id": scenario + "-E" + str(i), "status": "meets", "observation": value, "evidence_refs": saved[scenario]}
        for i, value in enumerate(values, 1)], "limitations": ["真实调用和AI自查；人工仍待审。", "UI用实际Project字节相同副本；原工作区既有工作台未被中断。", "读取声明按所见范围记录，历史全部章节未重新逐字审查。"]})
    ai_review.record_assessment(attempts[scenario], path)
# Verify read-only UI preservation separately from its visual quality.
fixture = json.loads((RUN / "project-ui-fixture.json").read_text(encoding="utf-8"))
differences = []
for name, expected in fixture["fixed_memory_hashes"].items():
    for owner in (Path(fixture["original"]), Path(fixture["root"]) / "projects/architecture-evolution"):
        if hashlib.sha256((owner / name).read_bytes()).hexdigest() != expected:
            differences.append(str(owner / name))
ai_review.write_new(RUN / "project-ui-preservation.json", {"checked_files_each": len(fixture["fixed_memory_hashes"]), "differences": differences, "unchanged": not differences})
print(ai_review.render(RUN / "actual-ai"))
