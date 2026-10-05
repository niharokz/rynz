"""`rynz serve`: a local preview with clean URLs that rebuilds when you save a file.

No JavaScript is injected: after a rebuild, refresh the browser yourself.
"""

from __future__ import annotations

import functools
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from rynz import log
from rynz.build import CACHE_FILE, Builder, report
from rynz.errors import BuildError, RynzError


class CleanURLHandler(SimpleHTTPRequestHandler):
    """Serves /notes from notes.html and /notes/ from notes/index.html, like most static hosts."""

    def translate_path(self, path: str) -> str:
        fs_path = Path(super().translate_path(path))
        if not fs_path.exists() and fs_path.with_name(fs_path.name + ".html").is_file():
            return str(fs_path.with_name(fs_path.name + ".html"))
        return str(fs_path)

    def send_error(self, code, message=None, explain=None):
        page = Path(self.directory) / "404.html"
        if code == 404 and page.is_file():
            body = page.read_bytes()
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().send_error(code, message, explain)

    def log_message(self, fmt, *args):
        log.debug(fmt % args)


def _snapshot(root: Path, skip: Path) -> dict[Path, int]:
    state = {}
    for path in root.rglob("*"):
        if path.is_file() and not path.is_relative_to(skip) and ".git" not in path.parts \
                and path.name != CACHE_FILE and "__pycache__" not in path.parts:
            state[path] = path.stat().st_mtime_ns
    return state


def _build(builder: Builder) -> bool:
    try:
        report(builder.build())
        builder.errors = []
        return True
    except BuildError as exc:
        for err in exc.errors:
            log.error(str(err))
        log.error(str(exc))
    except RynzError as exc:
        log.error(str(exc))
    builder.errors = []
    return False


def serve(root: Path | str = ".", host: str = "127.0.0.1", port: int = 5555, drafts: bool = True,
          watch: bool = True, interval: float = 1.0) -> None:
    root = Path(root).resolve()
    builder = Builder(root, drafts=drafts, incremental=True)
    _build(builder)
    from rynz import config as config_mod

    out = (root / config_mod.load(root, warn_legacy=False).paths["output"]).resolve()
    out.mkdir(parents=True, exist_ok=True)

    handler = functools.partial(CleanURLHandler, directory=str(out))
    httpd = ThreadingHTTPServer((host, port), handler)
    log.ok(f"serving http://{host}:{port}  (drafts {'shown' if drafts else 'hidden'}, Ctrl+C to stop)")

    stop = threading.Event()
    if watch:
        def watcher() -> None:
            state = _snapshot(root, out)
            while not stop.wait(interval):
                current = _snapshot(root, out)
                if current != state:
                    changed = {p for p in current.keys() | state.keys() if current.get(p) != state.get(p)}
                    names = ", ".join(sorted(str(p.relative_to(root)) for p in changed)[:3])
                    log.info(f"[dim]changed: {names} — rebuilding[/dim]")
                    _build(builder)
                    state = _snapshot(root, out)

        threading.Thread(target=watcher, daemon=True).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        log.info("stopped")
    finally:
        stop.set()
        httpd.server_close()
