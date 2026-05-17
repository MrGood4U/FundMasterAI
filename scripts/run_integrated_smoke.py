import json
import subprocess
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
ENGINE_ROOT = ROOT / "ai_agent" / "fund_llm_engine"


class QuietHTTPRequestHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return


def run_llm_smoke() -> dict:
    sys.path.insert(0, str(ENGINE_ROOT / "src"))
    from fund_llm.mock_pipeline import build_mock_input, run_mock_analysis_for_input

    result = run_mock_analysis_for_input(build_mock_input()).to_dict()
    return {
        "request_id": result["request_id"],
        "overall_rating": result["overall_rating"],
        "agent_count": len(result["agent_outputs"]),
    }


def run_backend_smoke(name: str, cwd: Path) -> dict:
    code = (
        "import json; "
        "from app import create_app; "
        "app = create_app(); "
        "client = app.test_client(); "
        "response = client.get('/'); "
        "print(response.status_code); "
        "print(json.dumps(response.get_json(), ensure_ascii=False))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    lines = completed.stdout.strip().splitlines()
    return {
        "service": name,
        "status_code": int(lines[0]),
        "payload": json.loads(lines[1]),
    }


def run_frontend_smoke() -> dict:
    frontend_dir = ROOT / "frontend_new"
    handler = partial(QuietHTTPRequestHandler, directory=str(frontend_dir))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/index.html"
        with urlopen(url, timeout=10) as response:
            html = response.read().decode("utf-8")
            status = response.status
        return {
            "url": url,
            "status_code": status,
            "has_shell": "FundMaster" in html and "Market Intelligence" in html,
        }
    finally:
        server.shutdown()
        thread.join(timeout=5)


def main() -> int:
    report = {
        "llm": run_llm_smoke(),
        "market_backend": run_backend_smoke(
            "market_backend",
            ROOT / "backend" / "market_backend",
        ),
        "news_backend": run_backend_smoke(
            "news_backend",
            ROOT / "backend" / "news_backend",
        ),
        "frontend": run_frontend_smoke(),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
