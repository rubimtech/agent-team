"""Запуск .csx через Revit MCP: runcsx.py <файл.csx> compile|execute."""
import json
import sys
import urllib.request

URL = "http://127.0.0.1:18765/mcp"  # порт динамический: см. SKILL.md, раздел «Порядок работы»


def rpc(method, params, timeout=120):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(URL, data=body, headers={
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode("utf-8", "replace")
    if raw.startswith("event:") or "\ndata:" in raw[:200]:
        for line in raw.splitlines():
            if line.startswith("data:"):
                raw = line[5:].strip()
                break
    return json.loads(raw, strict=False)


def call(name, args=None, timeout=120):
    return rpc("tools/call", {"name": name, "arguments": args or {}}, timeout)


if __name__ == "__main__":
    path = sys.argv[1]
    stage = sys.argv[2] if len(sys.argv) > 2 else "execute"
    code = open(path, encoding="utf-8").read()
    result = call(f"code_runner_{stage}", {"code": code}, timeout=280)
    print(json.dumps(result, ensure_ascii=False)[:8000])