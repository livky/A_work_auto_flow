"""按当前选择导出安全、可读的记忆内容；下载不会产生第二份规范记录。"""
import html
import json

from .errors import MemoryError


def export(service, request):
    if type(request.get('include_raw_materials', False)) is not bool:
        raise MemoryError('INVALID_ARGUMENT', 'include_raw_materials 必须为布尔值')
    value = service.inspect(request["owner_id"])
    selected = set(request.get("record_ids", value["records"].keys()))
    selected -= set(request.get("exclude_ids", []))
    unknown = selected - value["records"].keys()
    if unknown:
        raise MemoryError("NOT_FOUND", "导出选择含不可读或不存在的记录")
    records = [r for rid,r in value["records"].items() if rid in selected]
    raw = None
    if request.get('include_raw_materials'):
        from .raw_materials import listing
        raw = listing(service, {'owner_id': request['owner_id']})
        records = [r for r in records if r['kind'] != 'source']
    manifest = {"owner_id": request["owner_id"], "head": value["head"],
                "records": [{k:r[k] for k in ("record_id", "revision", "content_hash")} for r in records],
                "exclude_ids": request.get("exclude_ids", [])}
    if raw is not None:
        manifest['raw_materials'] = raw
    format = request.get("format", "markdown")
    if format == "json":
        content = json.dumps({"manifest": manifest, "records": records}, ensure_ascii=False, indent=2)
    else:
        sections = ["# 记忆导出：" + request["owner_id"]]
        if raw is not None:
            # Export provenance metadata, never automatically copy original files.
            sections.append('## L0 原始材料清单\n\n```json\n' + json.dumps(raw, ensure_ascii=False, indent=2) + '\n```')
        for record in records:
            sections.append("## " + record["title"] + "\n\n" + record["record_id"] + " · r" + str(record["revision"]))
            from .technical_units import is_unit, render_full
            sections.append(render_full(record) if is_unit(record) else record['body_markdown'])
            if record["kind"] == "experience":
                for title, key in (("适用条件", "applicable"), ("禁止迁移条件", "prohibited"), ("失败模式", "failure_modes")):
                    sections.append("### " + title + "\n\n" + "\n".join("- " + text for text in record["payload"][key]))
            sections.append("固定来源：\n\n```json\n" + json.dumps(record["sources"], ensure_ascii=False, indent=2) + "\n```")
        content = "\n\n".join(sections)
        if format == "html":
            # Do not run a Markdown renderer with raw HTML enabled. Exported
            # material is inert text even when its title contains script markup.
            content = '<!doctype html><html lang="zh"><meta charset="utf-8"><title>记忆导出</title><body><pre>' + html.escape(content) + '</pre></body></html>'
        elif format != "markdown":
            raise MemoryError("INVALID_ARGUMENT", "导出格式需为 markdown、json 或 html")
    return {"filename": "memory-export." + {"markdown": "md", "json": "json", "html": "html"}[format],
            "content": content, "manifest": manifest, "canonical_writes": 0}
