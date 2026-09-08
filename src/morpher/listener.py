from __future__ import annotations

import argparse
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from morpher.storage.paths import StoragePaths

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8767
IMPORT_PATH = "/figma/import"


def safe_stem(value: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-._")
    return stem or "figma-node"


def save_figma_import(envelope: dict[str, Any], storage: StoragePaths) -> tuple[Path, bool]:
    name = envelope.get("name")
    payload = envelope.get("payload")

    if not isinstance(name, str) or not name.strip():
        raise ValueError("Request must include a non-empty string 'name'.")
    if not isinstance(payload, dict):
        raise ValueError("Request must include an object 'payload'.")
    if "document" not in payload:
        raise ValueError("Figma JSON_REST_V1 payload must contain 'document'.")

    storage.ensure()
    target = storage.figma_import / f"{safe_stem(name)}.json"
    replaced = target.exists()
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(target)
    return target, replaced


class MorpherRequestHandler(BaseHTTPRequestHandler):
    storage = StoragePaths()

    def _headers(self, status: int) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.end_headers()

    def _json(self, status: int, body: dict[str, Any]) -> None:
        self._headers(status)
        self.wfile.write(json.dumps(body).encode("utf-8"))

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._headers(204)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != IMPORT_PATH:
            self._json(404, {"error": "Not found."})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                raise ValueError("Request body is empty.")
            envelope = json.loads(self.rfile.read(length))
            if not isinstance(envelope, dict):
                raise ValueError("Request body must be a JSON object.")

            target, replaced = save_figma_import(envelope, self.storage)
            self._json(
                200,
                {
                    "ok": True,
                    "filename": target.name,
                    "replaced": replaced,
                },
            )
        except (ValueError, json.JSONDecodeError) as error:
            self._json(400, {"error": str(error)})
        except OSError as error:
            self._json(500, {"error": f"Could not save import: {error}"})

    def log_message(self, format: str, *args: object) -> None:
        print(f"[morpher] {self.address_string()} - {format % args}")


def serve(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, storage_root: Path = Path("storage")) -> None:
    handler = type(
        "ConfiguredMorpherRequestHandler",
        (MorpherRequestHandler,),
        {"storage": StoragePaths(storage_root)},
    )
    server = ThreadingHTTPServer((host, port), handler)
    print(f"Morpher listener: http://{host}:{port}{IMPORT_PATH}")
    print(f"Figma imports: {storage_root / 'figma-import'}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nMorpher listener stopped.")
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Receive Figma plugin exports into Morpher storage.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--storage-root", type=Path, default=Path("storage"))
    args = parser.parse_args()
    serve(args.host, args.port, args.storage_root)


if __name__ == "__main__":
    main()
