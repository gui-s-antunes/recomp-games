#!/usr/bin/env python3
"""Coleta candidatos de listas estruturadas públicas e grava data/candidates.json.

Fontes (cada uma é clonada com `git clone --depth 1` para um diretório temporário):
  - CharlotteCross1998/awesome-game-decompilations  (decompilações e recompilações por console)
  - Sebastrion/awesome-unofficial-pc-ports           (ports e recompilações para PC)
  - opengaming/osgameclones                          (engines reimplementadas: type=remake com dados comerciais)

Uso: python3 scripts/harvest.py [diretório-de-trabalho]
Depois rode scripts/merge.py para verificar e incorporar ao catálogo.
"""
import json, os, re, subprocess, sys, tempfile

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "data", "candidates.json")
REPO_RE = re.compile(r"https?://(?:www\.)?(github\.com|gitlab\.com|codeberg\.org|git\.sr\.ht|bitbucket\.org)/([^\s)\]>\"'#?]+)")

# Nome de seção/console nas listas -> nome de plataforma usado no catálogo
PLATFORM_ALIASES = {
    "nes / famicom": "NES", "gameboy": "Game Boy", "snes / super famicom": "Super Nintendo",
    "gameboy colour": "Game Boy Color", "nintendo 64": "Nintendo 64", "gameboy advance": "Game Boy Advance",
    "nintendo gamecube": "GameCube", "nintendo ds": "Nintendo DS", "nintendo wii": "Wii",
    "nintendo 3ds": "Nintendo 3DS", "nintendo wii u": "Wii U", "nintendo switch": "Nintendo Switch",
    "xbox": "Xbox", "playstation": "PlayStation", "playstation 2": "PlayStation 2", "xbox 360": "Xbox 360",
    "xbox one": "Xbox One", "pc / computer": "PC", "mobile": "Mobile",
}
# Palavras-chave para deduzir plataforma em textos livres (ordem importa: mais específicas primeiro)
PLATFORM_HINTS = [
    (r"xbox ?360|xenon|rexglue", "Xbox 360"), (r"\bxbox one\b", "Xbox One"), (r"original xbox|\bxbox\b", "Xbox"),
    (r"\bps5\b|playstation 5", "PlayStation 5"), (r"\bps4\b|playstation 4", "PlayStation 4"),
    (r"\bps3\b|playstation 3", "PlayStation 3"), (r"\bps2\b|playstation 2", "PlayStation 2"),
    (r"\bpsp\b", "PSP"), (r"\bps1\b|\bpsx\b|playstation", "PlayStation"),
    (r"wii u", "Wii U"), (r"\bwii\b", "Wii"), (r"gamecube|\bgcn?\b", "GameCube"), (r"\b3ds\b", "Nintendo 3DS"),
    (r"\bswitch\b", "Nintendo Switch"), (r"\bn64\b|nintendo 64|n64recomp", "Nintendo 64"),
    (r"\bgba\b|game ?boy advance", "Game Boy Advance"), (r"\bnds\b|nintendo ds", "Nintendo DS"),
    (r"game ?boy color|\bgbc\b", "Game Boy Color"), (r"game ?boy", "Game Boy"),
    (r"\bsnes\b|super nintendo|super famicom", "Super Nintendo"), (r"\bnes\b|famicom", "NES"),
    (r"dreamcast", "Dreamcast"), (r"saturn", "Sega Saturn"), (r"mega drive|genesis", "Mega Drive"),
    (r"\b32x\b", "Sega 32X"), (r"j2me", "J2ME"), (r"android|\bios\b|mobile", "Mobile"),
]


def norm_repo(host, path):
    parts = [p for p in path.split("/") if p]
    if host == "git.sr.ht":
        parts = parts[:2]
    elif host == "gitlab.com":
        cut = parts.index("-") if "-" in parts else len(parts)
        parts = parts[:cut][:3]
    else:
        parts = parts[:2]
    if len(parts) < 2:
        return None
    parts = [re.sub(r"https?:?$", "", x) for x in parts]
    path = "/".join(parts)
    path = re.sub(r"\.git$", "", path)
    return f"https://{host}/{path}"


def guess_platform(*texts):
    t = " ".join(x for x in texts if x).lower()
    for pat, name in PLATFORM_HINTS:
        if re.search(pat, t):
            return name
    return None


def kind_from_text(name, url, desc=""):
    t = f"{name} {url} {desc}".lower()
    if re.search(r"recomp|recompil", t):
        return "recomp"
    if re.search(r"reimplement|engine recreation", t):
        return "reimpl"
    if re.search(r"native port|pc port|\bport\b|source port", t):
        return "port"
    return "decomp"


def clone(repo, workdir):
    dest = os.path.join(workdir, repo.split("/")[1])
    if not os.path.isdir(dest):
        subprocess.run(["git", "clone", "-q", "--depth", "1", f"https://github.com/{repo}.git", dest], check=True, timeout=300)
    return dest


def from_awesome_decomp(workdir):
    path = os.path.join(clone("CharlotteCross1998/awesome-game-decompilations", workdir), "README.md")
    section, out = None, []
    for line in open(path, encoding="utf-8"):
        h = re.match(r"^##\s+(.*)", line)
        if h:
            section = h.group(1).strip()
            continue
        m = re.match(r"^\s*-\s+\[(.+?)\]\((\S+?)\)", line)
        if not m or not section:
            continue
        name, url = m.groups()
        r = REPO_RE.search(url)
        if not r:
            continue
        repo_url = norm_repo(*r.groups())
        if not repo_url:
            continue
        ai = "⚠️" in name
        game = re.sub(r"⚠️\s*", "", name).strip()
        game_clean = re.sub(r"\s*\((native port|browser reimplementation)\)\s*$", "", game, flags=re.I)
        plat = PLATFORM_ALIASES.get(section.lower()) or guess_platform(game, url) or "Não informada"
        out.append(dict(url=repo_url, name=game, game=game_clean, original_platform=plat,
                        type=kind_from_text(game, url), ai_assisted=ai,
                        source="awesome-game-decompilations"))
    return out


def from_awesome_pc_ports(workdir):
    path = os.path.join(clone("Sebastrion/awesome-unofficial-pc-ports", workdir), "README.md")
    brand_platform = {"nintendo": None, "playstation": "PlayStation", "xbox": "Xbox", "sega": "Sega",
                      "indie": "PC", "j2me": "J2ME", "utilities": None}
    brand, game, sub, out, last = None, None, None, [], None
    for line in open(path, encoding="utf-8"):
        h2 = re.match(r"^##\s+\S+\s+(.*)", line)
        if h2:
            brand = h2.group(1).strip().lower(); game = None; continue
        s = re.search(r"<summary><strong>(.+?)</strong></summary>", line)
        if s:
            game, sub = s.group(1).strip(), None; continue
        h4 = re.match(r"^####\s+(.*)", line)
        if h4:
            sub = h4.group(1).strip().lower(); continue
        if brand in (None, "utilities") or not game:
            continue
        h3 = re.match(r"^###\s+(?:⭐\s*)?\[(.+?)\]\((\S+?)\)", line)
        li = re.match(r"^\s*-\s+\[(.+?)\]\((\S+?)\)\s*(?:[–-]\s*(.*))?", line)
        if h3:
            name, url, desc, role = h3.group(1), h3.group(2), "", "main"; sub = None
        elif li and sub in ("project(s)", "ports"):
            name, url, desc, role = li.group(1), li.group(2), li.group(3) or "", sub
        else:
            if last is not None and line.strip() and not line.startswith(("#", "<", "📺", "-")):
                last["_desc"] = (last.get("_desc", "") + " " + line.strip()).strip()
            continue
        r = REPO_RE.search(url)
        if not r:
            last = None; continue
        repo_url = norm_repo(*r.groups())
        if not repo_url:
            last = None; continue
        kind = "decomp" if role == "project(s)" else kind_from_text(name, url, desc)
        if kind == "decomp" and role != "project(s)":
            kind = "port"
        entry = dict(url=repo_url, name=name.strip(), game=game, original_platform=None, type=kind,
                     ai_assisted=False, source="awesome-unofficial-pc-ports", _brand=brand, _desc=desc)
        out.append(entry); last = entry if role == "main" else None
    for e in out:
        desc = e.pop("_desc", ""); brand = e.pop("_brand")
        e["original_platform"] = guess_platform(desc, e["name"], e["url"], e["game"]) or brand_platform.get(brand) or "Não informada"
        if e["type"] != "decomp":
            e["type"] = kind_from_text(e["name"], e["url"], desc)
            if e["type"] == "decomp":
                e["type"] = "port"
        if re.search(r"\bAI\b|LLM|claude|codex|gpt", desc):
            e["ai_assisted"] = True
    return out


def from_osgameclones(workdir):
    import yaml
    base = clone("opengaming/osgameclones", workdir)
    originals = {}
    for f in os.listdir(os.path.join(base, "originals")):
        for o in yaml.safe_load(open(os.path.join(base, "originals", f), encoding="utf-8")) or []:
            originals[o["name"]] = o
            for n in o.get("names", []) or []:
                originals[n] = o
    out = []
    for f in sorted(os.listdir(os.path.join(base, "games"))):
        for g in yaml.safe_load(open(os.path.join(base, "games", f), encoding="utf-8")) or []:
            if g.get("type") != "remake" or g.get("content") != "commercial":
                continue
            repo = g.get("repo") or ""
            r = REPO_RE.search(repo)
            url = norm_repo(*r.groups()) if r else (repo or g.get("url"))
            if not url:
                continue
            origs = g.get("originals") or []
            plats = []
            for o in origs:
                plats += (originals.get(o, {}).get("platforms") or [])
            out.append(dict(url=url, name=g["name"], game=" / ".join(origs) or g["name"], original_platform=None,
                            _platforms=plats,
                            type="reimpl", ai_assisted=False, source="osgameclones",
                            target_platforms=g.get("platforms") or [],
                            fallback_date=str(g.get("updated") or "") or None,
                            git=bool(r)))
    return out


def main():
    workdir = sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp()
    sys.path.insert(0, workdir)
    cands = []
    for fn in (from_awesome_decomp, from_awesome_pc_ports, from_osgameclones):
        got = fn(workdir)
        print(f"{fn.__name__}: {len(got)}")
        cands += got
    json.dump(cands, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(cands)} candidatos em {OUT}")


if __name__ == "__main__":
    main()
