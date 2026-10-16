#!/usr/bin/env python3
"""Junta todas as fontes, verifica cada repositório e regrava data/projects.json.

Entradas:
  data/projects.json            catálogo atual (sempre tem prioridade: nada que já está lá é sobrescrito)
  data/sources/manual.tsv       achados de pesquisa manual
  data/candidates.json          saída de scripts/harvest.py (listas awesome e osgameclones)
  data/sources/quiver.tsv       exportação do catálogo do Quiver Launcher

Regras:
  - Duplicatas são removidas pela URL (sem diferenciar maiúsculas) e pelo commit do HEAD
    (dois endereços com o mesmo commit são o mesmo repositório, por redirecionamento ou fork parado).
  - Só entra repositório git que responde. Exceção: entradas do osgameclones fora de hosts git,
    que mantêm a data informada pela própria lista.
  - O uso de IA é o mais alto declarado por qualquer fonte (none < assisted < generated).

Uso: python3 scripts/merge.py
"""
import datetime, json, os, re, sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_repos import check

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DATA = os.path.join(ROOT, "data")
TODAY = datetime.date.today()

QUIVER_PLATFORMS = {
    "n64": "Nintendo 64", "gcn": "GameCube", "wii": "Wii", "wiiu": "Wii U", "switch": "Nintendo Switch",
    "nes": "NES", "snes": "Super Nintendo", "gb": "Game Boy", "gbc": "Game Boy Color", "gba": "Game Boy Advance",
    "nds": "Nintendo DS", "3ds": "Nintendo 3DS", "vb": "Virtual Boy", "ps1": "PlayStation", "ps2": "PlayStation 2",
    "ps3": "PlayStation 3", "ps4": "PlayStation 4", "ps5": "PlayStation 5", "psp": "PSP", "og xbox": "Xbox",
    "x360": "Xbox 360", "gen": "Mega Drive", "32x": "Sega 32X", "saturn": "Sega Saturn", "dreamcast": "Dreamcast",
    "gg": "Game Gear", "arcade": "Arcade", "pc": "PC", "mobile": "Mobile",
}
OS_NAMES = {"windows": "Windows", "linux": "Linux", "macos": "macOS", "android": "Android", "ios": "iOS"}
AI_RANK = {None: -1, "": -1, "none": 0, "assisted": 1, "generated": 2}
# Prioridade de cada fonte quando duas discordam sobre tipo e plataforma (menor vence)
PRIORITY = {"catálogo inicial": 0, "manual": 1, "awesome-game-decompilations": 2, "osgameclones": 3,
            "awesome-unofficial-pc-ports": 4, "quiver": 5}


PLATFORM_NORMAL = {
    "n64": "Nintendo 64", "ps": "PlayStation", "ps1": "PlayStation", "psx": "PlayStation", "ps2": "PlayStation 2",
    "ps3": "PlayStation 3", "ps4": "PlayStation 4", "3ds": "Nintendo 3DS", "switch": "Nintendo Switch",
    "snes": "Super Nintendo", "gba": "Game Boy Advance", "gbc": "Game Boy Color", "gb": "Game Boy", "nds": "Nintendo DS",
    "ds": "Nintendo DS", "genesis": "Mega Drive", "mega drive": "Mega Drive", "sega genesis": "Mega Drive",
    "dos": "PC (DOS)", "ms-dos": "PC (DOS)", "windows": "PC (Windows)", "pc": "PC", "wii u": "Wii U",
    "gamecube": "GameCube", "game cube": "GameCube", "xbox": "Xbox", "xbox 360": "Xbox 360",
    "mac": "Classic Mac OS", "32x": "Sega 32X", "c64": "Commodore 64", "commodore 64": "Commodore 64", "classic mac os": "Classic Mac OS", "j2me": "Mobile (J2ME)",
}
# Plataformas que costumam ser relançamentos; ao escolher a original, ficam por último
MODERN = {"PC (Windows)", "PC", "Linux", "macOS", "Android", "iOS", "Mobile", "Nintendo 3DS", "Nintendo Switch",
          "PlayStation 4", "PlayStation 5", "Xbox One", "Web", "Browser", "Steam", "Wii U", "Xbox 360", "PlayStation 3"}


ORIGIN_PREFERENCE = ["Arcade", "PC (DOS)", "NES", "Super Nintendo", "Mega Drive", "PlayStation", "Nintendo 64",
                     "Game Boy", "Amiga", "ZX Spectrum", "C64", "Atari", "Apple II", "Classic Mac OS", "PC"]


def norm_platform(name):
    if not name:
        return "Não informada"
    return PLATFORM_NORMAL.get(name.strip().lower(), name.strip())


def pick_original(platforms):
    names = [norm_platform(p) for p in platforms if p]
    if not names:
        return "Não informada"
    classic = [n for n in names if n not in MODERN]
    pool = classic or names
    # A lista do osgameclones vem em ordem alfabética, então "Acorn 32-bit" apareceria primeiro em muitos jogos.
    # Preferimos as plataformas onde jogos comerciais costumavam estrear.
    for pref in ORIGIN_PREFERENCE:
        if pref in pool:
            return pref
    return pool[0]


def key(url):
    return url.lower().rstrip("/").removesuffix(".git")


def read_tsv(path):
    rows = []
    for line in open(path, encoding="utf-8"):
        if line.startswith("#") or not line.strip():
            continue
        rows.append(line.rstrip("\n").split("\t"))
    return rows


def kind_from_name(*texts):
    t = " ".join(texts).lower()
    if re.search(r"recomp|recompil|xenon", t):
        return "recomp"
    return "port"


def describe(p):
    game, plat, targets = p["game"], p["original_platform"], p.get("target_platforms") or []
    plat_txt = f" ({plat})" if plat and plat != "Não informada" else ""
    to = f" para {', '.join(targets)}" if targets else ""
    if p["type"] == "decomp":
        return f"Decompilação de {game}{plat_txt}: código-fonte reconstruído a partir do executável original."
    if p["type"] == "recomp":
        if game.startswith("("):
            return f"Ferramenta de recompilação estática para jogos de {plat}."
        return f"Recompilação estática de {game}{plat_txt}, gerando um executável nativo{to}."
    if p["type"] == "port":
        return f"Port nativo de {game}{plat_txt}{to}."
    return f"Engine reimplementada que roda {game} usando os arquivos do jogo original."


def status(d):
    if not d:
        return "desconhecido"
    age = (TODAY - datetime.date.fromisoformat(d)).days
    return "ativo" if age <= 180 else "lento" if age <= 730 else "parado"


def slug(url):
    return re.sub(r"[^a-z0-9]+", "__", key(url).split("://", 1)[1].split("/", 1)[1]).strip("_")


def main():
    current = json.load(open(os.path.join(DATA, "projects.json"), encoding="utf-8"))
    projects = {key(p["url"]): p for p in current["projects"]}
    for p in projects.values():
        p.setdefault("sources", [p.get("source", "catálogo inicial")])
        p.setdefault("ai", None)

    incoming = []  # (prioridade, dados)
    for r in read_tsv(os.path.join(DATA, "sources", "manual.tsv")):
        url, name, game, plat, typ, ai, src = (r + [""] * 7)[:7]
        incoming.append(dict(url=url, name=name, game=game, original_platform=plat, type=typ, ai=ai or None,
                             source="manual", note=src))
    for c in json.load(open(os.path.join(DATA, "candidates.json"), encoding="utf-8")):
        c["ai"] = "assisted" if c.pop("ai_assisted", False) else None
        if c.get("source") == "osgameclones" and c.get("_platforms"):
            c["original_platform"] = pick_original(c.pop("_platforms"))
        c["original_platform"] = norm_platform(c.get("original_platform"))
        incoming.append(c)
    for r in read_tsv(os.path.join(DATA, "sources", "quiver.tsv")):
        url, game, consoles, ai, oses = (r + [""] * 5)[:5]
        first = consoles.split(",")[0].strip()
        plat = QUIVER_PLATFORMS.get(first, first or "Não informada")
        name = re.sub(r"[-_]+", " ", url.rstrip("/").split("/")[-1]).strip()
        typ = kind_from_name(name, url)
        if plat == "PC" and typ == "port":
            typ = "reimpl"
        incoming.append(dict(url=url, name=name, game=game, original_platform=plat, type=typ, ai=ai or None,
                             target_platforms=[OS_NAMES.get(o, o) for o in oses.split(",") if o in OS_NAMES],
                             source="quiver"))

    incoming.sort(key=lambda c: PRIORITY.get(c["source"], 9))
    new = {}
    for c in incoming:
        k = key(c["url"])
        target = projects.get(k) or new.get(k)
        if target:
            if c["source"] not in target["sources"]:
                target["sources"].append(c["source"])
            if AI_RANK[c.get("ai")] > AI_RANK[target.get("ai")]:
                target["ai"] = c["ai"]
            if not target.get("target_platforms") and c.get("target_platforms"):
                target["target_platforms"] = c["target_platforms"]
            if target.get("original_platform") in (None, "Não informada") and c.get("original_platform") not in (None, "Não informada"):
                target["original_platform"] = c["original_platform"]
            continue
        c = dict(c)
        c["sources"] = [c.pop("source")]
        new[k] = c

    print(f"{len(projects)} já no catálogo, {len(new)} candidatos novos")
    git_hosts = ("github.com", "gitlab.com", "codeberg.org", "git.sr.ht", "bitbucket.org")
    to_check = [c["url"] for c in new.values() if any(h in c["url"] for h in git_hosts)]
    with ThreadPoolExecutor(16) as ex:
        results = {key(r["repo"]): r for r in ex.map(check, to_check)}

    seen_sha = {}
    for p in projects.values():
        if p.get("sha"):
            seen_sha[p["sha"]] = key(p["url"])
    added, dropped, dup = 0, [], 0
    for k, c in new.items():
        r = results.get(k)
        if r and r["ok"]:
            if r.get("sha") and r["sha"] in seen_sha:
                dup += 1
                other = projects[seen_sha[r["sha"]]]
                for s in c["sources"]:
                    if s not in other["sources"]:
                        other["sources"].append(s)
                continue
            last = r["last_commit"]
            seen_sha[r.get("sha")] = k
        elif not r or (not r["ok"] and not c["url"].startswith("https://github.com/")):
            # Host fora do GitHub não verificável daqui (o proxy bloqueia) ou fora de host git:
            # entra marcado como não verificado, com a data informada pela fonte quando houver.
            last = c.get("fallback_date")
            r = None
        else:
            dropped.append(c["url"]); continue
        host_path = c["url"].split("://", 1)[1]
        p = dict(
            id=slug(c["url"]), name=c["name"], game=c["game"], original_platform=c.get("original_platform") or "Não informada",
            type=c["type"], target_platforms=c.get("target_platforms") or [],
            requires_original_game=True, url=c["url"],
            repo="/".join(host_path.split("/")[1:3]) if host_path.startswith("github.com/") else None,
            git=c["url"] if (r or any(h in c["url"] for h in git_hosts)) else None,
            verified=bool(r), description="", last_commit=last, status=status(last),
            added=TODAY.isoformat(), sources=c["sources"], ai=c.get("ai"), sha=r.get("sha") if r else None,
        )
        p["description"] = describe(p)
        projects[k] = p
        added += 1

    for p in projects.values():
        p.pop("source", None)
        p.setdefault("git", p["url"])
    out = sorted(projects.values(), key=lambda p: (p["game"].lower(), p["name"].lower()))
    json.dump({"updated": TODAY.isoformat(), "projects": out},
              open(os.path.join(DATA, "projects.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{added} adicionados, {dup} duplicatas por commit, {len(dropped)} sem resposta")
    with open(os.path.join(DATA, "sources", "unreachable.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(dropped) + "\n")


if __name__ == "__main__":
    main()
