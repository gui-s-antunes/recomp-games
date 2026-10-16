# Jogos antigos, código novo

Catálogo de decompilações, recompilações estáticas, ports e engines reimplementadas de jogos, atualizado diariamente por um agente.

- `index.html`: o site (estático, sem build).
- `data/projects.json`: os dados do catálogo.
- `scripts/refresh.py`: atualiza a atividade de todos os projetos.
- `scripts/check_repos.py`: verifica se um repositório existe e quando teve o último commit.
- `AGENT.md`: regras da atualização diária.

## Publicação

Ative o GitHub Pages em Settings → Pages → Deploy from a branch → `main` / raiz. O site fica em `https://SEU-USUARIO.github.io/NOME-DO-REPO/`.

Para testar localmente: `python3 -m http.server` e abra `http://localhost:8000`.

O catálogo só aponta para os projetos; não hospeda ROMs, assets ou binários de jogos.
