"""Thin read-mostly JSON-RPC caller for the Revit MCP server.

Usage:  python rpc.py <tool_name> ['{"arg":1}']
Ports:  hardcoded 18765 = first port of the dynamic range; if nothing answers,
        run netstat -ano | grep LISTENING | grep -E ':(187[6-9][0-9]|188[0-6][0-9]) '
        and edit PORT.
Why a script instead of inline curl: the request body must be passed as a FILE
(-d @file) because HTTPAPI rejects chunked bodies with 411, and the file path
must be a NATIVE Windows path -- curl here is a native binary and MSYS path
translation is disabled, so '/tmp/...' or '$TMPDIR/...' silently yields
'curl: option -d: error encountered when reading a file'.
"""
import json
import os
import subprocess
import sys

PORT = 18765
URL = "http://127.0.0.1:%d/mcp" % PORT
WORK = os.path.join(os.environ["LOCALAPPDATA"], "hermes", "cache", "scratch", "mcpcall")


def call(name, args=None, timeout=120):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                       "params": {"name": name, "arguments": args or {}}})
    os.makedirs(WORK, exist_ok=True)
    p = os.path.join(WORK, "b.json")
    with open(p, "w", encoding="utf-8") as f:
        f.write(body)
    r = subprocess.run(["curl", "-s", "-m", str(timeout), "-X", "POST", URL,
                        "-H", "Content-Type: application/json",
                        "-H", "Accept: application/json, text/event-stream",
                        "-d", "@" + p], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    try:
        j = json.loads(r.stdout)
    except Exception:
        return {"_raw": r.stdout[:1500], "_err": r.stderr[:300]}
    c = j.get("result", j)
    if isinstance(c, dict) and "content" in c:
        txt = "".join(x.get("text", "") for x in c["content"])
    else:
        txt = json.dumps(c, ensure_ascii=False)
    if isinstance(c, dict) and c.get("isError"):
        return {"_isError": txt[:1500]}
    return txt


def callj(name, args=None, timeout=120):
    t = call(name, args, timeout)
    try:
        return json.loads(t)
    except Exception:
        return t


def list_tools():
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
    p = os.path.join(WORK, "t.json")
    with open(p, "w", encoding="utf-8") as f:
        f.write(body)
    r = subprocess.run(["curl", "-s", "-m", "20", "-X", "POST", URL,
                        "-H", "Content-Type: application/json",
                        "-H", "Accept: application/json, text/event-stream",
                        "-d", "@" + p], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return [t["name"] for t in json.loads(r.stdout)["result"]["tools"]]


if __name__ == "__main__":
    if sys.argv[1] == "list":
        print("\n".join(list_tools()))
    else:
        print(call(sys.argv[1], json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}))