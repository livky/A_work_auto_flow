"""逐项解析工作区/类型/对象/请求策略；只给保存建议，不授权复核。"""
from copy import deepcopy
from .contracts import SCHEMA, validate_schema
from .errors import MemoryError


WORKSPACE_DEFAULTS = {'mode': 'basic', 'retain': [], 'granularity': 'normal',
                      'auto_summary': False, 'discovery': 'owner_only',
                      'auto_deepen': False, 'checkpoint': True}
TYPE_DEFAULTS = {'research': {'mode': 'explore', 'granularity': 'fine',
                             'retain': ['L0', 'L1', 'L2', 'L3', 'L4'],
                             'auto_summary': True}, 'run': {'mode': 'basic'},
                 'project': {'mode': 'basic'}}


def _flatten(value):
    """接受 policy payload 或直接字段映射；缺省不等价于 False。"""
    # 继承层允许省略字段，但字段的类型/枚举完全来自同一正式 schema。
    # 同时支持已保存 payload（mode+overrides）和请求层的直接字段映射。
    # missing_refs 是已知依据缺口，仅校验并保留在记录，不当成执行策略。
    schema = {'type': 'object', 'required': [], 'additionalProperties': False,
              'properties': {**SCHEMA['$defs']['PolicyOverrides']['properties'],
                             **SCHEMA['$defs']['PolicyPayload']['properties']}}
    errors = validate_schema(value, schema, SCHEMA['$defs'])
    if errors:
        raise MemoryError('INVALID_SCHEMA', '策略不符合记忆契约', errors=errors)
    out = {key: deepcopy(val) for key, val in value.items() if key not in {'overrides', 'missing_refs'}}
    out.update(deepcopy(value.get('overrides', {})))
    return out


def resolve(owner, request_overrides=None, *, workspace_defaults=None, type_defaults=None, owner_policy=None):
    """工作区 < 类型 < 对象 < 本次请求，并返回每个字段的最终来源。

    owner 可携带已经由服务读取的 workspace_defaults/type_defaults/policy；
    本函数不读原业务 manifest 中的自由文本规则，也不把叙述当作执行授权。
    显式关键字便于调用服务提供已验证配置，并让测试不依赖磁盘状态。
    """
    values, sources = {}, {}
    workspace = deepcopy(WORKSPACE_DEFAULTS)
    workspace.update(_flatten(owner.get('workspace_defaults', {}) if workspace_defaults is None else workspace_defaults))
    type_policy = dict(TYPE_DEFAULTS.get(owner['owner_type'], {}))
    type_policy.update(_flatten(owner.get('type_defaults', {}) if type_defaults is None else type_defaults))
    explicit = owner.get('policy', {}) if owner_policy is None else owner_policy
    for source, policy in [('workspace', workspace), ('type', type_policy),
                           ('owner', explicit), ('request', {} if request_overrides is None else request_overrides)]:
        for key, value in _flatten(policy).items():
            values[key], sources[key] = value, source
    return {'values': values, 'sources': sources}
