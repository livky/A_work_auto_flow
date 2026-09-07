"""本地只读证据界面：离线快照或仅监听回环地址的轻量服务。

服务只有固定 GET 路由，不是任意文件服务器；源内容预览仅接受已存在的
对象 ID/引用序号。网页中的材料全部作为文本呈现，不执行其 HTML/脚本。
"""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import secrets
from urllib.parse import parse_qs, urlsplit

import evidence as e
import evidence_observer as observer
import retrieval as r

TEMPLATE = Path(__file__).resolve().parent.parent / "ui/evidence.html"
OUTPUT = "context/generated/evidence-view.html"


def data(root):
    snapshot = observer.collect(root)
    try:
        state = observer.load_state(root)
        snapshot["monitor"] = {"last_checked": state["snapshot"]["observed_at"], "events": state["events"],
            "candidates": list(state["candidates"].values()), "invalid_since": state["invalid_since"]} if state else None
    except (OSError, ValueError) as exc:
        snapshot["monitor"] = {"error": str(exc), "events": [], "candidates": [], "invalid_since": {}}
    return snapshot


def render(payload, live=False):
    # 防止 </script>、HTML 实体及 Unicode 行分隔符从数据区逃逸。
    encoded = json.dumps(payload, ensure_ascii=False).replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    return TEMPLATE.read_text(encoding="utf-8").replace("__LIVE_MODE__", "true" if live else "false").replace("__EVIDENCE_DATA__", encoded)


def export(root):
    root = Path(root).resolve()
    target = e.inside(root, root / OUTPUT)
    if target != root / OUTPUT:
        raise ValueError("快照路径被重定向，拒绝覆盖其他文件")
    target.parent.mkdir(parents=True, exist_ok=True)
    # 派生视图不覆盖原件；先写同目录临时文件再替换。
    import os
    import tempfile
    fd, temp = tempfile.mkstemp(dir=target.parent, prefix=".evidence-view-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(render(data(root)))
        os.replace(temp, target)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    return {"path": str(target), "mode": "snapshot", "note": "离线快照，不会自动刷新或修改复核状态"}


def source(root, nid, index=None, group=None, expected_fingerprint=None):
    """通过已知引用定位文本；不能传入任意 path 或浏览工作区目录。"""
    root = Path(root).resolve()
    graph = e.EvidenceGraph(root)
    if nid not in graph.nodes:
        raise ValueError("找不到证据对象")
    node = graph.nodes[nid]
    if expected_fingerprint is not None and expected_fingerprint != node["fingerprint"]:
        raise ValueError("记录自页面加载后已变化，请刷新后重新选择来源")
    path = node["path"]
    locator = "元数据记录"
    if index is not None:
        if group is not None and group not in {"inputs", "artifacts"}:
            raise ValueError("只支持 inputs/artifacts 预览")
        refs = node["raw"].get(group, []) if group else graph.refs(node)
        if not isinstance(refs, list):
            raise ValueError("引用清单格式无效")
        if index < 0 or index >= len(refs) or not isinstance(refs[index], dict):
            raise ValueError("无效引用序号")
        ref = refs[index]
        target = ref.get("path") if group else ref.get("target")
        path = graph.nodes[target]["path"] if isinstance(target, str) and target in graph.nodes else e.reference_path(root, target)
        locator = group or ref.get("locator") or "未记录定位"
    # CSV/TSV are bounded plain-text previews here, not spreadsheet formula execution.
    if path.suffix.lower() not in set(r.TEXT) | {'.csv', '.tsv'}:
        return {"path": observer.relative(root, path), "locator": locator, "text": "此格式请在获准的本地应用中查看原件。", "truncated": False}
    with path.open("rb") as stream:
        raw = stream.read(65537)
    return {"path": observer.relative(root, path), "locator": locator, "text": raw[:65536].decode("utf-8-sig", errors="replace"),
            "truncated": len(raw) > 65536}


def create_server(root, port=0, controller=None):
    if not 0 <= port <= 65535:
        raise ValueError("port 必须为 0–65535，0 表示自动选择空闲端口")
    root = Path(root).resolve()
    # 十六进制路径保留 192 位随机性，并避免随机单词触发浏览器内容过滤。
    token = secrets.token_hex(24)
    prefix = "/" + token + "/"
    # 新应用与旧只读快照共用同源保护，计算任务由独立应用服务排队。
    from workbench_app import web as app_web
    service = controller.app if controller is not None else None

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass  # URL 包含本机临时访问令牌，不写入访问日志。

        def respond(self, code, body, mime="application/json; charset=utf-8"):
            encoded = body if isinstance(body, bytes) else body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            # Only the legacy standalone evidence document contains inline JS.
            legacy = controller is None or urlsplit(self.path).path == prefix + 'evidence'
            scripts = "'self' 'unsafe-inline'" if legacy else "'self'"
            self.send_header("Content-Security-Policy", f"default-src 'none'; script-src {scripts}; style-src 'self' 'unsafe-inline'; worker-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(encoded)

        def do_GET(self):
            url = urlsplit(self.path)
            expected_host = f"127.0.0.1:{self.server.server_port}"
            # Host 和随机路径同时检查，避免 DNS 重绑定及无意暴露给其他网页。
            if self.headers.get("Host") != expected_host or not url.path.startswith(prefix):
                self.respond(404, '{"error":"not found"}')
                return
            try:
                route = url.path[len(prefix):]
                if service is not None and route.startswith('api/v1/'):
                    self.respond(200, json.dumps(app_web.get(service, route[7:], url.query), ensure_ascii=False))
                    return
                if service is not None and route.startswith('assets/'):
                    raw, mime = app_web.asset(route)
                    self.respond(200, raw, mime)
                    return
                if controller is not None and route == "":
                    raw, mime = app_web.asset('')
                    self.respond(200, raw, 'text/html; charset=utf-8')
                    return
                if controller is not None and route == "api/workbench":
                    self.respond(200, json.dumps(controller.status(), ensure_ascii=False))
                    return
                if controller is not None and route == "api/module":
                    value = controller.module(parse_qs(url.query).get('name', [''])[0])
                    self.respond(200, json.dumps(value, ensure_ascii=False))
                    return
                if controller is not None and route == "evidence":
                    page = render(data(root), live=True)
                    navigation = '<a href="./" style="color:white">← 返回研发工作台</a>'
                    if (root / 'synthetic-marker.json').exists():
                        navigation += '<span>合成测试沙盒 · 非业务证据</span>'
                    self.respond(200, page.replace('<header>', '<header>' + navigation, 1), "text/html; charset=utf-8")
                    return
                if route == "":
                    self.respond(200, render(data(root), live=True), "text/html; charset=utf-8")
                    return
                if route == "api/state":
                    value = data(root)
                elif route == "api/source":
                    args = parse_qs(url.query)
                    value = source(root, args.get("id", [""])[0], int(args["ref"][0]) if "ref" in args else None,
                                   args.get("group", [None])[0], args.get("fingerprint", [None])[0])
                else:
                    self.respond(404, '{"error":"not found"}')
                    return
                self.respond(200, json.dumps(value, ensure_ascii=False))
            except (OSError, ValueError, KeyError, TypeError) as exc:
                self.respond(400, json.dumps({"error": str(exc)}, ensure_ascii=False))

        def do_POST(self):
            if controller is None:
                self.respond(405, '{"error":"read only"}')
                return
            expected_host = f"127.0.0.1:{self.server.server_port}"
            route = urlsplit(self.path).path
            # Exact Origin+Host and token path prevent cross-site form/fetch actions.
            if (self.headers.get("Host") != expected_host or
                self.headers.get("Origin") != "http://" + expected_host or
                not (route == prefix + "api/action" or route.startswith(prefix + 'api/v1/'))):
                self.respond(403, '{"error":"origin or route rejected"}')
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                versioned = route.startswith(prefix + 'api/v1/')
                # Large global Worker cluster membership lists remain local and
                # bounded; ordinary actions retain their smaller request limit.
                cap = 2_000_000 if route == prefix + 'api/v1/clusters' else (500_000 if versioned else 256)
                if self.headers.get("Content-Type") != "application/json" or not 0 < length <= cap:
                    raise ValueError("只接受小型 JSON 动作")
                payload = json.loads(self.rfile.read(length))
                if versioned:
                    name = route[len(prefix + 'api/v1/'):]
                    value = app_web.post(service, name, payload)
                    self.respond(202 if name == 'jobs' else 200, json.dumps(value, ensure_ascii=False))
                    return
                if not isinstance(payload, dict) or set(payload) != {"action"}:
                    raise ValueError("只能传入 action")
                value = controller.action(payload['action'])
                self.respond(200, json.dumps(value, ensure_ascii=False))
            except (OSError, ValueError, KeyError, TypeError) as exc:
                self.respond(400, json.dumps({'error': str(exc)}, ensure_ascii=False))

        def do_PUT(self):
            self.respond(405, '{"error":"read only"}')

        do_DELETE = do_PATCH = do_PUT

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.timeout = 1
    return server, f"http://127.0.0.1:{server.server_port}{prefix}"


def serve(root, port=0):
    server, url = create_server(root, port)
    print(json.dumps({"url": url, "mode": "read-only", "stop": "Ctrl+C"}, ensure_ascii=False), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
