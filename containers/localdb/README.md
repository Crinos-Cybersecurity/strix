# Sandbox local-databases layer

Camada construída sobre `ghcr.io/usestrix/strix-sandbox:1.3.0` que acrescenta
**duas coisas**, e só elas:

1. **Pillow** no venv `/app/.venv` — sem ele o agente morre com
   `ModuleNotFoundError: No module named 'PIL'` ao processar imagem.
2. **Clientes _e_ servidores de banco** — MongoDB (`mongod` + `mongosh`), Redis,
   PostgreSQL, MariaDB/MySQL e SQLite — mais o helper `sandbox-db`
   (`/home/pentester/.local/bin`, já no `PATH`).

## Por que servidores, não só clientes

Um scan registrou a lacuna *"Could not dynamically confirm (no Mongo/LLM in
sandbox)"*: o agente achou um problema real de isolamento entre tenants, mas não
tinha como **reproduzir** — faltava subir uma instância local e apontar a
aplicação para ela. Só o cliente não resolve.

## Build

```bash
docker build -t ironbot-engine-sandbox:<tag> .
```

O resultado é consumido pelo worker via `STRIX_IMAGE` (o CLI lê
`RuntimeSettings.image` e o worker repassa a env do systemd ao subprocesso).

## Por que este diretório existe

A imagem com essa camada era construída a partir de um diretório fora de
controle de versão (`/root/engine_sandbox`, no host de pentest). Isso tornava a
imagem **irreproduzível**: o `containers/Dockerfile` do repositório builda do
Kali puro e **não** copia o `sandbox-db`. Versionar os dois arquivos aqui é o que
permite reconstruir a imagem em qualquer host — e é o único motivo de o helper
estar neste diretório.

## Contrato do helper

`sandbox-db` é o **único** caminho sancionado para subir/derrubar banco dentro
do sandbox — a skill `strix/skills/tooling/local_databases.md` proíbe iniciar
`mongod`, `redis-server`, `postgres`/`pg_ctl` ou `mariadbd` na mão.
