"""Request-body rejection regression: no business actions or source reads."""
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch
from email.message import Message

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import evidence_view


class HttpRejectionTests(unittest.TestCase):
    def test_unsupported_method_consumes_small_body_before_405(self):
        server, _ = evidence_view.create_server(Path.cwd())
        try:
            handler = object.__new__(server.RequestHandlerClass)
            handler.headers = {"Content-Length": "2"}
            handler.rfile = io.BytesIO(b"{}")
            handler.connection = Mock()
            handler.connection.gettimeout.return_value = None
            responses = []
            handler.respond = lambda status, body: responses.append((status, handler.rfile.tell()))
            handler.do_PUT()
            self.assertEqual(responses, [(405, 2)])
        finally:
            server.server_close()

    def test_discard_is_bounded_and_ambiguous_framing_is_not_read(self):
        server, _ = evidence_view.create_server(Path.cwd())
        try:
            for headers in ({"Content-Length": "2000001"}, {"Content-Length": "-1"},
                            {"Content-Length": "invalid"}, {"Content-Length": "2", "Transfer-Encoding": "chunked"}):
                handler = object.__new__(server.RequestHandlerClass)
                handler.headers, handler.rfile, handler.connection = headers, Mock(), Mock()
                handler.respond = Mock()
                handler.do_PUT()
                handler.rfile.read1.assert_not_called()
                self.assertEqual(handler.respond.call_args.args[0], 405)
                self.assertTrue(handler.close_connection)
            duplicates = Message()
            duplicates["Content-Length"] = "2"
            duplicates["Content-Length"] = "3"
            handler.headers = duplicates
            handler.do_PUT()
            handler.rfile.read1.assert_not_called()

            handler.headers = {"Content-Length": "100"}
            handler.connection.gettimeout.return_value = None
            handler.rfile.read1.return_value = b"x"
            # A slow peer cannot reset the total deadline by sending one byte.
            with patch.object(evidence_view.time, "monotonic", side_effect=[0.0, 0.1, 0.6]):
                handler.do_PUT()
            handler.rfile.read1.assert_called_once_with(100)
            self.assertEqual(handler.connection.settimeout.call_args.args, (None,))
            handler.rfile.read1.side_effect = TimeoutError("slow peer")
            handler.do_PUT()
            self.assertEqual(handler.respond.call_args.args[0], 405)
        finally:
            server.server_close()

    def test_readonly_post_delete_patch_retain_rejection_after_drain(self):
        server, _ = evidence_view.create_server(Path.cwd())
        try:
            for method in ("do_POST", "do_DELETE", "do_PATCH"):
                handler = object.__new__(server.RequestHandlerClass)
                handler.headers = {"Content-Length": "18"}
                handler.rfile = io.BytesIO(b'{"action":"shell"}')
                handler.connection = Mock()
                handler.connection.gettimeout.return_value = None
                handler.respond = Mock()
                getattr(handler, method)()
                self.assertEqual(handler.rfile.tell(), 18)
                self.assertEqual(handler.respond.call_args.args[0], 405)
        finally:
            server.server_close()


if __name__ == "__main__":
    unittest.main()
