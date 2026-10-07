#!/usr/bin/env python3
"""Экспорт команды ботов RevitAiTools из живых Hermes-профилей в каталог репозитория.

Идемпотентен: повторный запуск перезаписывает agent-team/bots|mcp|skills и MANIFEST.json.
Пути этой машины заменяются плейсхолдерами, чтобы экспорт разворачивался на другой машине
через apply_team.py.

Запуск:  python agent-team/scripts/export_team.py
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys

# ── пути этой машины ──────────────────────────────────────────────────────────
HERMES_HOME = r"C:\Users\olegs\AppData\Local\hermes"
USER_HOME = r"C:\Users\olegs"
REPO = r"D:\DEV\RevitAiTools"
HARNESS = r"D:\DEV\harness-plugins"
KB_MCP = r"D:\DEV\KnowledgeBaseMCP"
SSH_MCP = r"D:/DEV/SRVLLMTOLS/SSH-MCP"

TEAM = [
    ("revit-orchestrator", "full"),
    ("revit-pm", "full"),
    ("revit-ai-dev", "full"),
    ("revit-qa-tester", "full"),
    ("revit-code-reviewer", "reviewer"),
]

HERMES_NATIVE_SKILLS = [
    "revit-mcp-tool-operations",
    "revit-reuse-ladder",
    "revit-ai-agent-console",
    "qdrant-kb-and-cgc-mcp",
    "task-manager",
    "task-manager-insights",
    "verification-dod",
    "agent-org-orchestration",
    "cli-agent-orchestration",
    "revit-donor-porting",
]

OUT = os.path.join(REPO, "agent-team")

SUBS = [
    (HERMES_HOME.replace("\\", "/"), "{{HERMES_HOME}}"),
    (HERMES_HOME, "{{HERMES_HOME}}"),
    (USER_HOME.replace("\\", "/") + "/AppData/Local", "{{LOCALAPPDATA}}"),
    (USER_HOME + "\\AppData\\Local", "{{LOCALAPPDATA}}"),
    (USER_HOME.replace("\\", "/"), "{{USER_HOME}}"),
    (USER_HOME, "{{USER_HOME}}"),
    (REPO.replace("\\", "/"), "{{REPO}}"),
    (REPO, "{{REPO}}"),
    (HARNESS.replace("\\", "/"), "{{HARNESS_PLUGINS}}"),
    (HARNESS, "{{HARNESS_PLUGINS}}"),
    (KB_MCP.replace("\\", "/"), "{{KNOWLEDGEBASE_MCP}}"),
    (KB_MCP, "{{KNOWLEDGEBASE_MCP}}"),
    (SSH_MCP, "{{SSH_MCP}}"),
    (SSH_MCP.replace("/", "\\"), "{{SSH_MCP}}"),
]


def template(text: str) -> str:
    for a, b in SUBS:
        text = text.replace(a, b)
    return text


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def read(p: str) -> str:
    with open(p, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def write(p: str, text: str) -> None:
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def mcp_block(profile: str) -> str:
    cfg = read(os.path.join(HERMES_HOME, "profiles", profile, "config.yaml"))
    if "mcp_servers:" not in cfg:
        raise SystemExit(f"{profile}: нет блока mcp_servers")
    tail = cfg.split("mcp_servers:", 1)[1]
    # блок заканчивается на следующем top-level ключе
    lines = tail.splitlines()
    keep = []
    for ln in lines:
        if ln and not ln.startswith((" ", "\t", "#")) and keep:
            break
        keep.append(ln)
    block = "mcp_servers:" + "\n".join(keep).rstrip() + "\n"
    return template(block)


MANAGED_KEYS = ["model", "agent", "terminal", "skills", "delegation", "memory"]


def managed_blocks(cfg_text: str) -> str:
    """Верхнеуровневые блоки, которые определяют роль бота (модель, тулсеты, cwd, скиллы,
    делегирование, память). Возвращает их как один YAML-текст в фиксированном порядке."""
    lines = cfg_text.splitlines()
    found: dict[str, list[str]] = {}
    i = 0
    while i < len(lines):
        ln = lines[i]
        key = ln.split(":", 1)[0] if ln and not ln[0].isspace() and ":" in ln else None
        if key in MANAGED_KEYS and key not in found:
            block = [ln]
            if ln.strip() in (key + ":", key + ": {}"):
                j = i + 1
                while j < len(lines) and (lines[j].startswith((" ", "\t")) and lines[j].strip()):
                    block.append(lines[j])
                    j += 1
                i = j - 1
            found[key] = block
        i += 1
    out = []
    for k in MANAGED_KEYS:
        if k in found:
            out.extend(found[k])
    return "\n".join(out) + "\n"


def main() -> int:
    manifest = {"generated_from": {"hermes_home": "{{HERMES_HOME}}", "repo": "{{REPO}}"},
                "bots": {}, "mcp": {}, "hermes_native_skills": {}, "templated": True}

    # bots
    for profile, mcp_kind in TEAM:
        src = os.path.join(HERMES_HOME, "profiles", profile)
        if not os.path.isdir(src):
            print(f"!! профиль не найден: {src}")
            continue
        files = {}
        for name in ("SOUL.md", "profile.yaml", "AGENTS.md"):
            sp = os.path.join(src, name)
            if not os.path.exists(sp):
                continue
            dst = os.path.join(OUT, "bots", profile, name)
            write(dst, template(read(sp)))
            files[name] = {"bytes": os.path.getsize(dst), "sha256": sha256(dst)}
        # роль-настройки: модель, тулсеты, cwd, скиллы, делегирование, память
        keys_dst = os.path.join(OUT, "bots", profile, "config-keys.yaml")
        write(keys_dst, template(managed_blocks(read(os.path.join(src, "config.yaml")))))
        if os.path.exists(keys_dst):
            files["config-keys.yaml"] = {"bytes": os.path.getsize(keys_dst), "sha256": sha256(keys_dst)}
        manifest["bots"][profile] = {"files": files, "mcp_set": mcp_kind, "source": f"profiles/{profile}"}
        print(f"bots/{profile}: {', '.join(files)}")

    # mcp
    write(os.path.join(OUT, "mcp", "mcp-servers.full.yaml"), mcp_block("revit-orchestrator"))
    write(os.path.join(OUT, "mcp", "mcp-servers.reviewer.yaml"), mcp_block("revit-code-reviewer"))
    for f in ("mcp-servers.full.yaml", "mcp-servers.reviewer.yaml"):
        p = os.path.join(OUT, "mcp", f)
        servers = re.findall(r"^  ([a-z_0-9-]+):$", read(p), re.M)
        manifest["mcp"][f] = {"servers": servers, "bytes": os.path.getsize(p), "sha256": sha256(p)}
        print(f"mcp/{f}: {servers}")

    # hermes-native skills (их нет в репозитории — копируются целиком)
    skills_root = os.path.join(HERMES_HOME, "skills")
    for skill in HERMES_NATIVE_SKILLS:
        found = None
        for root, dirs, _ in os.walk(skills_root):
            if os.path.basename(root) == skill and "SKILL.md" in os.listdir(root):
                found = root
                break
        if not found:
            print(f"!! скилл не найден: {skill}")
            continue
        dst = os.path.join(OUT, "skills", "hermes-native", skill)
        if os.path.isdir(dst):
            shutil.rmtree(dst)
        shutil.copytree(found, dst)
        n = sum(len(fs) for _, _, fs in os.walk(dst))
        manifest["hermes_native_skills"][skill] = {"files": n,
                                                   "source": template(found)}
        print(f"skills/hermes-native/{skill}: {n} файлов")

    write(os.path.join(OUT, "MANIFEST.json"), json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    total = sum(len(fs) for _, _, fs in os.walk(OUT))
    print(f"\nИтого файлов в agent-team/: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
