"""测试/开发使用的契约核对器，仅支持本仓库 Schema 使用的明确子集。

生产服务仍在各操作入口校验输入；这里不宣称实现完整 JSON Schema 标准。
新增未支持关键词时抛错，防止测试静默忽略新约束。
"""
import json
from pathlib import Path


def check_graph(value):
    schema = json.loads((Path(__file__).resolve().parents[2] / 'frontend/contracts/graph.schema.json').read_text(encoding='utf-8'))
    errors = []
    mapping = {'object': dict, 'array': list, 'string': str, 'boolean': bool, 'integer': int, 'number': (int, float), 'null': type(None)}
    def walk(node, rule, path):
        if '$ref' in rule:
            rule = schema['definitions'][rule['$ref'].split('/')[-1]]
        unsupported = set(rule) - {'$schema', 'title', 'type', 'required', 'properties', 'definitions', 'items', 'const', 'description', 'additionalProperties'}
        if unsupported:
            raise ValueError('契约核对器不支持：' + ','.join(unsupported))
        types = rule.get('type', [])
        types = [types] if isinstance(types, str) else types
        if types and not any(isinstance(node, mapping[t]) and not (t in ('integer', 'number') and isinstance(node, bool)) for t in types):
            errors.append(path + ': type mismatch')
            return
        if 'const' in rule and node != rule['const']:
            errors.append(path + ': const mismatch')
        if isinstance(node, dict):
            errors.extend(path + ': missing ' + key for key in rule.get('required', []) if key not in node)
            for key, child in rule.get('properties', {}).items():
                if key in node:
                    walk(node[key], child, path + '.' + key)
        if isinstance(node, list) and 'items' in rule:
            for i, child in enumerate(node):
                walk(child, rule['items'], path + f'[{i}]')
    walk(value, schema, '$')
    return errors
