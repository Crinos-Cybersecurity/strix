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

### Contagem de invocação de ferramenta (`tool_usage`) — 2026-09-14

- **O quê**: `strix/report/state.py` (`ReportState`) ganhou
  `_tool_usage: dict[str, int]` (contagem por nome de ferramenta),
  método `record_tool_invocation(tool_name)` (incrementa e persiste em
  `run.json`, mesmo padrão de `record_sdk_usage`) e
  `_build_tool_usage_record()` (monta `{"total_calls": N, "by_tool":
  {...}}`, guardado em `self.run_record["tool_usage"]`).
  `hydrate_from_run_dir()` também ganhou a hidratação desse bloco (pra
  resume de scan não perder a contagem já feita). `strix/core/hooks.py`
  (`ReportUsageHooks`, único `RunHooks` instanciado pelo runner,
  `strix/core/runner.py:275`) ganhou `on_tool_start()` — chama
  `report_state.record_tool_invocation(tool.name)` a cada ferramenta
  invocada por QUALQUER agente (root ou sub-agente), usando o hook
  nativo `RunHooksBase.on_tool_start` do SDK `openai-agents` (`agents.
  lifecycle`), nunca reimplementado à mão.
- **Por quê**: pedido do time IronBOT (downstream) — um scan concluído
  SEM achados mostrava "Nenhuma técnica de ataque específica
  identificada"/"Nenhuma vulnerabilidade encontrada" sem nenhuma prova
  de que o agente de fato tentou algo (a única fonte estruturada,
  `vulnerabilities.json`, fica vazia nesse caso). `run.json.tool_usage.
  total_calls` agora dá esse número, lido pelo worker
  (`backend/infra/deploy/droplet_worker.py`) e exposto no relatório do
  IronBOT como "Cobertura do teste", independente de haver achado ou
  não.
- **Risco de merge**: baixo — `state.py`/`hooks.py` são só ESTENDIDOS
  (campos/métodos novos, nenhuma linha existente alterada em
  `state.py`; em `hooks.py`, só um método novo adicionado ao fim da
  classe `ReportUsageHooks`, nenhum método existente tocado). Conflito
  só se o upstream adicionar um campo com o MESMO nome (`tool_usage`)
  em `run_record`, ou reescrever `ReportUsageHooks` por completo.

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
