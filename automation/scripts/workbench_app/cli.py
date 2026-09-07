"""材料关系命令。共用应用服务；批量写支持预览，候选处理保留历史。"""
import json
from pathlib import Path
from .service import Service
from .analysis import export_summary


def add_commands(parsers):
    parser = parsers.add_parser('relations', help='材料关系：查看、分析、导出及候选记录')
    parser.add_argument('--root', type=Path, help='指定含 workspace.json 的工作区；默认当前目录')
    actions = parser.add_subparsers(dest='relation_action', required=True)
    refresh = actions.add_parser('refresh', help='重建本机关系投影，不修改业务记录')
    refresh.add_argument('--dry-run', action='store_true')
    for command in ('view', 'export'):
        sub = actions.add_parser(command)
        sub.add_argument('--center', default='')
        sub.add_argument('--hops', type=int, choices=(1, 2), default=1)
        sub.add_argument('--exclude', action='append', default=[])
        sub.add_argument('--type', action='append', default=[])
        sub.add_argument('--candidates', action='store_true')
        sub.add_argument('--question', default='')
        sub.add_argument('--format', choices=('json', 'markdown'), default='json')
    analyze = actions.add_parser('analyze')
    analyze.add_argument('kind', choices=('keywords', 'semantic'))
    analyze.add_argument('--seed', action='append', required=True)
    analyze.add_argument('--exclude', action='append', default=[])
    analyze.add_argument('--dry-run', action='store_true')
    actions.add_parser('candidates', help='列出候选与版本状态')
    imp = actions.add_parser('import-candidate')
    imp.add_argument('file', type=Path)
    imp.add_argument('--dry-run', action='store_true')
    resolve = actions.add_parser('resolve')
    resolve.add_argument('id')
    resolve.add_argument('--status', choices=('pending', 'dismissed', 'handled'), required=True)
    resolve.add_argument('--actor', required=True)
    resolve.add_argument('--note', required=True)
    resolve.add_argument('--dry-run', action='store_true')


def execute(root, args):
    service = Service(root, enable_jobs=False)
    try:
        action = args.relation_action
        if action == 'refresh':
            if args.dry_run:
                from .projection import collect
                value = collect(root)
            else:
                value = service.rebuild()
        elif action in ('view', 'export'):
            graph = service.view({'center': args.center, 'hops': args.hops, 'excluded': args.exclude,
                                  'types': args.type, 'candidates': args.candidates})
            value = export_summary(graph, args.question) if action == 'export' else graph
            if args.format == 'markdown':
                return export_summary(graph, args.question)['markdown']
        elif action == 'analyze':
            value = {'kind': args.kind, 'seeds': args.seed, 'excluded': args.exclude, 'write': '.local/workbench/analysis.json'} if args.dry_run else service.analyze(args.kind, args.seed, args.exclude)
        elif action == 'candidates':
            value = service.candidates()
        elif action == 'import-candidate':
            value = service.save_candidate(json.loads(args.file.read_text(encoding='utf-8-sig')), args.dry_run)
        else:
            value = service.resolve_candidate(args.id, args.status, args.actor, args.note, args.dry_run)
        return json.dumps(value, ensure_ascii=False, indent=2)
    finally:
        service.close()
