"""为端到端测试创建本机合成工作区。退出后夹具可由临时目录自动回收。"""
import argparse
from pathlib import Path
import sys
import tempfile
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'automation/scripts'))
sys.path.insert(0, str(ROOT / 'automation/tests'))
import local_test_data
import workbench
from workbench_app.service import Service
from workbench_app.storage import Store
import retrieval as r


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scale', action='store_true')
    parser.add_argument('--reading', action='store_true')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='wb-e2e-', dir=ROOT / '.local') as directory:
        root = local_test_data.build(Path(directory) / '中文 沙盒')
        if args.reading:
            from reading_panel_fixture import populate
            populate(root)
        service = Service(root, enable_jobs=False)
        service.rebuild()
        if args.scale:
            # 只模拟图规模；不将这些节点冒充已导入文件或真实业务记录。
            template = service.graph['nodes'][0]
            nodes = [{**template, 'id': f'N{i}', 'title': f'合成材料 {i}', 'kind': 'material'} for i in range(10_000)]
            edge = service.graph['edges'][0]
            edges = [{**edge, 'id': f'E{i}', 'source': f'N{i % 10_000}', 'target': f'N{(i + 1 + i // 10_000) % 10_000}', 'type': 'references'} for i in range(100_000)]
            Store(root).write('projection', {**service.graph, 'nodes': nodes, 'edges': edges, 'coverage': {'synthetic': True, 'kind': 'in-memory graph performance fixture'}})
        service.close()
        workbench.serve(root, open_browser=False)


if __name__ == '__main__':
    main()
