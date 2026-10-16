# Instruções para a atualização diária

Este arquivo é lido pelo agente que atualiza o catálogo todo dia. Ele publica direto na branch `main`; o GitHub Pages republica o site sozinho.

## Rotina

1. `python3 scripts/refresh.py` para atualizar a data do último commit e o status de todos os projetos.
2. Procurar projetos novos (lista de fontes abaixo). Antes de adicionar, conferir se o `repo` ou a `url` já existe em `data/projects.json` (compare em minúsculas).
3. Verificar cada candidato com `python3 scripts/check_repos.py dono/repo`. Só entra quem responder `"ok": true`.
4. Adicionar os aprovados em `data/projects.json` e validar o JSON (`python3 -m json.tool data/projects.json > /dev/null`).
5. Commit com a mensagem `Atualização diária AAAA-MM-DD: N novos` (listar os nomes no corpo) e push para `main`.

## Fontes

- GitHub: buscas por "decompilation", "decomp", "static recompilation", "recomp", "pc port", "reimplementation", "open source engine", "reverse engineered", combinadas com nomes de consoles (N64, GameCube, Wii, PS1, PS2, PS3, Xbox, Xbox 360, GBA, DS, Saturn, Dreamcast, PSP).
- Organizações conhecidas: zeldaret, pret, n64decomp, doldecomp, HarbourMasters, N64Recomp, hedge-dev, PrimeDecomp, isledecomp, diasurgical.
- Notícias e comunidades: decomp.dev, r/emulation, r/REGames, sites de notícias de games e emulação.

## Critérios de inclusão

Entra:
- Decompilação, recompilação estática, port nativo ou engine reimplementada de um jogo comercial ou de uma ferramenta voltada a isso.
- Repositório público com código real (não só README) e pelo menos alguns commits.

Não entra:
- Forks sem mudanças relevantes, ROM hacks, mods, emuladores genéricos, trainers, cheats.
- Qualquer coisa que distribua ROMs, ISOs, assets ou executáveis do jogo original.
- Projetos já presentes no catálogo.

Na dúvida sobre um candidato, deixe de fora e cite-o na mensagem do commit como "não incluído".

## Tipos (campo `type`)

- `decomp`: código-fonte reescrito a partir do executável original, que compila para o mesmo jogo na plataforma original.
- `recomp`: tradução automática do código de máquina para C/C++ por uma ferramenta, gerando executável nativo.
- `port`: código de uma decompilação ou de um código-fonte oficial adaptado para rodar nativamente em outras plataformas.
- `reimpl`: motor novo escrito do zero que usa os arquivos (assets) do jogo original.

Se um projeto se encaixa em dois, escolha o que descreve o que o usuário final roda. Ex.: OpenGOAL decompila, mas o resultado é um port para PC, então `port`.

## Formato de um registro

```json
{
  "id": "dono__repo",
  "name": "Nome do projeto",
  "game": "Nome do jogo (ou \"(ferramenta)\")",
  "original_platform": "Nintendo 64",
  "type": "decomp | recomp | port | reimpl",
  "target_platforms": ["Windows", "Linux"],
  "requires_original_game": true,
  "url": "https://github.com/dono/repo",
  "repo": "dono/repo",
  "description": "Uma frase em português, sem marketing.",
  "last_commit": "AAAA-MM-DD",
  "status": "ativo | lento | parado",
  "added": "AAAA-MM-DD",
  "source": "onde o projeto foi encontrado"
}
```

Use os nomes de plataforma já existentes no arquivo para não criar duplicatas no filtro (ex.: "Nintendo 64", não "N64"). Para decompilações, `target_platforms` fica vazio.
