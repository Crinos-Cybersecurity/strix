# Imagem do sandbox do engine: Pillow + bancos de dados para reprodução.
#
# Base: `ghcr.io/usestrix/strix-sandbox:1.3.0` (fork do Strix).
#
# Esta imagem acrescenta DUAS coisas ao upstream, e nada mais:
#
# 1. **Pillow** no venv `/app/.venv` (scan `b1368ce3`, hackthissite.org — o
#    agente rodava `import PIL` e morria com `ModuleNotFoundError`).
#
# 2. **Clientes E servidores de banco de dados** — MongoDB (`mongod` +
#    `mongosh`), Redis, PostgreSQL, MariaDB/MySQL e SQLite.
#
# ## Por que servidores, e não só clientes
#
# O scan `3b1f5d39` (tst-asap-ai, cliente Elumini) registrou como lacuna:
# *"Could not dynamically confirm (no Mongo/LLM in sandbox)"* — o agente
# encontrou um problema real de isolamento entre tenants no Mongo, mas não
# tinha como REPRODUZIR: faltava o servidor para subir uma instância local e
# apontar a aplicação para ela. Um cliente sozinho não resolve, porque sem
# servidor não há como observar o comportamento.
#
# O agente roda `exec_command` como `pentester` (com `sudo NOPASSWD`), então
# basta os binários existirem no PATH para ele subir/derrubar instâncias
# efêmeras durante o scan.
#
# ## Mongo em ARM64
#
# O repositório oficial `mongodb-org` não publica pacotes ARM64, e o
# `mongosh` por download direto responde 403. As duas rotas que funcionam:
#   * `mongod` — tarball oficial `fastdl.mongodb.org` (existe aarch64 e x86_64)
#   * `mongosh` — via npm (é JavaScript, arquitetura-independente; 2.13.0)
#
# A imagem é usada definindo `STRIX_IMAGE` no serviço do worker (o CLI do
# Strix lê `RuntimeSettings.image`, alias `STRIX_IMAGE`, e o worker repassa a
# env do systemd ao subprocesso `strix`). Ver `README.md` desta pasta e
# `DEPLOY.md`.

FROM ghcr.io/usestrix/strix-sandbox:1.3.0

USER root

# ---------------------------------------------------------------------------
# Bancos de dados — clientes e servidores
#
# `--no-install-recommends` importa: sem ele o apt puxa dezenas de pacotes
# de documentação/recomendação e a imagem passa de 5.9 GB para 7 GB+.
# ---------------------------------------------------------------------------
RUN mkdir -p /var/lib/apt/lists/partial && \
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        sqlite3 \
        redis-tools \
        redis-server \
        postgresql \
        postgresql-client \
        default-mysql-client \
        mariadb-server && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# MongoDB — mongod do tarball oficial (não há pacote apt para ARM64)
# ---------------------------------------------------------------------------
ARG MONGO_VERSION=8.0.4
RUN set -eux; \
    ARCH="$(uname -m)"; \
    case "$ARCH" in \
        x86_64) MONGO_ARCH="x86_64" ;; \
        aarch64|arm64) MONGO_ARCH="aarch64" ;; \
        *) echo "Arquitetura sem build oficial do MongoDB: $ARCH" >&2; exit 1 ;; \
    esac; \
    cd /tmp; \
    curl -fsSL --retry 3 \
        "https://fastdl.mongodb.org/linux/mongodb-linux-${MONGO_ARCH}-ubuntu2204-${MONGO_VERSION}.tgz" \
        -o mongodb.tgz; \
    tar -xzf mongodb.tgz; \
    install -m 0755 mongodb-linux-${MONGO_ARCH}-ubuntu2204-${MONGO_VERSION}/bin/mongod /usr/local/bin/mongod; \
    install -m 0755 mongodb-linux-${MONGO_ARCH}-ubuntu2204-${MONGO_VERSION}/bin/mongos /usr/local/bin/mongos; \
    rm -rf mongodb.tgz mongodb-linux-*; \
    mongod --version | head -1

# mongosh: cliente oficial em JavaScript — o tarball ARM64 responde 403, o npm não.
RUN npm install -g mongosh@2.13.0 && \
    mongosh --version

# ---------------------------------------------------------------------------
# PostgreSQL: binários do servidor fora do PATH
#
# O apt instala o `postgres`/`initdb`/`pg_ctl` em
# `/usr/lib/postgresql/<versao>/bin/`, que NÃO está no PATH — só os clientes
# (`psql`, `pg_dump`) ficam em `/usr/bin`. Sem os symlinks, `command -v postgres`
# falha e o agente perderia um passo tentando subir uma instância local.
# Verificado no build: o pacote instala, o binário existe, só não é alcançável.
# ---------------------------------------------------------------------------
RUN set -eux; \
    PG_BINDIR="$(pg_config --bindir)"; \
    echo "pg bindir: ${PG_BINDIR}"; \
    for bin in postgres initdb pg_ctl pg_isready createdb createuser; do \
        if [ -x "${PG_BINDIR}/${bin}" ]; then \
            ln -sf "${PG_BINDIR}/${bin}" "/usr/local/bin/${bin}"; \
        fi; \
    done

# ---------------------------------------------------------------------------
# Diretórios de dados pré-criados, donos do `pentester`
#
# O agente roda como `pentester`, e cada servidor precisa de um diretório
# gravável para inicializar. Sem isso o primeiro `initdb`/`mongod`/`redis-server`
# falha por permissão e o scan perde um passo — exatamente o tipo de atrito
# que esta imagem existe para remover.
#
# ATENÇÃO: caminhos escritos um por um de propósito. `RUN` executa com
# `/bin/sh` (dash nesta base), que NÃO faz expansão de chaves: um
# `mkdir -p /home/pentester/dbdata/{mongo,redis}` cria UM diretório chamado
# literalmente `{mongo,redis}`. Foi o que aconteceu no primeiro build desta
# imagem (1.4.0) — `mongod` subia e morria com
# `NonExistentPath: Data directory ... not found`.
# ---------------------------------------------------------------------------
RUN mkdir -p /home/pentester/dbdata/mongo \
             /home/pentester/dbdata/redis \
             /home/pentester/dbdata/postgres \
             /home/pentester/dbdata/mysql \
             /home/pentester/dblogs && \
    chown -R pentester:pentester /home/pentester/dbdata /home/pentester/dblogs

USER pentester

# Pillow no venv existente (mantido do upstream desta imagem de extensão).
RUN /app/.venv/bin/pip install --no-cache-dir pillow

# Helper que sobe/derruba os bancos já com as armadilhas de cada um resolvidas.
# Existe para o agente não gastar passos descobrindo flags (ver comentário no
# próprio script e a seção "Bancos de dados" do README).
COPY --chmod=0755 sandbox-db /home/pentester/.local/bin/sandbox-db

# Prova de que tudo resolve no PATH do usuário que o agente usa.
RUN set -eux; \
    for bin in mongod mongosh redis-server redis-cli psql postgres \
               mariadb mysql mariadb-install-db sqlite3; do \
        command -v "$bin" >/dev/null || { echo "FALTA no PATH: $bin" >&2; exit 1; }; \
    done; \
    /app/.venv/bin/python -c "import PIL; print('Pillow', PIL.__version__)" && \
    mongosh --version && \
    mongod --version | head -1 && \
    psql --version && \
    redis-server --version && \
    sqlite3 --version

WORKDIR /workspace
