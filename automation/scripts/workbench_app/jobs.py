"""单工作区任务队列。HTTP 不运行重计算；只有完整成功结果可以替换缓存。"""
from concurrent.futures import ThreadPoolExecutor
import threading
import uuid
import retrieval as r
from .storage import ServerLease


class Cancelled(Exception):
    pass


class Jobs:
    def __init__(self, store):
        self.store = store
        self.lease = ServerLease(store)
        self.lock = threading.RLock()
        self.events = {}
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='workbench-job')
        self.items = store.read('jobs', {})
        for item in self.items.values():
            if item['status'] in ('queued', 'running'):
                item.update(status='interrupted', error='上次服务已结束；需手动重试')
        if self.items:
            self._save()

    def _save(self):
        self.store.write('jobs', self.items)

    def submit(self, kind, operation):
        with self.lock:
            if sum(i['status'] in ('queued', 'running') for i in self.items.values()) >= 10:
                raise ValueError('任务队列已满，请等待或取消现有任务')
            jid = uuid.uuid4().hex
            event = threading.Event()
            self.events[jid] = event
            self.items[jid] = {'id': jid, 'kind': kind, 'status': 'queued', 'done': 0, 'total': 0,
                               'created_at': r.now(), 'error': None, 'result': None}
            self._save()
        def run():
            def progress(done, total):
                if event.is_set():
                    raise Cancelled('任务已取消；未替换上次完整缓存')
                with self.lock:
                    self.items[jid].update(done=done, total=total)
            try:
                progress(0, 0)
                with self.lock:
                    self.items[jid]['status'] = 'running'
                    self._save()
                result = operation(progress)
                # operation 在每个批次以及缓存提交前检查取消。
                with self.lock:
                    self.items[jid].update(status='succeeded', result=result)
            except Cancelled as exc:
                with self.lock:
                    self.items[jid].update(status='cancelled', error=str(exc))
            except Exception as exc:
                with self.lock:
                    self.items[jid].update(status='failed', error=str(exc))
            finally:
                with self.lock:
                    self.items[jid]['ended_at'] = r.now()
                    self._save()
        self.pool.submit(run)
        return dict(self.items[jid])

    def list(self):
        with self.lock:
            return [dict(i) for i in reversed(list(self.items.values()))]

    def cancel(self, jid):
        with self.lock:
            if jid not in self.items:
                raise ValueError('找不到任务')
            if jid in self.events:
                self.events[jid].set()
            return dict(self.items[jid])

    def close(self):
        for event in self.events.values():
            event.set()
        self.pool.shutdown(wait=True, cancel_futures=False)
        self.lease.close()
