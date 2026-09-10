"""Create independent SYNTHETIC F3 inputs through public memory transactions.

Run from the repository root with its Python runtime. Native owner cards and
source registration are explicit synthetic bootstrap; canonical memory, HEAD,
versions and index are written only by the public CLI. Existing targets are
refused, so a retry cannot replace recorded inputs or receipts. This script
contains scenario premises, never the AI comparison or acceptance conclusions.
"""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import uuid

REPOSITORY = Path.cwd().resolve()
RUN = Path(__file__).resolve().parent
INPUTS = RUN / "f3-inputs"
ROOT = REPOSITORY / ".local/testing/material-query-f3-20260910-actual/workspace"
CLI = REPOSITORY / "automation/scripts/workspace_cli.py"
ACTOR = {"kind": "ai", "id": "Codex actual-AI F3 setup"}


def save(path, value):
    """Exclusive evidence writes; never use this helper inside memory stores."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n" if not isinstance(value, str) else value
    if "--resume" in sys.argv and path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise ValueError("Resume refuses changed bootstrap bytes: " + str(path))
        return
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def call(label, action, request=None, *, owner=None, record_id=None, revision=None):
    """Capture the exact public command, request and result, including failures."""
    base = INPUTS / "setup-calls" / label
    if "--resume" in sys.argv and (base / "invocation.json").exists():
        captured = json.loads((base / "stdout.txt").read_bytes())
        if captured.get("error") and captured.get("save_status") != "committed":
            raise ValueError("Previous failure needs separate investigation: " + str(base))
        return captured
    base.mkdir(parents=True)
    argv = [sys.executable, str(CLI), "--root", str(ROOT), "memory", action]
    if action == "inspect":
        argv += [owner]
        if record_id:
            argv += ["--record-id", record_id, "--revision", str(revision)]
    else:
        save(base / "request.json", request)
        argv += ["--request", str(base / "request.json")]
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    completed = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True, shell=False, timeout=60)
    (base / "stdout.txt").write_bytes(completed.stdout)
    (base / "stderr.txt").write_bytes(completed.stderr)
    save(base / "invocation.json", {"argv": argv, "cwd": str(ROOT), "exit_code": completed.returncode})
    parsed = json.loads(completed.stdout)
    # INDEX_PENDING is an honest post-commit outcome. Continue from its real
    # fixed record identity and reconcile text explicitly; never repeat a save.
    if completed.returncode and not (parsed.get("save_status") == "committed" and
                                     parsed.get("error", {}).get("code") == "INDEX_PENDING"):
        raise RuntimeError(str(base) + " " + completed.stdout.decode("utf-8", errors="replace"))
    return parsed


def fixed(record, legacy=False):
    result = {"revision": record["revision"], "sha256": record["record_hash"], "locator": ""}
    return {**result, "target_kind": "record", "target_id": record["record_id"], "relation": "references"} if legacy else {
        **result, "kind": "record", "id": record["record_id"]}


def create(label, owner, kind, title, payload, sources):
    head = call(label + "-before", "inspect", owner=owner)["head"]
    draft = {"schema_version": 3, "owner_id": owner, "kind": kind,
        "title": "SYNTHETIC F3 " + title, "body_markdown": "", "keywords": ["SYNTHETIC", "F3", title],
        "payload": payload, "sources": sources, "provenance_gap": None,
        "record_reason": "独立合成前提输入；用于实际 AI 使用检查，非实际试验或科学复核",
        "discovery": "workspace_summary", "sensitivity": "internal"}
    request = {"schema_version": 1, "request_id": str(uuid.uuid4()), "actor": ACTOR, "owner_id": owner,
        "expected_head": head["commit_id"] if head else None,
        "operations": [{"op": "put_record", "client_key": label, "draft": draft}]}
    call(label + "-validate", "validate-draft", request)
    receipt = call(label + "-commit", "commit", request)
    item = receipt["record_results"][0]
    return call(label + "-inspect", "inspect", owner=owner, record_id=item["record_id"], revision=item["revision"])["record"]


def unit(question, method, finding, applicable, not_applicable, limitation, blocks, refs):
    return {"unit_type": "analysis", "retrieval_description": {"question": question, "method": method,
        "key_findings": [finding], "applicable": [applicable], "not_applicable": [not_applicable], "limitations": [limitation]},
        "run_ref": None, "evidence_refs": refs, "blocks": blocks, "figures": [], "missing_refs": []}


TANK_DEFINITIONS = r"""## 必要变量与单位

设水箱横截面积 $A=2\,\mathrm{m^2}$，液位 $h(t)$ 与常值目标 $h_r$ 的单位为 $\mathrm{m}$，时间 $t$ 单位为 $\mathrm{s}$。入流量 $q(t)$ 单位为 $\mathrm{m^3/s}$；出流量采用线性假设 $q_{out}=c h$，其中 $c=0.1\,\mathrm{m^2/s}$。误差定义为 $e=h_r-h$。比例增益 $K\geq0$ 的单位为 $\mathrm{m^2/s}$，使 $K e$ 与流量同量纲。$q_c$ 是未限幅命令，$q_{max}>0$ 是泵的流量上限，二者单位均为 $\mathrm{m^3/s}$。

操作函数 $\operatorname{clip}(x,0,q_{max})=\min(q_{max},\max(0,x))$。初值 $h(0)=h_0\geq0$。传感器、泵在此材料中假设连续、无延迟；未加入噪声、泄漏变化或积分控制。
"""
TANK_MODEL = r"""## 水箱负反馈的线性段

质量守恒与控制律为

$$
A\frac{dh}{dt}=q-ch,\qquad q_c=c h_r+K(h_r-h),\qquad q=\operatorname{clip}(q_c,0,q_{max}).
$$

在整个讨论区间保持 $0<q_c<q_{max}$ 时，可代入 $q=q_c$；目标不变，故

$$
\frac{de}{dt}=-\frac{c+K}{A}e,\qquad e(t)=e(0)\exp\left(-\frac{c+K}{A}t\right).
$$

这是给定合成连续线性模型的代数推导，未做现实实验。若 $A>0,c>0,K\geq0$ 且不触发饱和，误差按该模型指数衰减。时间常数 $\tau=A/(c+K)$，单位为秒。

## 边界

上述指数解只属于未饱和区间；更大目标或初始误差可能使泵触顶或关闭，此时必须返回带 clip 的分段动力学。材料未提供普遍“增益越大越好”的现实结论。尚未测量延迟、噪声与出流非线性，也未验证目标流量是否可达。
"""
RETRY = r"""# SYNTHETIC F3 API 退避与重试

本材料是独立的软件策略前提，没有服务端负载测量、生产日志或成功率试验。

## 变量与机制

$k\in\{0,1,\ldots,N-1\}$ 为当前连续失败后的重试序号；$N=5$ 是总重试上限。$b=0.2\,\mathrm{s}$ 是初始等待，倍率 $r=2$ 无量纲，$d_{max}=3.2\,\mathrm{s}$ 是等待上限。等待策略为

$$
d_k=\min(d_{max},b r^k).
$$

一次请求失败后等待 $d_k$ 再重试，成功后结束本次流程，达到 $N$ 次则停止并返回失败。响应仅有成功/可重试失败/不可重试失败三类，不可重试失败立即停止。本前提没有目标误差 $e$、服务端队列长度、连续流量或物理守恒方程。

## 适用边界

只有具备幂等性或明确去重语义的操作可按此策略重复；必须给超时和最大总耗时单独设限。固定倍率与上限不证明服务端稳定、请求最终成功或最优吞吐。多个客户端同步重试可能同时唤醒；本前提未定义抖动、服务端容量、到达率、成功概率与响应延迟分布。
"""
SATURATION = r"""# SYNTHETIC F3 新材料：执行器饱和约束

这是新收到的独立合成约束输入，没有旧材料 ID、引用或关联边，不是现实实验结果。

## 变量与可达性

水箱模型的面积 $A=2\,\mathrm{m^2}$，出流系数 $c=0.1\,\mathrm{m^2/s}$，液位 $h$ 与目标 $h_r$ 单位为米。新给定泵上限 $q_{max}=0.15\,\mathrm{m^3/s}$，目标 $h_r=2\,\mathrm{m}$。非负泵流量必须满足 $0\leq q\leq q_{max}$，状态方程为 $A\dot h=q-ch$。

在目标液位维持平衡需要 $q=c h_r=0.2\,\mathrm{m^3/s}$，超出给定泵上限。持续饱和时，平衡液位为 $h_{sat}=q_{max}/c=1.5\,\mathrm{m}$，低于目标。仅增大比例增益不能提高泵的物理上限。

## 阅读边界

本材料给出特定合成参数下的代数约束，足以要求重新检查“未饱和”的前提。它不是线性段指数推导错误的证明，也不含真实泵、传感器或延迟数据。对其他目标与流量上限必须重新判断可达性。
"""


def main():
    if not (REPOSITORY / "workspace.json").is_file() or not ROOT.resolve().is_relative_to(REPOSITORY / ".local/testing"):
        raise ValueError("Run only from the repository; isolated target must stay below .local/testing")
    if (ROOT.exists() or INPUTS.exists()) and "--resume" not in sys.argv:
        raise ValueError("Refusing to overwrite an existing F3 target or captured inputs")
    if "--resume" in sys.argv and (not (ROOT / "SYNTHETIC_ONLY.txt").is_file() or not INPUTS.is_dir()):
        raise ValueError("Resume requires this script's existing SYNTHETIC target and inputs")
    ROOT.mkdir(parents=True, exist_ok="--resume" in sys.argv)
    save(ROOT / "workspace.json", {"schema_version": 1, "required_paths": []})
    save(ROOT / "SYNTHETIC_ONLY.txt", "F3 independent actual-AI premises; no real scientific experiment.\n")
    save(ROOT / "tools/registry.json", {"schema_version": 1, "tools": []})
    sources, owners = {}, {"tank": "RES-F3-TANK", "retry": "RES-F3-RETRY", "saturation": "RES-F3-SATURATION"}
    texts = {"tank": "# SYNTHETIC F3 水箱负反馈线性模型\n\n独立合成前提，不是公司算法或现实试验。\n\n" + TANK_DEFINITIONS + "\n" + TANK_MODEL,
        "retry": RETRY, "saturation": SATURATION}
    for alias, text in texts.items():
        save(INPUTS / (alias + ".md"), text)
        owner = owners[alias]
        save(ROOT / f"research/{alias}/research.json", {"research_id": owner, "title": "SYNTHETIC F3 " + alias,
            "status": "active", "claims": [], "dependencies": [], "sensitivity": "internal"})
        path = ROOT / f"research/{alias}/data/合成 输入.md"
        save(path, text)
        sources[alias] = {"source_id": "SRC-F3-" + alias.upper(), "path": path.relative_to(ROOT).as_posix(),
            "enabled": True, "sensitivity": "internal", "sha256": sha(path)}
    save(ROOT / "retrieval/sources.json", {"schema_version": 1, "sources": list(sources.values())})
    refs = {alias: {"target_kind": "file", "target_id": source["source_id"], "revision": None,
        "sha256": source["sha256"], "locator": "完整合成输入", "relation": "input"} for alias, source in sources.items()}
    records = {}
    def block(bid, role, text):
        return {"block_id": bid, "role": role, "markdown": text, "requires_block_ids": []}
    records["tank_definitions"] = create("tank-definitions", owners["tank"], "detail", "水箱必要变量定义", unit(
        "水箱模型采用哪些变量和单位", "固定变量符号、单位与理想化前提", "仅建立合成模型的变量字典", "同一水箱合成前提", "不同单位或物理机制", "没有现实参数辨识",
        [block("definitions", "definitions", TANK_DEFINITIONS)], [refs["tank"]]), [refs["tank"]])
    definition_ref = fixed(records["tank_definitions"], True)
    records["tank_model"] = create("tank-model-v2", owners["tank"], "detail", "水箱线性段误差分析", unit(
        "未饱和水箱负反馈的误差怎样变化", "代入质量守恒并在未饱和区间求解一阶误差方程", "给定无延迟合成模型中，误差在未饱和区间指数衰减", "变量字典一致且全过程未饱和", "执行器饱和、未知延迟或直接外推现实模型", "尚未验证目标可达性；需要同组必要定义",
        [block("model", "methods", TANK_MODEL)], [refs["tank"], definition_ref]), [refs["tank"], {**definition_ref, "relation": "prerequisite"}])
    records["tank_section"] = create("tank-section", owners["tank"], "document_section", "水箱模型完整章节", {
        "section_key": "tank", "title": "SYNTHETIC F3 水箱完整模型：定义、推导与边界", "role": "methods",
        "blocks": [{"type": "prose", "markdown": "本章需要同时阅读变量定义与线性段推导；排除定义会留下解释缺口。", "evidence_refs": []},
                   {"type": "unit", "ref": definition_ref}, {"type": "unit", "ref": fixed(records["tank_model"], True)}],
        "watch_refs": [], "missing_refs": []}, [refs["tank"]])
    for alias, title in (("retry", "API 退避重试策略"), ("saturation", "执行器饱和的新约束")):
        records[alias] = create(alias, owners[alias], "detail", title, unit(
            title + "的机制与约束", "读取独立合成前提并保留变量、公式和限制", "此输入没有真实执行结果",
            "本文明确的合成条件", "现实系统的稳定或性能结论", "缺少实测与科学复核", [block("body", "methods", texts[alias])], [refs[alias]]), [refs[alias]])
    reconcile = call("reconcile", "reconcile", {"vector": "off"})
    manifest = {"fixture": "F3-independent-actual-AI-v1", "root": str(ROOT), "owners": owners, "sources": sources,
        "refs": {key: fixed(value) for key, value in records.items()}, "legacy_refs": {key: fixed(value, True) for key, value in records.items()},
        "record_owners": {key: value["owner_id"] for key, value in records.items()}, "index_result": reconcile,
        "source_markers": "SYNTHETIC F3", "canonical_api": "workspace_cli.py --root TARGET memory validate-draft/commit/inspect",
        "initial_associations": [], "initial_scientific_reviews": [], "execution": "synthetic inputs saved, no physical experiment"}
    save(INPUTS / "manifest.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
