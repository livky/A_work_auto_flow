"""有界证据调查：选择、装载、用户覆盖与反馈扩展。

检索分数只产生候选；算法说明是阅读基线，其他角色根据大小和阶段装载。
不调用回答模型，也不伪判问题已解决。AI/用户通过反馈命令明确提供判断，
命令自动执行下一阶段；所有阶段使用已登记来源，保持预算和用户排除项。
"""
import hashlib
import json
from pathlib import Path
import uuid

STAGES = ("focus", "investigate", "wide")
ROLES = {"algorithm", "core-code", "application-code", "run", "research", "knowledge", "project", "document", "media"}


def policy(root):
    import retrieval as r
    value = r.read_json(root / "retrieval/context-policy.json")
    for stage in STAGES:
        for key in ("limit", "related_hops", "optional_sources", "excerpt_chars"):
            if type(value["stages"][stage][key]) is not int or value["stages"][stage][key] < 1:
                raise ValueError(f"context-policy {stage}.{key} 必须为正整数")
    if type(value["max_focus_modules"]) is not int or value["max_focus_modules"] < 1:
        raise ValueError("max_focus_modules 必须为正整数")
    for limit in value["short_full_chars"].values():
        if type(limit) is not int or limit < 1:
            raise ValueError("short_full_chars 必须为正整数")
    preferences = value.get("preferences", {})
    for group in [preferences.get("global", {}), *preferences.get("modules", {}).values()]:
        for key in ("include", "full", "exclude", "exclude_roles"):
            if not isinstance(group.get(key, []), list) or not all(isinstance(v, str) for v in group.get(key, [])):
                raise ValueError(f"偏好 {key} 必须为字符串数组")
        if set(group.get("exclude_roles", [])) - ROLES:
            raise ValueError("偏好中存在未知角色")
    return value


def role(root, doc):
    """显式角色优先；路径只作可覆盖的默认分类，不代表 AI 理解过材料。"""
    meta = doc["meta"]
    if meta.get("context_role"):
        return meta["context_role"]
    path = Path(doc["path"])
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        parts = ()
    if meta.get("assets") or meta.get("units"):
        return "media"
    if meta.get("run_id") or "runs" in parts[0:4] and len(parts) > 2:
        return "run"
    if meta.get("kind") == "code":
        # 普通软件模块不能因文件扩展名被提升为算法核心。默认只信任已
        # 关联算法对象的专用 code/；外部核心实现须登记显式 context_role。
        is_core = (len(parts) > 3 and parts[0] == "core-algorithms"
                   and parts[2] == "code" and meta.get("module_ids"))
        auxiliary = any(p.lower() in {"apps", "app", "ui", "examples", "application", "tests", "utils"} for p in parts)
        return "core-code" if is_core and not auxiliary else "application-code"
    if (len(parts) > 2 and parts[0] == "core-algorithms" and meta.get("module_ids")
            and (parts[2] in {"docs", "algorithm"} or len(parts) == 3 and path.name == "README.md")
            and path.suffix.lower() in {".md", ".txt", ".tex", ".docx", ".pdf"}):
        return "algorithm"
    return parts[0] if parts and parts[0] in {"research", "knowledge", "project"} else ("project" if parts and parts[0] == "projects" else "document")


def run_brief(doc):
    """仅选择原始字段，不生成新结论；保留版本/输入/限制及完整原文入口。"""
    try:
        raw = json.loads(doc["body"])
    except ValueError:
        return None
    if not isinstance(raw, dict) or "run_id" not in raw:
        return None
    keys = ("run_id", "title", "question", "conclusion", "status", "review", "keywords",
            "related_module_ids", "related_research_ids", "inputs", "code", "git", "environment",
            "parameters", "artifacts", "limitations", "parent_run_ids")
    lines = ["# Run 字段摘录（不是完整 Run，也不是 AI 总结）"]
    for key in keys:
        if key in raw:
            text = json.dumps(raw[key], ensure_ascii=False)
            lines.append(f"{key}: {text[:900]}" + (" [字段截断，请查原件]" if len(text) > 900 else ""))
    return "\n".join(lines)


def plan(root, result, cfg, *, stage, focus, include, full, exclude, mode=None):
    import retrieval as r
    formats = r.config(root).get("format_context", {})
    with r.closing(r.connect(root)) as db:
        docs = r.read_docs(db)
    for doc in docs.values():
        doc["meta"]["related"] = [str((root / p).resolve()) for p in doc["meta"].get("related", [])]
    by_path = {doc["path"]: sid for sid, doc in docs.items()}
    missing_preferences = []

    def resolve(values, strict=True):
        ids = set()
        for value in values:
            sid = value if value in docs else by_path.get(str((root / value).resolve()))
            if not sid:
                if strict:
                    raise ValueError(f"上下文选择不在当前可读索引中：{value}；先登记来源并索引")
                missing_preferences.append(value)
            else:
                ids.add(sid)
        return ids

    pref = cfg.get("preferences", {})
    defaults = [pref.get("global", {}), *[pref.get("modules", {}).get(m, {}) for m in focus]]
    selected = {key: resolve([p for group in defaults for p in group.get(key, [])], strict=False)
                for key in ("include", "full", "exclude")}
    # 当前明确选择覆盖持久偏好；同一命令 include/full 与 exclude 冲突时拒绝。
    pinned, forced, blocked = resolve(include), resolve(full), resolve(exclude)
    if (pinned | forced) & blocked:
        raise ValueError("同一来源不能同时加入/全文与排除")
    excluded_roles = {role_name for group in defaults for role_name in group.get("exclude_roles", [])}
    role_excluded = {sid for sid, doc in docs.items() if role(root, doc) in excluded_roles}
    excluded = ((selected["exclude"] | role_excluded) - pinned - forced) | blocked
    forced = (selected["full"] | forced) - excluded
    pinned = (selected["include"] | pinned | forced) - excluded
    roles = {sid: role(root, doc) for sid, doc in docs.items()}
    required = {sid for sid, doc in docs.items() if roles[sid] == "algorithm" and
                set(doc["meta"].get("module_ids", [])) & set(focus)}
    direct = {h["source_id"]: h for h in result["results"]}
    reasons = {sid: "query-hit" for sid in direct}
    for sid in required:
        reasons[sid] = "focus-module-algorithm"
    for sid in pinned:
        reasons[sid] = "user-selected"
    edges = r.relations(docs)
    frontier = set(reasons)
    for depth in range(cfg["stages"][stage]["related_hops"]):
        new = set()
        for sid in sorted(frontier - excluded):
            for target in sorted(edges.get(sid, [])):
                if target not in reasons:
                    reasons[target] = f"relation-hop-{depth+1}"
                    new.add(target)
        frontier = new
    rank = {sid: i for i, sid in enumerate(direct)}
    body_hits = {sid for sid in direct if set(r.tokens(docs[sid]["body"])) & set(result["expanded_terms"])}
    paired_code = set()
    for module_id in focus:
        eligible = [sid for sid in reasons if roles[sid] == "core-code" and sid not in excluded
                    and module_id in docs[sid]["meta"].get("module_ids", [])]
        if eligible:
            paired_code.add(min(eligible, key=lambda sid: (rank.get(sid, 1000), sid)))

    def order(sid):
        # 算法基线先读，再满足用户选择；文档/代码不一致时优先核对实现，
        # 并非因为文档更可信而隐藏冲突代码。应用代码只有命中/显式选择才在首轮加入。
        priority = (0 if sid in required else 1 if sid in pinned else
                    2 if docs[sid]["meta"].get("consistency") == "mismatch" else
                    3 if sid in paired_code else 4 if sid in direct else 5 if roles[sid] == "core-code" else 6)
        return (priority, rank.get(sid, 1000), sid)

    candidates, modes, briefs, inventory, optional = [], {}, {}, [], 0
    stage_index = STAGES.index(stage)
    for sid in sorted(reasons, key=order):
        doc = docs[sid]
        hit = direct.get(sid)
        selected_mode = "full" if sid in required or sid in forced else None
        status = "selected"
        if sid in excluded:
            status = "excluded-by-user"
        elif sid not in required | pinned:
            if optional >= cfg["stages"][stage]["optional_sources"]:
                status = "deferred-by-stage-limit"
            elif (stage == "focus" and roles[sid] in {"application-code", "project"} and
                  sid not in body_hits and doc["meta"].get("consistency") != "mismatch"):
                status = "deferred-unless-hit"
            else:
                optional += 1
        if selected_mode is None:
            selected_mode = doc["meta"].get("context_mode")
        if selected_mode is None:
            threshold = cfg["short_full_chars"].get(roles[sid], 3000) * (1 + stage_index)
            selected_mode = "full" if len(doc["body"]) <= threshold else "excerpt"
            if roles[sid] == "media":
                selected_mode = formats.get(Path(doc["path"]).suffix.lower(), "excerpt")
            if roles[sid] == "run" and len(doc["body"]) > threshold and stage == "focus":
                brief = run_brief(doc)
                if brief:
                    selected_mode, briefs[sid] = "brief", brief
        # 显式命令覆盖自动策略，full 和算法基线优先于全局 excerpt。
        if mode and mode != "auto" and sid not in required | forced:
            selected_mode = mode
        modes[sid] = selected_mode
        inventory.append({"source_id": sid, "path": doc["path"], "role": roles[sid],
                          "module_ids": doc["meta"].get("module_ids", []),
                          "chars": len(doc["body"]), "reason": reasons[sid], "selection": status,
                          "requested_mode": selected_mode, "required": sid in required,
                          "consistency": doc["meta"].get("consistency", "unknown")})
        if status == "selected":
            candidates.append((sid, reasons[sid], hit["span"] if hit else None, hit["digest"] if hit else doc["digest"]))
    return {"candidates": candidates, "modes": modes, "briefs": briefs, "inventory": inventory,
            "focus_modules": focus, "stage": stage, "missing_preferences": missing_preferences,
            "excerpt_chars": cfg["stages"][stage]["excerpt_chars"]}


def create(root, query, *, stage="focus", module=None, project=None, budget=None, mode=None,
           include=(), full=(), exclude=(), parent=None, focus_modules=None, limit=None, trigger_feedback=None):
    import retrieval as r
    if stage not in STAGES:
        raise ValueError("未知上下文阶段")
    cfg = policy(root)
    mode = mode or r.config(root).get("context_mode", "auto")
    result = r.search(root, query, module=None if stage == "wide" else module,
                      project=None if stage == "wide" else project,
                      limit=limit or cfg["stages"][stage]["limit"])
    focus = list(focus_modules or ([module] if module else []))
    if not focus:
        focus = list(dict.fromkeys(m for h in result["results"] for m in h["meta"].get("module_ids", [])))[:cfg["max_focus_modules"]]
    selection = plan(root, result, cfg, stage=stage, focus=focus, include=include, full=full, exclude=exclude, mode=mode)
    pack = r.assemble(root, result, budget, mode, selection=selection)
    context_id = "CTX-" + uuid.uuid4().hex
    manifest = pack["manifest"]
    manifest.pop("related_limit", None)
    manifest.pop("related_omitted_by_limit", None)
    manifest["selection_limits"] = {**cfg["stages"][stage], "limit": limit or cfg["stages"][stage]["limit"]}
    manifest["search_scope"] = {"module": result["module"], "project": result["project"]}
    manifest["note"] = "候选与实际装载分开记录；阶段扩展不改变读取授权，总预算不自动增长。"
    loaded = {s["source_id"]: s for s in manifest["sources"]}
    missing = [i["source_id"] for i in selection["inventory"] if i["required"] and loaded.get(i["source_id"], {}).get("mode") != "full"]
    manifest.update(context_id=context_id, parent_context_id=parent, stage=stage, focus_modules=focus,
                    trigger_feedback_id=trigger_feedback,
                    candidates=selection["inventory"][:40], candidate_count=len(selection["inventory"]),
                    candidate_preview_truncated=len(selection["inventory"]) > 40, required_not_full=missing,
                    missing_preferences=selection["missing_preferences"],
                    next_stage=STAGES[STAGES.index(stage)+1] if stage != "wide" else None,
                    selection_policy="role-stage-v1")
    manifest["module_algorithm_missing"] = [m for m in focus if not any(
        i["required"] and m in i["module_ids"] for i in selection["inventory"])]
    destination = r.inside(root, root / "retrieval/generated" / context_id)
    # 大模块可能关联数千文件，清单本身也不能无界塞入模型上下文。
    # 常用清单只展示前 40 项；全部决策另存文件和调查记录，仍可审计/按需查阅。
    inventory_path = destination.with_suffix(".candidates.json")
    r.write_json(inventory_path, selection["inventory"])
    manifest["candidate_inventory_path"] = str(inventory_path)
    r.write_json(destination.with_suffix(".json"), manifest)
    destination.with_suffix(".md").write_text(pack["text"], encoding="utf-8")
    record = {"context_id": context_id, "created_at": r.now(), "query_id": result["query_id"],
              "parent_context_id": parent, "query": query, "stage": stage, "module": module, "project": project,
              "trigger_feedback_id": trigger_feedback,
              "focus_modules": focus, "budget": budget, "mode": mode,
              "include": list(include), "full": list(full), "exclude": list(exclude),
              "policy_digest": hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest(),
              "candidate_inventory": selection["inventory"],
              "manifest": manifest}
    r.write_json(r.inside(root, root / "retrieval/sessions" / (context_id + ".json")), record)
    return {"context_id": context_id, "query_id": result["query_id"], "stage": stage,
            "context_path": str(destination.with_suffix(".md")), "manifest_path": str(destination.with_suffix(".json")),
            "manifest": manifest, "vector_enabled": result["vector_enabled"], "index_status": result["index_status"]}


def feedback(root, context_id, outcome, actor, note, *, include=(), full=(), exclude=(), query=None):
    """先存真实反馈，再自动扩展；失败反馈不会因扩展过程失败而丢失。"""
    import retrieval as r
    if not context_id.startswith("CTX-") or any(c not in "0123456789abcdef" for c in context_id[4:]) or len(context_id) != 36:
        raise ValueError("context_id 无效")
    if outcome not in {"solved", "unresolved", "conflict"} or not actor.strip() or not note.strip():
        raise ValueError("反馈需要 outcome、actor 和说明证据缺口的 note")
    previous = r.read_json(r.inside(root, root / "retrieval/sessions" / (context_id + ".json")))
    event_id = "CF-" + uuid.uuid4().hex
    event = {"feedback_id": event_id, "context_id": context_id, "outcome": outcome, "actor": actor,
             "refined_query": query,
             "note": note, "created_at": r.now(), "include": list(include), "full": list(full), "exclude": list(exclude)}
    r.write_json(r.inside(root, root / "retrieval/context-feedback" / (event_id + ".json")), event)
    if outcome == "solved":
        return {"feedback": event, "status": "recorded; no expansion"}
    # 两次自动扩展后停止，继续操作需用户/AI给出更具体来源，不无限扩大上下文。
    if previous["stage"] == "wide":
        return {"feedback": event, "status": "expansion-limit; identify missing evidence or refine question"}
    def canonical(value):
        return value if value.startswith("SRC-") else r.source_id((root / value).resolve())
    added = {canonical(v) for v in [*include, *full]}
    removed = {canonical(v) for v in exclude}
    selected_include = list(dict.fromkeys([v for v in previous["include"] if canonical(v) not in removed] + list(include)))
    selected_full = list(dict.fromkeys([v for v in previous["full"] if canonical(v) not in removed] + list(full)))
    selected_exclude = list(dict.fromkeys([v for v in previous["exclude"] if canonical(v) not in added] + list(exclude)))
    try:
        child = create(root, query or previous["query"], stage=STAGES[STAGES.index(previous["stage"])+1],
                       module=previous["module"], project=previous["project"], budget=previous["budget"], mode=previous["mode"],
                       include=selected_include, full=selected_full, exclude=selected_exclude,
                       parent=context_id, focus_modules=previous["focus_modules"], trigger_feedback=event_id)
    except (OSError, ValueError, RuntimeError) as exc:
        return {"feedback": event, "status": "recorded; expansion failed", "error": str(exc)}
    return {"feedback": event, "status": "expanded", **child}
