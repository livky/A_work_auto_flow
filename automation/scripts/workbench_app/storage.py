"""工作区内本机状态。固定键、原子写入和排他锁避免覆盖原件及并发丢失。"""
import json
from pathlib import Path
import re
import evidence as e
import retrieval as r


class Store:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.base = self.root / '.local/workbench'

    def path(self, key):
        if not re.fullmatch(r'[a-z0-9_-]+', key):
            raise ValueError('无效的本机记录键')
        raw = self.base / (key + '.json')
        if raw.resolve() != raw:
            raise ValueError('本机状态路径被重定向')
        return raw

    def read(self, key, default=None):
        path = self.path(key)
        return e.read(path) if path.exists() else default

    def update(self, key, change):
        path = self.path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        # 创建父目录后再次核对，防止链接重定向。
        self.path(key)
        with e.locked(path):
            result = change(self.read(key))
            r.write_json(path, result)
        return result

    def write(self, key, value):
        return self.update(key, lambda old: value)


class ServerLease:
    """进程持有的操作系统锁；进程崩溃自动释放，不靠删除猜测的残留锁恢复。"""
    def __init__(self, store):
        path = store.path('server-lease')
        path.parent.mkdir(parents=True, exist_ok=True)
        self.stream = path.open('a+b')
        self.stream.seek(0, 2)
        if self.stream.tell() == 0:
            self.stream.write(b' '); self.stream.flush()
        self.stream.seek(0)
        try:
            if __import__('os').name == 'nt':
                import msvcrt
                msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self.stream.close()
            raise ValueError('此工作区已有新工作台服务，复用其地址或先关闭该服务') from exc

    def close(self):
        if not self.stream.closed:
            self.stream.close()
