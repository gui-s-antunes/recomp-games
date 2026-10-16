#!/usr/bin/env python3
"""Verifica repositórios do GitHub sem API: faz um fetch raso do HEAD e lê a data do último commit.

Uso: python3 scripts/check_repos.py owner/repo [owner/repo ...]
Saída: uma linha JSON por repositório: {"repo":..., "ok":bool, "last_commit":"AAAA-MM-DD"|null}
"""
import json, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor


def check(repo):
    """repo pode ser 'dono/repo' (GitHub) ou uma URL completa de qualquer host git."""
    with tempfile.TemporaryDirectory() as d:
        url = repo if repo.startswith("http") else f"https://github.com/{repo}.git"
        run = lambda *a: subprocess.run(["git", "-C", d, *a], capture_output=True, text=True, timeout=120)
        try:
            run("init", "-q")
            r = run("fetch", "-q", "--depth=1", "--filter=blob:none", url, "HEAD")
            if r.returncode != 0:
                return {"repo": repo, "ok": False, "last_commit": None}
            out = run("log", "-1", "--format=%cs %H", "FETCH_HEAD").stdout.split()
            date, sha = (out + [None, None])[:2]
            return {"repo": repo, "ok": True, "last_commit": date, "sha": sha}
        except Exception:
            return {"repo": repo, "ok": False, "last_commit": None}


if __name__ == "__main__":
    with ThreadPoolExecutor(16) as ex:
        for res in ex.map(check, sys.argv[1:]):
            print(json.dumps(res), flush=True)
