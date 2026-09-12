# strix (fork interno)

Este diretório é um FORK do Strix open source (upstream original:
<preencher: url do repo oficial>). Preencha este arquivo à medida que
customizações forem feitas — ele existe para que qualquer sessão do Claude
Code (ou qualquer dev) saiba, sem precisar rodar `git diff` contra o
upstream, o que é "nosso" e o que é "deles".

## Remotos configurados

- `origin` → nosso fork (onde fazemos push)
- `upstream` → repositório oficial do Strix (só fazemos pull/fetch, nunca push)

## O que foi customizado em relação ao upstream

<!--
Preencher conforme customizações reais forem feitas. Formato sugerido:

### <arquivo ou módulo alterado>
- O quê: <resumo da mudança>
- Por quê: <motivo — ex: integração com nosso CALLBACK_URL, formato de
  output pro nosso schema de findings>
- Risco de merge: <baixo/médio/alto — esse arquivo muda com frequência no
  upstream? é código próprio nosso adicionado, ou edição de algo deles?>
-->

## Estratégia de merge com upstream

Preferimos **isolar customizações em arquivos novos** (ex: um adapter
nosso que chama a API pública do Strix) em vez de editar os arquivos
originais deles diretamente, sempre que a arquitetura do Strix permitir —
isso reduz conflito de merge quase a zero. Quando a edição direta for
inevitável (ex: mudar comportamento interno do agente), documentar aqui
e considerar isolar num patch/diff versionado separadamente.

Antes de rodar `git merge upstream/main`, revisar o changelog do upstream
por mudanças nos arquivos listados na seção acima como "risco de merge:
alto" — são os pontos onde conflito é mais provável.

## Integração com o resto do projeto

- LLM usado: DeepSeek (`api.deepseek.com`), não o provedor padrão do Strix
  — configurado via `llm_configs` (repo `backend`) e repassado ao CLI
  `strix` como argumento/env var pelo worker abaixo.
- Este fork é distribuído como pacote (`strix-agent`) e invocado como
  **subprocesso CLI** (`strix ...`) pelo `backend/infra/deploy/
  droplet_worker.py`, rodando numa instância dedicada com Docker local —
  não como Job Kubernetes efêmero (arquitetura DOKS avaliada e abandonada
  antes de qualquer integração real ser escrita, ver `backend/CLAUDE.md`).
  O próprio CLI gerencia seu sandbox via Docker local (Docker-in-Docker).
- **Isolamento de rede por scan não existe nesta arquitetura** — trade-off
  aceito pela simplicidade do modelo de instância única (ver
  `backend/CLAUDE.md`); não há mais `CiliumNetworkPolicy`/egress
  restringido por scan.
