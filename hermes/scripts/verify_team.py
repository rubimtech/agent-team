#!/usr/bin/env python3
"""Проверка развёрнутой команды ботов: профиль, модель, Bot Chat, MCP, скиллы, ключ, AGENTS.md.

Запуск:  python agent-team/scripts/verify_team.py [--hermes-home PATH]
Код возврата 0 — все боты в порядке; 1 — есть находки.
"""
from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys

TEAM = ["revit-orchestrator", "revit-pm", "revit-ai-dev", "revit-qa-tester", "revit-code-reviewer"]
EXPECT_MCP = {"revit-orchestrator": 9, "revit-pm": 9, "revit-ai-dev": 9,
              "revit-qa-tester": 9, "revit-code-reviewer": 7}

HEADER = f"{'bot':20} {'title':22} {'model(cfg)':24} {'BotChat':24} {'soul':>6} {'mcp':>4} {'key':>4} {'AGENTS':>7}"


def read(p: str) -> str:
    with open(p, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def mcp_block(cfg: str) -> str:
    """Верхнеуровневый блок mcp_servers: от ключа до следующего ключа в 0-й колонке."""
    if "mcp_servers:" not in cfg:
        return ""
    lines = cfg.split("mcp_servers:", 1)[1].splitlines()
    keep: list[str] = []
    for ln in lines:
        if ln and not ln[0].isspace() and keep:
            break
        keep.append(ln)
    return "\n".join(keep)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hermes-home", default=os.environ.get("HERMES_HOME") or
                    os.path.join(os.environ.get("LOCALAPPDATA", ""), "hermes"))
    args = ap.parse_args()
    base = os.path.join(os.path.abspath(args.hermes_home), "profiles")

    print(HEADER)
    print("-" * len(HEADER))
    findings: list[str] = []
    for p in TEAM:
        d = os.path.join(base, p)
        if not os.path.isdir(d):
            findings.append(f"{p}: профиль отсутствует ({d})")
            continue
        title = model_cfg = "?"
        prof = os.path.join(d, "profile.yaml")
        if os.path.exists(prof):
            m = re.search(r"title:\s*'?([^'\n]+)'?", read(prof))
            title = m.group(1).strip() if m else "НЕТ ui_meta.hermes-bots.title"
        else:
            findings.append(f"{p}: нет profile.yaml")
        cfg_path = os.path.join(d, "config.yaml")
        cfg = read(cfg_path) if os.path.exists(cfg_path) else ""
        m = re.search(r"^model:\n(?:.*\n)*?\s*default:\s*(\S+)", cfg, re.M)
        model_cfg = m.group(1) if m else "?"
        block = mcp_block(cfg)
        tops = [l.split(":", 1)[0] for l in cfg.splitlines()
                if l and not l[0].isspace() and ":" in l and not l.startswith("#")]
        dups = sorted({k for k in tops if tops.count(k) > 1})
        if dups:
            findings.append(f"{p}: дублирующиеся ключи верхнего уровня в config.yaml: {dups}")
        servers = re.findall(r"^  ([a-z_0-9-]+):$", block, re.M)
        disabled_servers = len(re.findall(r"enabled: false", block))
        bc = "MISSING"
        db = os.path.join(d, "state.db")
        if os.path.exists(db):
            try:
                c = sqlite3.connect(db)
                rows = c.execute("select model from sessions where title='Bot Chat'").fetchall()
                bc = f"{len(rows)}x {rows[0][0]}" if rows else "MISSING"
            except Exception as e:  # noqa: BLE001
                bc = f"ERR {e}"
        soul = os.path.getsize(os.path.join(d, "SOUL.md")) if os.path.exists(os.path.join(d, "SOUL.md")) else 0
        env_p = os.path.join(d, ".env")
        key = "ok" if os.path.exists(env_p) and "ROUTERAI_API_KEY" in read(env_p) else "НЕТ"
        ag = "yes" if os.path.exists(os.path.join(d, "AGENTS.md")) else "no"
        print(f"{p:20} {title[:22]:22} {model_cfg[:24]:24} {bc[:24]:24} {soul:6} {len(servers):4} {key:>4} {ag:>7}")

        if bc == "MISSING":
            findings.append(f"{p}: нет сессии 'Bot Chat' (Bots-таб его не увидит)")
        if key == "НЕТ":
            findings.append(f"{p}: в .env нет ключа провайдера (hermes -p {p} setup)")
        if soul < 3000:
            findings.append(f"{p}: подозрительно маленький SOUL.md ({soul} байт)")
        if len(servers) != EXPECT_MCP[p]:
            findings.append(f"{p}: MCP-серверов {len(servers)}, ожидалось {EXPECT_MCP[p]}")
        if disabled_servers:
            findings.append(f"{p}: {disabled_servers} MCP-сервер(а) помечены enabled: false "
                            f"(не разрешились пути — см. apply_team.py)")
        if not os.path.isdir(os.path.join(os.path.dirname(base), "skills-revita")):
            findings.append(f"{p}: нет общего каталога skills-revita")

    print()
    if findings:
        print("НАХОДКИ:")
        for f in findings:
            print(f"  ! {f}")
        return 1
    print("ВСЁ ОК")
    return 0


if __name__ == "__main__":
    sys.exit(main())
