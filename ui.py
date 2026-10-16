"""One-command launcher for the Smart PDF Analyser UI.

Usage:
    uv run ui.py          # dev mode: start FastAPI + Vite and open the browser
    uv run ui.py --serve  # production mode: build the React app and serve it
                          # through FastAPI on a single port
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
import webbrowser
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parent


def _frontend_dir() -> Path:
    return _repo_root() / "frontend"


def _node_version() -> str | None:
    return shutil.which("node")


def _npm_version() -> str | None:
    return shutil.which("npm")


def _ensure_node_tools() -> None:
    if not _node_version():
        print("error: Node.js is not installed or not on PATH.", file=sys.stderr)
        sys.exit(1)
    if not _npm_version():
        print("error: npm is not installed or not on PATH.", file=sys.stderr)
        sys.exit(1)


def _npm_install(frontend: Path) -> None:
    print("[ui] Installing frontend dependencies…")
    subprocess.run(["npm", "install"], cwd=frontend, check=True)


def _build_frontend(frontend: Path) -> None:
    print("[ui] Building frontend…")
    subprocess.run(["npm", "run", "build"], cwd=frontend, check=True)


def _start_backend(reload: bool = True, static_dir: Path | None = None) -> subprocess.Popen:
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "contract_checker.api:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
    ]
    if reload:
        cmd.append("--reload")

    env = os.environ.copy()
    if static_dir:
        env["FRONTEND_STATIC_DIR"] = str(static_dir)
        print(f"[ui] Serving built frontend from {static_dir}")

    print(f"[ui] Starting FastAPI backend: {' '.join(cmd)}")
    return subprocess.Popen(
        cmd,
        cwd=_repo_root(),
        env=env,
        start_new_session=True,
    )


def _start_vite(frontend: Path) -> subprocess.Popen:
    print("[ui] Starting Vite dev server…")
    return subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=frontend,
        start_new_session=True,
    )


def _terminate(process: subprocess.Popen) -> None:
    if process.poll() is None:
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        except ProcessLookupError:
            process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)


def _dev_mode() -> int:
    _ensure_node_tools()
    frontend = _frontend_dir()

    if not (frontend / "node_modules").exists():
        _npm_install(frontend)

    backend = _start_backend(reload=True)
    vite = _start_vite(frontend)

    time.sleep(2)
    url = "http://localhost:5173"
    print(f"[ui] Opening {url} in the default browser…")
    webbrowser.open(url)

    try:
        backend.wait()
    except KeyboardInterrupt:
        pass
    finally:
        _terminate(vite)
        _terminate(backend)

    return 0


def _serve_mode() -> int:
    _ensure_node_tools()
    frontend = _frontend_dir()

    _npm_install(frontend)
    _build_frontend(frontend)

    dist = frontend / "dist"
    backend = _start_backend(reload=False, static_dir=dist)

    time.sleep(1)
    url = "http://localhost:8000"
    print(f"[ui] Opening {url} in the default browser…")
    webbrowser.open(url)

    try:
        backend.wait()
    except KeyboardInterrupt:
        pass
    finally:
        _terminate(backend)

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Launch the Smart PDF Analyser UI.",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Build the frontend and serve it through FastAPI (default is dev mode).",
    )
    args = parser.parse_args()

    if args.serve:
        return _serve_mode()
    return _dev_mode()


if __name__ == "__main__":
    raise SystemExit(main())
