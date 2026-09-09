"""最小正式 CLI：JSON 文件输入、JSON 输出，日志及帮助之外不混入正文。"""
import argparse
import json
from pathlib import Path

from .errors import MemoryError, EXIT_CODES


class MemoryParser(argparse.ArgumentParser):
    def error(self, message):
        raise MemoryError("INVALID_ARGUMENT", message)


def add_commands(subparsers):
    # Delay memory imports until dispatch: old unrelated commands must remain
    # available while schema/optional memory capabilities are being upgraded.
    parser = subparsers.add_parser("memory", help="版本记忆：预检、保存、读取、采用与恢复")
    parser.add_argument("memory_args", nargs=argparse.REMAINDER, help="运行 memory --help 查看用法")


def parser():
    result = MemoryParser(prog="workbench.cmd memory", description="版本记忆、证据复核、研究续接与阶段巩固；JSON 请求和可解析回执")
    commands = result.add_subparsers(dest="action", required=True, parser_class=MemoryParser)
    view = commands.add_parser("inspect", help="读取对象或固定记录修订")
    view.add_argument("owner_id")
    view.add_argument("--record-id")
    view.add_argument("--revision", type=int)
    commands.add_parser("list-owners", help="只读列出已有业务对象")
    from .api import ACTIONS, PREVIEW_ACTIONS
    for name in (name for name in ACTIONS if name not in {"inspect", "list-owners", "adopt-owner", "recover"}):
        child = commands.add_parser(name, help="从 UTF-8 JSON 文件读取请求")
        child.add_argument("--request", required=True, type=Path)
        if name in PREVIEW_ACTIONS:
            child.add_argument("--dry-run", action="store_true", help="只校验，不生成业务目录或回执")
    adopt = commands.add_parser("adopt-owner", help="为已有材料创建记忆入口；原文件不变")
    adopt.add_argument("native_ref")
    adopt.add_argument("--expected-hash", required=True)
    adopt.add_argument("--actor", required=True, help="声明执行者 ID，不表示身份认证")
    recover = commands.add_parser("recover", help="检查未完成事务；--apply 仅归档已证明退出的锁")
    recover.add_argument("owner_id")
    recover.add_argument("--apply", action="store_true")
    return result


def execute(root, argv):
    from .service import MemoryService
    from . import owners, recovery
    try:
        args = parser().parse_args(argv)
        service = MemoryService(root)
        if args.action == "inspect":
            if args.revision is not None and (not args.record_id or args.revision < 1):
                raise MemoryError("INVALID_ARGUMENT", "--revision 必须为正整数且与 --record-id 同用")
            value = service.inspect(args.owner_id, args.revision, record_id=args.record_id)
        elif args.action == "list-owners":
            value = {"owners": owners.public_list_owners(root)}
        elif args.action == "adopt-owner":
            value = owners.adopt_owner(root, args.native_ref, args.expected_hash,
                                       actor={"kind": "ai", "id": args.actor})
        elif args.action == "recover":
            value = recovery.recover(root, args.owner_id, apply=args.apply)
        else:
            with args.request.open(encoding="utf-8-sig") as stream:
                request = json.load(stream, parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))
            if getattr(args, "dry_run", False):
                request["dry_run"] = True
            from .api import dispatch
            value = dispatch(service, args.action, request)
        code = EXIT_CODES.get((value.get("error") or {}).get("code"), 0)
        return value, code
    except MemoryError as exc:
        return {"error": exc.as_dict(), "save_status": exc.details.get("save_status", "not_committed")}, exc.exit_code
    except (OSError, ValueError, TypeError, KeyError) as exc:
        # Invalid JSON and input I/O are parseable failures too, not traceback or
        # stderr-only messages which automation could mistake for empty success.
        return {"error": {"code": "INVALID_ARGUMENT", "message": str(exc)}, "save_status": "not_committed"}, 2
