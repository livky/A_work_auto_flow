"""Save this analysis Run's observed execution facts, without approving claims."""
from datetime import datetime, timezone
import json
from pathlib import Path

RUN = Path(__file__).resolve().parent
path = RUN / "run.json"
value = json.loads(path.read_text(encoding="utf-8"))
value.update(status="completed", started_at="2026-09-09T19:47:10Z", ended_at=datetime.now(timezone.utc).isoformat(),
    owner="Codex主任务及用户授权协作代理", question="怎样实现表示查询与语义维护首期，并按继承行为、实际AI使用和旧工作区升级分别验证？",
    keywords=["表示查询", "固定引用", "范围硬上限", "累计预算", "局部证据", "语义维护", "Windows升级", "双文稿"],
    parameters={"full_selection": "testing/selection-full-v4.json", "quick_selection": "testing/selection-v2.json", "scale": "deferred", "external_models": "not-enabled"},
    conclusion="P0-P6首期实现和整合执行完成。full原始596/599通过，两项补测关闭；既有B01指纹故障保留。双文稿r5公开回读完整并完成实际UI自查。",
    limitations=["软件与AI自查不等于人工或科学认可", "B01历史冻结指纹故障未关闭", "合成材料和本机隔离目录结果，不外推真实企业质量或第二物理机", "万条规模、未注册策略及依赖包发布未执行"])
value["code"] = {"commit": "647d7862331e283439d06d42ec01d3882a32d163", "dirty": True,
                 "fingerprints": "final-source-fingerprints.json"}
value["quality_results"] = [
    {"name": "full-v4", "status": "failed", "passed": 596, "failed": 2, "errors": 1, "total": 599, "evidence": "testing/full-attempt-01/results.json"},
    {"name": "C17-fixture-supplement", "status": "passed", "evidence": "inheritance-closure-final.json"},
    {"name": "structural-types-supplement", "status": "passed", "evidence": "testing/memory-contracts-supplement-final.log"},
    {"name": "project-documents", "status": "executed", "evidence": "implementation-recording-checks.json"},
    {"name": "project-ui", "status": "ai-reviewed", "evidence": "project-ui-attempt-02/results.json"}]
# The analysis completed even though an independently recorded software suite
# failed. Never replace the suite's failed outcome with the Run execution state.
path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
