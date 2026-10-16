#!/usr/bin/env python3
"""Verifica repositórios do GitHub sem API: faz um fetch raso do HEAD e lê a data do último commit.

Uso: python3 scripts/check_repos.py owner/repo [owner/repo ...]
Saída: uma linha JSON por repositório: {"repo":..., "ok":bool, "last_commit":"AAAA-MM-DD"|null}
"""
import json, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor


def check(repo):
    with tempfile.TemporaryDirectory() as d:
        url = f"https://github.com/{repo}.git"
        run = lambda *a: subprocess.run(["git", "-C", d, *a], capture_output=True, text=True, timeout=120)
        try:
            run("init", "-q")
            r = run("fetch", "-q", "--depth=1", "--filter=blob:none", url, "HEAD")
            if r.returncode != 0:
                return {"repo": repo, "ok": False, "last_commit": None}
            date = run("log", "-1", "--format=%cs", "FETCH_HEAD").stdout.strip()
            return {"repo": repo, "ok": True, "last_commit": date or None}
        except Exception:
            return {"repo": repo, "ok": False, "last_commit": None}


if __name__ == "__main__":
    with ThreadPoolExecutor(8) as ex:
        for res in ex.map(check, sys.argv[1:]):
            print(json.dumps(res), flush=True)
