"""本次已授权浮点研究语义迁移的固定配方，不是自动改写任意研究的工具。

输入：--root 指定工作区，.local/unified-layers-before.json 为公开 inspect 的完整回读。
输出：.local/unified-layers 下的请求、预检、提交与回读；规范内容只经公开 memory API 写入。
默认 prepare 零规范写入；apply 按固定 request_id 幂等提交，冲突直接非零退出。
旧记录和 Run 均不覆盖；历史恢复可回读旧修订并另建经过审查的新修订。
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
import uuid


OWNER = "RES-FLOATING-POINT-SUMMATION"
NAMESPACE = uuid.UUID("9e7b0cab-a6b5-4d0c-8d28-9e607b0b4773")
QUESTION = "浮点求和中，输入顺序与补偿方法怎样影响大数抵消后的结果？"
LIMITS = ["仅整理已保存的有限整数 binary64 输入与本机结果，未重跑实验。",
          "非整数、极端指数、跨平台和性能尚未验证；研究仍未经过人工科学复核。"]
ROUND_UNITS = ["MEM-c52df8fb-ca9e-53a7-a49b-342592884a50", "MEM-c4a61c00-1bf1-59b3-a65e-0fa4847db2e1",
               "MEM-96f79923-f023-509e-a002-40f2d5a4fca1"]
METHOD = "MEM-4acc73bb-59c7-560d-9415-fd42e9dcaa2d"
EXPERIENCE = "MEM-58fd845a-05a5-516c-8bbe-c88d887cbb91"
OVERVIEW = "MEM-a8226b54-a4cd-545a-8f22-422c2f513bfc"
# 每条原因来自本次实际阅读后的判断；不从旧字段机械生成“已审查”结论。
STAGES = {
    "MEM-eae11b05-09a7-5f4e-a2fd-65fc1ec6000e": (
        "输入顺序改变了小量是否保留，需要先确定误差从哪一步出现。",
        "比较大数先加、小量先加及随后抵消的三种固定输入。",
        "先检查顺序敏感性，再缩小输入以分析补偿机制。", [ROUND_UNITS[0]]),
    "MEM-f1b731ce-9e87-502b-a9cf-a93c3f47c5f6": (
        "第一轮观察到逐次舍入损失，下一步检验采用补偿是否足以消除误差。",
        "枚举三个数 [10^16, 1, -10^16] 的全部六种排列，比较四种方法并检查中间补偿。",
        "三项输入可逐步核对；Kahan 已产生补偿，但补偿在下一步仍可能舍入。", [ROUND_UNITS[1], METHOD]),
    "MEM-77b35d77-f6c1-5d05-80a1-7c3b9d5e9d09": (
        "三项抵消已有反例，需要检查同类结构在更多项与不同排列中是否仍出现。",
        "将三项重复十次，比较保存的三十种三十项排列。",
        "扩大已知抵消结构的有限样本；这些排列不能估计真实业务失败概率。", [ROUND_UNITS[2]]),
    "MEM-d117fbde-ec6b-5168-9a40-f4a25459aa2a": (
        "三轮结果已有，需要补充中间计算轨迹与图表核对。",
        "执行首次逐步复核与绘图命令，分别保存数值输出和失败日志。",
        "绘图依赖导入失败属于执行环境问题，不能据此否定数值方法或原结果。", []),
    "MEM-ff3cf263-e13e-51b3-8a4f-6c7574040f10": (
        "首次复核因绘图环境失败而未完整结束，原失败记录需要保留。",
        "修复绘图依赖可读性后在独立 Run 复试，并核对固定输入与采样配方。",
        "将失败执行与成功复试分别保存，避免把事后补记当成重新实验。", [*ROUND_UNITS, METHOD]),
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if path.exists() and path.read_text(encoding="utf-8-sig") != raw:
        raise RuntimeError(f"拒绝覆盖本次已保存产物：{path.name}")
    path.write_text(raw, encoding="utf-8")


def ref(record):
    return dict(target_kind="record", target_id=record["record_id"], revision=record["revision"],
                sha256=record["record_hash"], locator="完整正文与固定依据", relation="references")


def editable(record):
    from memory.contracts import CONTENT_FIELDS
    value = {key: deepcopy(record[key]) for key in (*CONTENT_FIELDS, "schema_version", "record_reason")}
    value["change_reason"] = "按用户要求实际整理为统一层级；本次审阅旧正文、技术单元与边界，保留原修订和科学复核状态。"
    return value


def request(phase, snapshot, drafts):
    return dict(schema_version=1, request_id=str(uuid.uuid5(NAMESPACE, phase)),
                actor=dict(kind="ai", id="codex-unified-layer-migration"), owner_id=OWNER,
                expected_head=snapshot["head"]["commit_id"], operations=[
                    dict(op="put_record", record_id=rid, expected_revision=snapshot["records"][rid]["revision"], draft=value)
                    for rid, value in drafts.items()])


def narratives(before):
    records, drafts = before["records"], {}
    for rid, (situation, action, reason, technical_ids) in STAGES.items():
        old = records[rid]
        assert old["kind"] == "event"
        p, value = old["payload"], editable(old)
        technical = [ref(records[tid]) for tid in technical_ids]
        # 原来源保持原固定修订；新展开关系另行引用本次读过的最新技术单元。
        sources = [*old["sources"], ref(old), *technical]
        outcome = p["observation"] + " 下一步决定：" + p["decision"]
        body = "\n\n".join(["## 研究情境\n" + situation, "## 做了什么，为什么\n" + action + "\n\n" + reason,
            "## 结果与下一步\n" + outcome, "## 发生时间\n" + (p["occurred_at"] or "原记录未注明"),
            "## 限制\n" + "\n".join("- " + item for item in [*LIMITS, *([p["failure"]["cannot_infer"]] if p["failure"] else [])])])
        payload = dict(question=QUESTION, stages=[dict(situation=situation, action=action, reason=reason,
            outcome=outcome, evidence_refs=[*p["decision_refs"], *technical])], process_refs=[], technical_refs=technical,
            experience_refs=[], limitations=LIMITS, claims=deepcopy(p["claims"]), missing_refs=deepcopy(p.get("missing_refs", [])))
        # 保留发生时间、失败类别与研究关联，使检索/时间线不把迁移时间当发生时间。
        for key in ("occurred_at", "failure", "goal_ref", "route_ref", "question_refs", "run_refs"):
            payload[key] = deepcopy(p[key])
        value.update(schema_version=4, kind="narrative", payload=payload, body_markdown=body, sources=sources,
                     keywords=["浮点求和", "数值稳定性", "研究经过"])
        drafts[rid] = value
    return request("narratives", before, drafts)


def experience(current):
    records = current["records"]
    old = records[EXPERIENCE]
    value = editable(old)
    value["schema_version"] = 4
    value["payload"].update(knowledge_type="recommendation", process_refs=[ref(records[rid]) for rid in STAGES],
                            technical_refs=[ref(records[rid]) for rid in [METHOD, *ROUND_UNITS]])
    value["sources"].append(ref(old))
    return request("experience", current, {EXPERIENCE: value})


def overview(current):
    records = current["records"]
    old = records[OVERVIEW]
    value = editable(old)
    results = ["第一轮：逐项累加精确 1/3，最大绝对误差 1000；math.fsum 精确 3/3。",
               "第二轮六种排列：逐项累加与 Kahan 各精确 2/6；Neumaier 与 math.fsum 各精确 6/6。",
               "第三轮三十种排列：逐项累加精确 0/30、Kahan 5/30，最大绝对误差均为 10；Neumaier 与 math.fsum 各精确 30/30。"]
    process = [ref(records[rid]) for rid in STAGES]
    technical = [ref(records[rid]) for rid in [METHOD, *ROUND_UNITS]]
    body = "\n\n".join(["## 研究要回答什么\n" + QUESTION,
        "## 研究怎么推进\n先比较顺序造成的小量损失，再用三项输入逐步分析补偿，最后扩大到三十项的三十种固定排列。精确基准针对程序实际收到的 binary64 输入，不混入十进制转换误差。",
        "## 已得到的结果\n" + "\n".join("- " + item for item in results),
        "## 复核经过\n首次逐步复核留下绘图依赖导入失败；后续独立复试核对了 150 个最终结果和精确误差、111 组算法轨迹及 30 组采样配方。保留两次 Run，环境执行失败与数值反例分别解释。",
        "## 当前阶段与适用边界\n本组三轮计算已完成。可以复用的是固定输入、精确参考和逐步核对的方法；不能从有限命中率推出任意输入都精确，亦未作性能排名。研究仍为 not-reviewed。",
        "## 后续要补什么\n非整数输入、极端指数与溢出边界、跨平台复算，以及独立性能测量。",
        "## 阅读入口\n本条概览明确关联五段研究经过、一条经验和四个技术单元，可继续展开。完整研究过程与简版研究报告仍是独立文稿，在工作台研究经过页阅读；其固定来源也保留在本条记录中。"])
    value.update(schema_version=4, kind="overview", title="浮点求和数值稳定性：整体概览", body_markdown=body,
        sources=[*old["sources"], ref(old), *old["payload"].get("document_refs", []), *process, *technical, ref(records[EXPERIENCE])],
        payload=dict(question=QUESTION, methods=["精确有理数参考", "输入顺序与补偿方法比较", "固定排列与逐步轨迹复核"],
            results=results, current_stage="三轮有限构造实验及独立复试已完成；扩展研究尚未开始",
            limitations=LIMITS, open_questions=["非整数与极端指数下的误差边界", "跨平台复算", "独立性能测量"],
            process_refs=process, technical_refs=technical, experience_refs=[ref(records[EXPERIENCE])], claims=[], missing_refs=[]))
    return request("overview", current, {OVERVIEW: value})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("phase", choices=["prepare", "apply", "rebuild"])
    args = parser.parse_args()
    root = args.root.resolve()
    sys.path.insert(0, str(root / "automation/scripts"))
    from memory import api
    from memory.service import MemoryService
    service = MemoryService(root)
    out = root / ".local/unified-layers"
    before = read(root / ".local/unified-layers-before.json")
    assert before["owner"]["owner_id"] == OWNER
    if args.phase == "prepare":
        req = narratives(before)
        write(out / "narratives-request.json", req)
        print(json.dumps(api.dispatch(service, "validate-draft", req), ensure_ascii=False, indent=2))
        return
    if args.phase == "rebuild":
        value = api.dispatch(service, "rebuild", {"scope": [OWNER], "vector": "required"})
        write(out / "rebuild.json", value)
        print(json.dumps(value, ensure_ascii=False, indent=2))
        if value["index_status"] != "indexed":
            raise RuntimeError("索引尚未完成")
        return
    for phase, author in (("narratives", None), ("experience", experience), ("overview", overview)):
        path = out / (phase + "-request.json")
        if not path.exists():
            current = api.dispatch(service, "inspect", {"owner_id": OWNER})
            write(path, author(current))
        req = read(path)
        # 公共 commit 的固定 request_id 可安全回放已完成阶段；不更换 ID 强行重试。
        value = api.dispatch(service, "commit", req)
        write(out / (phase + "-receipt.json"), value)
        if value["save_status"] != "committed":
            raise RuntimeError(json.dumps(value, ensure_ascii=False))
        print(phase, value["save_status"], value["index_status"], flush=True)
    current = api.dispatch(service, "inspect", {"owner_id": OWNER})
    write(out / "after.json", current)
    assert not any(r["kind"] in {"event", "map"} for r in current["records"].values())
    for rid in [*STAGES, EXPERIENCE, OVERVIEW]:
        old = before["records"][rid]
        actual = api.dispatch(service, "inspect", {"owner_id": OWNER, "record_id": rid, "revision": old["revision"]})["record"]
        assert actual == old, "旧固定修订必须完全保持"
    print("当前类型已统一；七条旧修订逐条回读完全一致。", flush=True)


if __name__ == "__main__":
    main()
