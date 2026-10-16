# Instruções para a atualização diária

Este arquivo é lido pelo agente que atualiza o catálogo todo dia. Ele publica direto na branch `main`; o GitHub Pages republica o site sozinho. A pesquisa precisa ser exaustiva: passe por **todas** as fontes abaixo em todas as execuções, não só pelo GitHub.

## Rotina

1. **Atividade dos projetos existentes:** `python3 scripts/refresh.py`.
2. **Listas estruturadas (automático):** `python3 scripts/harvest.py` clona e lê as listas da seção A e grava `data/candidates.json`.
3. **Quiver Launcher (seção B):** se houver um navegador disponível, exporte o catálogo para `data/sources/quiver.tsv` (instruções na seção B). Sem navegador, mantenha o arquivo atual.
4. **Pesquisa na web (seções C e D):** faça as buscas listadas. Cada projeto novo encontrado vira uma linha em `data/sources/manual.tsv` com tipo, plataforma e uso de IA quando a fonte informar.
5. **Junção e verificação:** `python3 scripts/merge.py`. Ele remove duplicatas (por URL e pelo commit do HEAD), testa cada repositório e só inclui o que responde. Repositórios fora do GitHub não podem ser testados deste ambiente; entram marcados como não verificados.
6. **Validação:** `python3 -m json.tool data/projects.json > /dev/null` e confira o resumo impresso pelo merge.
7. **Publicação:** commit `Atualização diária AAAA-MM-DD: N novos` (nomes no corpo, mais a lista de candidatos descartados) e push para `main`.

## Fontes

### A. Listas estruturadas (lidas pelo harvest.py)
- [awesome-game-decompilations](https://github.com/CharlotteCross1998/awesome-game-decompilations): decompilações e recompilações por console; marca projetos com IA (⚠️).
- [awesome-unofficial-pc-ports](https://github.com/Sebastrion/awesome-unofficial-pc-ports): ports e recompilações para PC com instalação simples.
- [osgameclones](https://github.com/opengaming/osgameclones): engines reimplementadas (`type: remake` com `content: commercial`).

### B. Quiver Launcher
Catálogo de cerca de 400 ports e recompilações com o nível de uso de IA declarado (`none`, `assisted`, `generated`). A API pública fica em `https://api.quiverlauncher.com/api/v1/apps?limit=100` (paginação por `nextCursor`), e o repositório de cada app está em `/apps/{slug}` → `project.repository`. O shell deste ambiente não alcança esse host; use um navegador (abra quiverlauncher.com e rode o `fetch` no console da página) e grave no formato de `data/sources/quiver.tsv`.

### C. Páginas e listas para consultar na web
- Wikipedia: "List of game engine recreations".
- Emulation General Wiki: "Game engine recreations and source ports".
- Held Games: listas de jogos recompilados (geral, N64, Xbox 360, PS3).
- readonlymemo.com: "decompilation projects and N64 recompiled list".
- decomp.dev (painel de progresso das decompilações; o site bloqueia robôs, então use buscas sobre ele).
- Tópicos do GitHub (inclua as páginas 2 e 3): `decompilation`, `recompilation`, `static-recompilation`, `n64recomp`, `pc-port`, `xenonrecomp`, `rexglue`, `source-port`, `reverse-engineering` + nome de jogo.
- Organizações: zeldaret, pret, n64decomp, doldecomp, HarbourMasters, N64Recomp, hedge-dev, rexglue, PrimeDecomp, isledecomp, diasurgical, BlackLabelHQ, sonicdcer, mstan, alexbeavs-ps1-ports, TechnicallyComputers, RSDKModding, snesrev, TheAssemblyArmada, alexbatalov.
- GitLab, Codeberg e sourcehut: buscas por "decomp" e "recomp" (muitos projetos de N64 ficam no GitLab).

### D. Notícias e comunidades (para achar o que ainda não entrou nas listas)
Buscas do tipo "recompiled PC port", "native PC port decompilation", "static recompilation" + o mês atual em: Time Extension, GamingOnLinux, Notebookcheck, PC Gamer, DSOGaming, TweakTown, Tom's Hardware, Retro Handhelds, GBAtemp, r/emulation, r/REGames, r/SteamDeck. Notícia só vale se apontar para o repositório.

## Critérios de inclusão

Entra:
- Decompilação, recompilação estática, port nativo ou engine reimplementada de um jogo comercial, ou ferramenta específica para isso (ex.: N64Recomp, XenonRecomp).
- Repositório público com código real.
- Projetos feitos com IA também entram, com o campo `ai` preenchido. O site mostra isso ao visitante.

Não entra:
- ROM hacks, mods, emuladores genéricos, launchers, trainers, cheats, servidores de jogos online.
- Jogos originais (não são ports de nada).
- Qualquer coisa que distribua ROMs, ISOs, assets ou executáveis do jogo original.
- Forks sem mudanças (o merge já descarta os de commit igual).

Na dúvida, deixe de fora e cite o candidato no commit como "não incluído".

## Tipos (campo `type`)

- `decomp`: código-fonte reescrito a partir do executável original, que compila para o mesmo jogo na plataforma original.
- `recomp`: tradução automática do código de máquina para C/C++ por uma ferramenta, gerando executável nativo.
- `port`: código de uma decompilação ou de um código-fonte oficial adaptado para rodar nativamente em outras plataformas.
- `reimpl`: motor novo escrito do zero que usa os arquivos (assets) do jogo original.

Se um projeto se encaixa em dois, escolha o que descreve o que o usuário final roda. Ex.: OpenGOAL decompila, mas o resultado é um port para PC, então `port`.

## Uso de IA (campo `ai`)

`none` (a fonte diz que não usa), `assisted` (IA ajudou), `generated` (código majoritariamente gerado por IA) ou `null` (nenhuma fonte informa). Sempre use o nível mais alto declarado por qualquer fonte. Não deduza por conta própria.

## Formato de `data/sources/manual.tsv`

Uma linha por projeto, separada por tabulação: `repositório  nome  jogo  plataforma original  tipo  uso de IA  fonte`. Use os nomes de plataforma já existentes no catálogo (ex.: "Nintendo 64", "PlayStation", "Xbox 360", "PC (DOS)").
