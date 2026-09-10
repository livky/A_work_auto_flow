"""Archive post-reading AI declarations; never infer or generate judgments."""
from pathlib import Path
import json
import sys

REPOSITORY = Path.cwd().resolve()
RUN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY / "automation/testing"))
import ai_review

attempts = json.loads((RUN / "f3-inputs/attempts.json").read_text(encoding="utf-8"))["attempts"]
results = {}
for scenario, raw in attempts.items():
    attempt = Path(raw)
    reads = [str(ai_review.record_read(attempt, path)) for path in sorted((attempt / "authored-review").glob("read-*.json"))]
    assessment = ai_review.record_assessment(attempt, attempt / "authored-review/assessment.json")
    results[scenario] = {"reads": reads, "assessment": str(assessment)}
report = ai_review.render(RUN / "actual-ai")
result = {"saved": results, "report": str(report)}
with (RUN / "f3-inputs/review-receipt.json").open("x", encoding="utf-8") as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
print(json.dumps(result, ensure_ascii=False, indent=2))
