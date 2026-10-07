#!/usr/bin/env python3
"""Разворачивает команду ботов RevitAiTools на машине (в т.ч. чистой).

Что делает (идемпотентно, повторный запуск не плодит дублей):
  1. находит пути этой машины (HERMES_HOME, REPO, node, python, uvx, внешние MCP-проекты);
  2. создаёт 5 Hermes-профилей (если их нет) и пишет в них SOUL.md / AGENTS.md / profile.yaml
     из agent-team/bots/<профиль>/ с подстановкой плейсхолдеров;
  3. прописывает блок mcp_servers (mcp/mcp-servers.full.yaml | reviewer.yaml) в config.yaml
     каждого профиля; сервера, чьи пути не разрешились, помечает disabled и перечисляет в отчёте;
  4. пиннит модель (config.yaml + sessions.model) и создаёт сессию "Bot Chat";
  5. собирает общий каталог скиллов <HERMES_HOME>/skills-revita из {{REPO}}/.kilo/skills
     + agent-team/skills/hermes-native, пропуская дубли по frontmatter name;
  6. печатает отчёт: что установлено, что требует ручной установки.

Запуск:
  python agent-team/scripts/apply_team.py                 # план, ничего не пишет
  python agent-team/scripts/apply_team.py --apply          # развернуть
  python agent-team/scripts/apply_team.py --apply --smoke  # + живой смоук каждого бота

Секреты не печатает: ключ провайдера переносится построчно из <HERMES_HOME>/.env.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys

TEAM = ["revit-orchestrator", "revit-pm", "revit-ai-dev", "revit-qa-tester", "revit-code-reviewer"]
REVIEWER = "revit-code-reviewer"
DEFAULT_MODEL = "xiaomi/mimo-v2.6-flash"
DEFAULT_PROVIDER = "routerai"
SKILLS_DIR_NAME = "skills-revita"
DISABLED_SKILLS = ["agent-designer", "agent-harness"]


def log(msg: str = "") -> None:
    print(msg)


def run(cmd: list[str], cwd: str | None = None) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=900)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception as e:  # noqa: BLE001
        return 1, f"{type(e).__name__}: {e}"


def write(p: str, text: str) -> None:
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def read(p: str) -> str:
    with open(p, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def frontmatter_name(skill_md: str) -> str | None:
    txt = read(skill_md)
    m = re.search(r"^---\s*\n(.*?)\n---", txt, re.S)
    if not m:
        return None
    n = re.search(r"^name:\s*['\"]?([\w.\-]+)", m.group(1), re.M)
    return n.group(1) if n else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="реально писать (иначе только план)")
    ap.add_argument("--repo", default=None)
    ap.add_argument("--hermes-home", default=None)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--provider", default=DEFAULT_PROVIDER)
    ap.add_argument("--smoke", action="store_true", help="после установки прогнать по одному запросу на бота")
    ap.add_argument("--skip-skills", action="store_true")
    ap.add_argument("--skip-chat", action="store_true", help="не создавать/не дёргать сессии Bot Chat")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    team_dir = os.path.dirname(here)
    repo = os.path.abspath(args.repo or os.path.dirname(team_dir))
    hermes_home = os.path.abspath(
        args.hermes_home or os.environ.get("HERMES_HOME") or os.path.join(os.environ.get("LOCALAPPDATA", ""), "hermes")
    )
    user_home = os.path.expanduser("~")
    localappdata = os.environ.get("LOCALAPPDATA", os.path.join(user_home, "AppData", "Local"))

    log(f"REPO         = {repo}")
    log(f"HERMES_HOME  = {hermes_home}")
    log(f"REVIEW: каталог agent-team = {team_dir}")
    missing: list[str] = []

    if not os.path.isdir(hermes_home):
        log(f"!! HERMES_HOME не найден ({hermes_home}) — сначала установи Hermes Agent.")
        return 2

    # ── разрешение путей ─────────────────────────────────────────────────────
    def pick(*cands: str) -> str:
        for c in cands:
            if c and os.path.exists(c):
                return c.replace("\\", "/")
        return ""

    node = pick(os.path.join(hermes_home, "node", "node.exe"), shutil.which("node") or "")
    py311 = pick(os.path.join(localappdata, "Programs", "Python", "Python311", "python.exe"),
                 shutil.which("python") or "", shutil.which("python3") or "")
    uvx = pick(os.path.join(hermes_home, "bin", "uvx.exe"), shutil.which("uvx") or "")
    harness = pick(os.environ.get("HARNESS_PLUGINS", ""), r"D:/DEV/harness-plugins")
    kb_mcp = pick(os.environ.get("KNOWLEDGEBASE_MCP", ""), r"D:/DEV/KnowledgeBaseMCP")
    ssh_mcp = pick(os.environ.get("SSH_MCP", ""), r"D:/DEV/SRVLLMTOLS/SSH-MCP")
    uicontroller = pick(os.path.join(localappdata, "UiController", "RevitUiController.McpServer.exe"))

    vals = {
        "{{HERMES_HOME}}": hermes_home.replace("\\", "/"),
        "{{REPO}}": repo.replace("\\", "/"),
        "{{LOCALAPPDATA}}": localappdata.replace("\\", "/"),
        "{{USER_HOME}}": user_home.replace("\\", "/"),
        "{{HARNESS_PLUGINS}}": harness,
        "{{KNOWLEDGEBASE_MCP}}": kb_mcp,
        "{{SSH_MCP}}": ssh_mcp,
    }
    for k, v in vals.items():
        log(f"  {k:22} -> {v or 'НЕ НАЙДЕНО'}")
    log(f"  node={node or 'НЕ НАЙДЕН'}  py311={py311 or 'НЕ НАЙДЕН'}  uvx={uvx or 'НЕ НАЙДЕН'}")
    log(f"  UiController.McpServer.exe={uicontroller or 'НЕ НАЙДЕН'}")

    def subst(text: str) -> str:
        for k, v in vals.items():
            if v:
                text = text.replace(k, v)
        return text

    # ── MCP-блоки ────────────────────────────────────────────────────────────
    def mcp_block(kind: str) -> tuple[str, list[str]]:
        f = os.path.join(team_dir, "mcp", "mcp-servers.reviewer.yaml" if kind == "reviewer" else "mcp-servers.full.yaml")
        block = subst(read(f))
        unresolved = []
        out_lines = []
        for ln in block.splitlines():
            out_lines.append(ln)
        block = "\n".join(out_lines) + "\n"
        # сервера с неразрешёнными путями выключаем
        entries = re.split(r"(?=^  [a-z_0-9-]+:$)", block, flags=re.M)
        rebuilt = []
        for e in entries:
            if not e.strip():
                continue
            name = (re.match(r"^  ([a-z_0-9-]+):$", e, re.M) or [None, "?"])[1]
            bad = "{{" in e
            if bad:
                unresolved.append(name)
                e = e.replace("enabled: true", "enabled: false")
                e = re.sub(r"(^\s*(command|url):).*$", r"\1 CHANGEME-unresolved-path", e, flags=re.M)
            rebuilt.append(e.rstrip() + "\n")
        return "".join(rebuilt), unresolved

    # ── профили ──────────────────────────────────────────────────────────────
    plan = []
    for profile in TEAM:
        pdir = os.path.join(hermes_home, "profiles", profile)
        exists = os.path.isdir(pdir)
        cfg = os.path.join(pdir, "config.yaml")
        has_mcp = exists and "mcp_servers:" in read(cfg)
        plan.append((profile, exists, has_mcp))
    log("\nПлан по профилям:")
    for profile, exists, has_mcp in plan:
        log(f"  {profile:20} {'есть' if exists else 'создать':8} mcp_servers: {'есть' if has_mcp else 'прописать'}")

    if not args.apply:
        log("\nЭто план. Повтори с --apply, чтобы применить.")
        return 0

    # ── профили: роль-настройки из config-keys.yaml ──────────────────────────
    def replace_block(text: str, key: str, block_lines: list[str]) -> str:
        lines = text.splitlines()
        start = None
        for i, ln in enumerate(lines):
            if ln == key + ":" or ln.startswith(key + ": ") or ln.startswith(key + ":"):
                if ln.split(":", 1)[0] == key:
                    start = i
                    break
        if start is None:
            return text.rstrip("\n") + "\n" + "\n".join(block_lines) + "\n"
        end = len(lines)
        for i in range(start + 1, len(lines)):
            if lines[i] and not lines[i][0].isspace():
                end = i
                break
        return "\n".join(lines[:start] + block_lines + lines[end:]) + "\n"

    def role_blocks(profile: str) -> list[str]:
        p = os.path.join(team_dir, "bots", profile, "config-keys.yaml")
        if not os.path.exists(p):
            return []
        return subst(read(p)).splitlines()

    def split_top(text: str) -> list[tuple[str, list[str]]]:
        out: list[tuple[str, list[str]]] = []
        cur_key, cur = None, []
        for ln in text.splitlines():
            if ln and not ln[0].isspace() and ":" in ln:
                if cur_key:
                    out.append((cur_key, cur))
                cur_key, cur = ln.split(":", 1)[0], [ln]
            elif cur_key:
                cur.append(ln)
        if cur_key:
            out.append((cur_key, cur))
        return out

    # 1) профили
    for profile in TEAM:
        pdir = os.path.join(hermes_home, "profiles", profile)
        if not os.path.isdir(pdir):
            rc, out = run(["hermes", "profile", "create", profile, "--no-skills", "--no-alias"])
            log(f"profile create {profile}: rc={rc}")
            if rc != 0:
                log(out[-500:])
        src_bot = os.path.join(team_dir, "bots", profile)
        for name in ("SOUL.md", "AGENTS.md", "profile.yaml"):
            sp = os.path.join(src_bot, name)
            if os.path.exists(sp):
                write(os.path.join(pdir, name), subst(read(sp)))

    # 2) MCP + модель + скиллы
    for profile, _, _ in plan:
        pdir = os.path.join(hermes_home, "profiles", profile)
        cfg = os.path.join(pdir, "config.yaml")
        kind = "reviewer" if profile == REVIEWER else "full"
        mcp_block_text, unresolved = mcp_block(kind)
        text = read(cfg) if os.path.exists(cfg) else ""
        if "mcp_servers:" not in text:
            with open(cfg, "a", encoding="utf-8", newline="\n") as fh:
                fh.write("\n" + mcp_block_text)
        # роль-настройки пишем прямо в YAML: `hermes config set` поднимает все MCP-серверы
        # профиля на каждый вызов (минуты, а с живым мостом Revit — и вовсе висит).
        rblocks = dict(split_top("\n".join(role_blocks(profile))))
        if rblocks:
            for key, blk in rblocks.items():
                if key == "model":
                    blk = [re.sub(r"^(\s*default:).*$", r"\g<1> " + args.model, l) if l.strip().startswith("default:")
                           else re.sub(r"^(\s*provider:).*$", r"\g<1> " + args.provider, l) if l.strip().startswith("provider:")
                           else l for l in blk]
                text = replace_block(text, key, blk)
        else:
            skills_dir = os.path.join(hermes_home, SKILLS_DIR_NAME).replace("\\", "/")
            text = replace_block(text, "skills", ["skills:", "  external_dirs:",
                                                  f"    - {skills_dir}", "  disabled:"] +
                                 [f"    - {sk}" for sk in DISABLED_SKILLS])
        write(cfg, text)
        # ключ провайдера из общего .env (построчно, значение не печатаем)
        src_env = os.path.join(hermes_home, ".env")
        dst_env = os.path.join(pdir, ".env")
        if os.path.exists(src_env):
            keys = [l for l in read(src_env).splitlines() if re.match(r"^(HERMES_CUSTOM_\w*ROUTERAI|ROUTERAI)\w*=", l)]
            have = read(dst_env) if os.path.exists(dst_env) else ""
            add = [l for l in keys if l.split("=")[0] not in have]
            if add:
                with open(dst_env, "a", encoding="utf-8", newline="\n") as fh:
                    fh.write("\n".join(add) + "\n")
        log(f"{profile}: mcp={kind}{' (disabled: ' + ','.join(unresolved) + ')' if unresolved else ''}")

    # 3) скиллы: репозиторные + hermes-native в общий каталог
    if not args.skip_skills:
        dest = os.path.join(hermes_home, SKILLS_DIR_NAME)
        os.makedirs(dest, exist_ok=True)
        builtin = set()
        bdir = os.path.join(hermes_home, "skills")
        for root, _, files in os.walk(bdir):
            if "SKILL.md" in files:
                n = frontmatter_name(os.path.join(root, "SKILL.md"))
                if n:
                    builtin.add(n)
        src_repo = os.path.join(repo, ".kilo", "skills")
        copied = skipped = 0
        if os.path.isdir(src_repo):
            for name in sorted(os.listdir(src_repo)):
                s = os.path.join(src_repo, name)
                sk = os.path.join(s, "SKILL.md")
                if not os.path.isfile(sk):
                    continue
                fname = frontmatter_name(sk) or name
                if fname in builtin or os.path.isdir(os.path.join(dest, name)):
                    skipped += 1
                    continue
                shutil.copytree(s, os.path.join(dest, name))
                for junk in ("skills", "agents", "commands", ".claude-plugin"):
                    j = os.path.join(dest, name, junk)
                    if os.path.isdir(j):
                        shutil.rmtree(j, ignore_errors=True)
                copied += 1
        native = os.path.join(team_dir, "skills", "hermes-native")
        n_copied = 0
        if os.path.isdir(native):
            for name in sorted(os.listdir(native)):
                s = os.path.join(native, name)
                if not os.path.isdir(s):
                    continue
                d = os.path.join(dest, name)
                if os.path.isdir(d):
                    shutil.rmtree(d)
                shutil.copytree(s, d)
                n_copied += 1
        log(f"skills-revita: +{copied} из репо (пропущено дублей {skipped}), +{n_copied} hermes-native")

    # 4) Bot Chat + sessions.model
    for profile in TEAM:
        pdir = os.path.join(hermes_home, "profiles", profile)
        if not args.skip_chat:
            q = os.path.join(pdir, "bot-chat-probe.txt")
            write(q, "Ответь одной строкой: имя своего профиля и свою роль. Без рассуждений.\n")
            rc, out = run(["hermes", "-p", profile, "chat", "--continue", "Bot Chat",
                           "--create-if-missing", "--query-file", q])
            log(f"Bot Chat {profile}: rc={rc} {'ok' if 'Title:' in out else 'ПРОВЕРЬ ВРУЧНУЮ'}")
        db = os.path.join(pdir, "state.db")
        if os.path.exists(db):
            try:
                c = sqlite3.connect(db)
                for sid, mc in c.execute("select id, model_config from sessions").fetchall():
                    try:
                        d = json.loads(mc) if mc else {}
                    except Exception:  # noqa: BLE001
                        d = {}
                    d.update({"provider": args.provider, "model": args.model, "follow_profile_config": True})
                    c.execute("update sessions set model=?, model_config=? where id=?", (args.model, json.dumps(d), sid))
                c.commit()
            except Exception as e:  # noqa: BLE001
                log(f"  sessions patch: {e}")

    # 5) смоук
    if args.smoke:
        for profile in TEAM:
            rc, out = run(["hermes", "-p", profile, "chat", "-q", "Ответь одной строкой: кто ты и какая у тебя роль."])
            tail = [l for l in out.splitlines() if l.strip()][-1:] or [""]
            log(f"smoke {profile}: rc={rc} | {tail[0][:160]}")

    # 6) проверка
    rc, out = run([sys.executable, os.path.join(here, "verify_team.py"), "--hermes-home", hermes_home])
    log("\n" + out)

    log("Требует ручной установки/запуска (если перечислено):")
    hints = []
    if not harness:
        hints.append("D:/DEV/harness-plugins (memory-store, qdrant-kb) — скилл qdrant-kb-and-cgc-mcp")
    if not kb_mcp:
        hints.append("D:/DEV/KnowledgeBaseMCP — python venv + requirements.txt")
    if not ssh_mcp:
        hints.append("D:/DEV/SRVLLMTOLS/SSH-MCP — python venv + servers.yaml")
    if not uicontroller:
        hints.append("UiController — powershell -File .kilo/scripts/ui-setup.ps1")
    hints.append("Qdrant на 127.0.0.1:6333 (коллекции не переносятся автоматически)")
    hints.append("CodeGraph: cd D:/DEV/harness-plugins && docker compose --profile cgc up -d codegraphcontext")
    hints.append("Revit + плагин ReVibe: .kilo/scripts/build-all.ps1 / deploy-isolated.ps1")
    for h in hints:
        log(f"  - {h}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
