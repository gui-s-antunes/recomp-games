#!/usr/bin/env python3
"""Atualiza last_commit e status de todos os projetos em data/projects.json.

Uso: python3 scripts/refresh.py
Repositórios que não respondem mantêm os dados anteriores e são listados no final.
"""
import datetime, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from check_repos import check
from concurrent.futures import ThreadPoolExecutor

PATH = os.path.join(os.path.dirname(__file__), "..", "data", "projects.json")


def status(d, today):
    if not d:
        return "desconhecido"
    age = (today - datetime.date.fromisoformat(d)).days
    return "ativo" if age <= 180 else "lento" if age <= 730 else "parado"


def main():
    data = json.load(open(PATH, encoding="utf-8"))
    today = datetime.date.today()
    github = [p for p in data["projects"] if p.get("repo")]
    with ThreadPoolExecutor(8) as ex:
        results = {r["repo"]: r for r in ex.map(check, [p["repo"] for p in github])}
    failed = []
    for p in github:
        r = results[p["repo"]]
        if r["ok"]:
            p["last_commit"] = r["last_commit"]
        else:
            failed.append(p["repo"])
        p["status"] = status(p.get("last_commit"), today)
    data["updated"] = today.isoformat()
    json.dump(data, open(PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"{len(github) - len(failed)} atualizados, {len(failed)} sem resposta: {failed}")


if __name__ == "__main__":
    main()
