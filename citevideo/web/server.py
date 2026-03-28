"""
Lightweight local reader UI for CiteVideo package outputs.
"""

from __future__ import annotations

import argparse
import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from citevideo.chat import answer_grounded_question


APP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app")


def _load_json(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_feedback_bundle(run_dir: str) -> dict[str, Any]:
    package_dir = os.path.join(run_dir, "package")
    web_dir = os.path.join(run_dir, "web")

    dossier = _load_json(
        os.path.join(web_dir, "web_dossier.json"),
        _load_json(os.path.join(package_dir, "web_dossier.json"), {}),
    )
    topic_hub = _load_json(
        os.path.join(web_dir, "topic_hub.json"),
        _load_json(os.path.join(web_dir, "topic_hub_fragment.json"), {}),
    )
    chat_index = _load_json(os.path.join(package_dir, "chat_index.json"), {"records": []})
    claims = _load_json(os.path.join(package_dir, "claims.json"), {"claims": []})
    decision_table = _load_json(os.path.join(package_dir, "decision_table.json"), {"rows": []})
    evidence_graph = _load_json(os.path.join(package_dir, "evidence_graph.json"), {"claims": []})

    audits_dir = os.path.join(package_dir, "audits")
    audits = {}
    for name in ("coverage", "policy", "clarity", "trust", "delivery"):
        audits[name] = _load_json(os.path.join(audits_dir, f"{name}.json"), {})

    return {
        "run_id": os.path.basename(run_dir.rstrip(os.sep)),
        "run_dir": run_dir,
        "dossier": dossier,
        "topic_hub": topic_hub,
        "chat_index": chat_index,
        "claims": claims,
        "decision_table": decision_table,
        "evidence_graph": evidence_graph,
        "audits": audits,
    }


def _json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")


def _guess_content_type(path: str) -> str:
    if path.endswith(".css"):
        return "text/css; charset=utf-8"
    if path.endswith(".js"):
        return "application/javascript; charset=utf-8"
    if path.endswith(".html"):
        return "text/html; charset=utf-8"
    return "application/octet-stream"


def create_reader_handler(run_dir: str):
    class ReaderHandler(BaseHTTPRequestHandler):
        def _write(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _write_json(self, status: int, payload: Any) -> None:
            self._write(status, _json_bytes(payload), "application/json; charset=utf-8")

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path or "/"

            if path == "/api/health":
                self._write_json(HTTPStatus.OK, {"ok": True, "run_dir": run_dir})
                return

            if path == "/api/bundle":
                self._write_json(HTTPStatus.OK, load_feedback_bundle(run_dir))
                return

            if path == "/api/answer":
                question = parse_qs(parsed.query).get("question", [""])[0].strip()
                if not question:
                    self._write_json(
                        HTTPStatus.BAD_REQUEST,
                        {"error": "Missing question query parameter."},
                    )
                    return
                self._write_json(
                    HTTPStatus.OK,
                    answer_grounded_question(run_dir, question),
                )
                return

            asset_path = "index.html" if path == "/" else path.lstrip("/")
            fs_path = os.path.join(APP_DIR, asset_path)
            if not os.path.abspath(fs_path).startswith(APP_DIR):
                self._write_json(HTTPStatus.FORBIDDEN, {"error": "Forbidden"})
                return
            if not os.path.exists(fs_path) or not os.path.isfile(fs_path):
                self._write_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
                return

            with open(fs_path, "rb") as handle:
                body = handle.read()
            self._write(HTTPStatus.OK, body, _guess_content_type(fs_path))

    return ReaderHandler


def run_reader_server(run_dir: str, host: str = "127.0.0.1", port: int = 4173) -> None:
    server = ThreadingHTTPServer((host, port), create_reader_handler(run_dir))
    print(f"CiteVideo reader running at http://{host}:{port}")
    print(f"Run directory: {run_dir}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the CiteVideo reader UI.")
    parser.add_argument("run_dir", help="Run directory with package/web outputs")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind")
    parser.add_argument("--port", default=4173, type=int, help="Port to bind")
    args = parser.parse_args()

    run_reader_server(os.path.abspath(args.run_dir), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
