"""Живой пробник Revit-AiTools MCP-сервера без сессии и без регистрации в Hermes.

Зачем: сервер может быть живым, но `enabled: false` в config.yaml — тогда инструментов в сессии нет,
а сам MCP отвечает. Этот скрипт доказывает живость по HTTP и печатает состояние Revit.

Использование:
    python scripts/probe_mcp.py                       # авто-поиск порта в 18765-18864
    python scripts/probe_mcp.py --port 18765
    python scripts/probe_mcp.py --tool get_document_info --args '{"title":"x"}'

Правила, зашитые в код (иначе проба врёт):
  * тело JSON уходит аргументом, НЕ через stdin — иначе HTTPAPI отвечает 411 Length Required;
  * отсутствие заголовка Mcp-Session-Id нормально: сервер безассионный, tools/* идут сразу после initialize.
"""

import argparse
import json
import subprocess
import sys

DEFAULT_RANGE = range(18765, 18865)
INIT_BODY = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "probe", "version": "1"},
    },
}


def post(port, payload, timeout=30):
    cmd = [
        "curl", "-s", "-m", str(timeout), "-X", "POST",
        f"http://127.0.0.1:{port}/mcp",
        "-H", "Content-Type: application/json",
        "-H", "Accept: application/json, text/event-stream",
        "-d", json.dumps(payload),
    ]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return None


def discover(ports):
    for port in ports:
        env = subprocess.run(
            ["curl", "-s", "-m", "10", "-X", "POST", f"http://127.0.0.1:{port}/mcp",
             "-H", "Content-Type: application/json",
             "-H", "Accept: application/json, text/event-stream",
             "-D", "-", "-d", json.dumps(INIT_BODY)],
            capture_output=True, text=True).stdout
        if '"serverInfo"' in env:
            info = json.loads(env[env.index("{"):]).get("result", {}).get("serverInfo", {})
            return port, info
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int)
    ap.add_argument("--tool", default="get_document_info")
    ap.add_argument("--args", default="{}")
    args = ap.parse_args()

    port, info = (args.port, None) if args.port else discover(DEFAULT_RANGE)
    if not port:
        print("no live MCP server in 18765-18864: check Revit + ReVibe addin")
        return 2

    post(port, {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
    listed = post(port, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    tools = [t["name"] for t in listed["result"]["tools"]] if listed else []
    print(f"port={port} server={info} tools={len(tools)}")

    called = post(port, {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                         "params": {"name": args.tool, "arguments": json.loads(args.args)}})
    print(json.dumps(called, ensure_ascii=False)[:2000] if called else "tools/call: no JSON")
    return 0


if __name__ == "__main__":
    sys.exit(main())
