"""按Owner发现阅读会话；只读有界目录，不建立第二份RS索引或知识真源。"""
from itertools import islice
import json
from .budget import DEFAULT_BUDGET, Ledger
from .coordinator import envelope
from .reading import BASE, path, read_json, require
from .validation import object_fields, QueryError
from memory.errors import MemoryError


def listing(reading, raw):
    object_fields(raw, set(), {'owner_id', 'offset', 'limit', 'include_archived'})
    offset, limit = raw.get('offset', 0), raw.get('limit', 20)
    require(type(offset) is int and offset >= 0, 'offset必须为非负整数')
    require(type(limit) is int and 1 <= limit <= 50, 'limit必须为1到50')
    require(type(raw.get('include_archived', False)) is bool, 'include_archived必须是布尔值')
    oid = raw.get('owner_id')
    require(oid is None or isinstance(oid, str) and bool(oid.strip()), 'owner_id必须是非空字符串')
    # 目录元数据盘点独立受有界预算约束；不执行研究召回或模型编码，
    # 也不返回笔记正文。查看正文仍走view的持久会话账本。
    reading.ledger = Ledger(DEFAULT_BUDGET)
    base = reading.root / BASE
    paths = list(islice(base.glob('RS-*/HEAD.json'), 10001)) if base.exists() else []
    require(len(paths) <= 10000, '阅读目录超过10000会话，需维护目录容量后重试；归档标记不会删除目录')
    paths.sort(key=lambda item: item.parent.name)
    selected = paths[offset:offset + limit]
    items, unavailable = [], 0
    with reading.ledger.active():
        for candidate in selected:
            try:
                file = path(reading.root, candidate.parent.name, 'HEAD.json')
                reading.ledger.charge('read_bytes', file.stat().st_size)
                session = read_json(file)
                if session['access'] != reading.access():
                    continue
                if oid is not None and session.get('owner_id') != oid:
                    continue
                if session.get('archived') and not raw.get('include_archived', False):
                    continue
                state = reading.state(session)
                reading.reauthorize(session, state)
                item = {key: session.get(key) for key in ('session_id', 'revision', 'owner_id', 'goal', 'phase', 'archived')}
                reading.ledger.charge('output_chars', len(json.dumps(item, ensure_ascii=False)))
                items.append(item)
            except (QueryError, MemoryError, OSError, ValueError, KeyError):
                # 不泄漏不可读会话的身份、目标或路径；其他会话仍可查看。
                unavailable += 1
    next_offset = offset + len(selected) if offset + len(selected) < len(paths) else None
    result = envelope({'items': items, 'next_offset': next_offset, 'unavailable_count': unavailable,
                       'scope_note': '按目录窗口筛选；空页仍可能有下一页。未绑定旧会话用全局列表发现后显式bind。'})
    result['consumed'] = reading.ledger.snapshot()
    return result
