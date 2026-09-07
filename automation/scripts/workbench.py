"""本机统一入口。后台只读监测随本进程退出，没有开机任务或自动信任晋升。

HTTP 动作采用固定白名单和同源校验，不接受命令、路径或 shell 参数。
后台监测与手动监测共享锁；异常明确显示，不能当作“没有变化”。
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import threading
import webbrowser

import evidence_observer as observer
import evidence_view

TEMPLATE = Path(__file__).resolve().parent.parent / 'ui/workbench.html'
MODULES = {'core-algorithms': '核心算法', 'runs': '实验与分析', 'research': '专题研究',
           'knowledge': '可复用知识', 'data': '数据目录与契约', 'reports': '报告',
           'projects': '交付项目', 'tools': '工具', 'retrieval': '检索配置', 'context': '导航与记录'}


class Controller:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.stop_event = threading.Event()
        self.thread = None
        self.operation = threading.Lock()
        self.state_lock = threading.Lock()
        self.last_result = None
        self.error = None
        self.capabilities = None
        self.interval = 60
        from workbench_app.service import Service
        self.app = Service(self.root, self)

    def status(self):
        with self.state_lock:
            return {'root': str(self.root), 'synthetic': (self.root / 'synthetic-marker.json').exists(),
                    'monitor_running': bool(self.thread and self.thread.is_alive() and not self.stop_event.is_set()),
                    'interval_seconds': self.interval, 'result': self.last_result, 'error': self.error,
                    'capabilities': self.capabilities,
                    'modules': [{'path': p, 'title': title, 'exists': (self.root / p).is_dir()} for p, title in MODULES.items()]}

    def module(self, name):
        """模块目录只接受内置键；展示小型文件清单，不执行工具或读取外部原件。"""
        if name not in MODULES:
            raise ValueError('未知模块')
        import workspace_cli as cli
        files = []
        from itertools import chain
        tabular = (p for p in (self.root / name).rglob('*.csv')
                   if not cli.is_excluded(p.relative_to(self.root / name), ['generated'])
                   and p.is_file() and p.stat().st_size <= 1_000_000)
        for path in chain(cli.iter_small_text_files(self.root / name), tabular):
            if path.resolve().is_relative_to(self.root) and '_template' not in path.parts:
                files.append(path.relative_to(self.root).as_posix())
            if len(files) >= 40:
                break
        return {'title': MODULES[name], 'files': sorted(files), 'limit': 40}

    def monitor(self):
        if not self.operation.acquire(blocking=False):
            raise ValueError('已有监测正在执行，请稍后刷新')
        try:
            result = observer.monitor(self.root)
            if result.get('errors'):
                raise ValueError('; '.join(result['errors']))
            with self.state_lock:
                self.last_result, self.error = result, None
            return result
        except Exception as exc:
            with self.state_lock:
                self.error = str(exc)
            raise
        finally:
            self.operation.release()

    def loop(self):
        while not self.stop_event.is_set():
            try:
                self.monitor()
            except Exception:
                pass  # monitor already recorded the failure for the UI.
            self.stop_event.wait(self.interval)

    def action(self, name):
        if name == 'monitor':
            self.monitor()
        elif name == 'start-monitor':
            if self.thread and self.thread.is_alive():
                if self.stop_event.is_set():
                    raise ValueError('上一轮正在停止，等待当前扫描完成后重试')
            else:
                self.stop_event.clear()
                self.thread = threading.Thread(target=self.loop, daemon=True, name='read-only-monitor')
                self.thread.start()
        elif name == 'stop-monitor':
            self.stop_event.set()
        elif name == 'doctor':
            import health
            result = health.doctor(self.root)
            with self.state_lock:
                self.capabilities = result['capabilities']
        else:
            raise ValueError('未知工作台动作')
        return self.status()

    def close(self):
        self.stop_event.set()
        self.app.close()
        # Allow atomic state writes to finish; no new scan starts after this signal.
        if self.thread:
            self.thread.join(timeout=5)


def serve(root, port=0, open_browser=True):
    # 启动时一次性验证发布源码；不在五秒轮询中反复读取源码。
    from workbench_app.web import asset_manifest
    import hashlib
    manifest = asset_manifest()
    frontend = Path(__file__).resolve().parents[1] / 'frontend'
    for name, fingerprint in manifest.get('sources', {}).items():
        path = frontend / name
        if path.resolve() != path or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != fingerprint:
            raise ValueError('前端源码和资源不匹配，请重新构建或安装完整版本：' + name)
    control = Controller(root)
    server, url = evidence_view.create_server(root, port, controller=control)
    print(json.dumps({'url': url, 'stop': 'Ctrl+C', 'monitor': '在工作台手动开启；关闭终端即停止'}, ensure_ascii=False), flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        control.close()
        server.server_close()
