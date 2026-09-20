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

**Nenhuma customização de código no momento** — zero diff em relação ao
upstream. Histórico: uma customização foi adicionada em 2026-09-14
(contagem de invocação de ferramenta, `tool_usage` em `run.json`) pra
provar que um scan concluído sem achados de fato tentou algo, mas foi
REVERTIDA no mesmo dia ao sincronizar com `upstream/main` (v1.5.0 →
v1.6.2, 112 commits) e descobrir que o upstream já resolve exatamente
esse problema, de forma mais completa: `strix/report/coverage.py`
monta `coverage.json` automaticamente ao fim de todo scan
(`ReportState._save_artifacts()`), com `summary.surfaces_reviewed`/
`summary.outcomes` (ledger de superfícies revisadas + resultado de
cada uma — reportado/sem problema/descartado/não aplicável/pendente)
e `completeness.complete`/`caveats` (se o scan terminou de verdade ou
foi cortado, e por quê). Ver `ironbot-backend/CLAUDE.md`, "Cobertura do
teste via coverage.json nativo", pra como o downstream (IronBOT) passou
a consumir esse artifact — só LEITURA de um arquivo que o Strix já
escreve sozinho, nenhuma modificação de código no fork.

## Estratégia de merge com upstream

**Política do projeto (decidida em 2026-09-19, vale pros três forks):**
paridade total é mantida, e lacuna de ferramenta é coberta por
**aplicação adicional NOSSA**, no nosso repositório, usando os pontos de
extensão que a própria ferramenta oferece. Editar arquivo do upstream é
último recurso.

O que a paridade compra, medido: o upstream do Strix publica ~78
commits/mês, e o do Prowler ganhou 49 checks AWS novos em 90 dias.
Divergir custa isso. Há também um precedente caro DESTE fork, descrito na
seção acima: a customização de `tool_usage` (14/09) foi revertida no
mesmo dia porque o upstream já resolvia o problema melhor — só que
custou o trabalho de escrevê-la.

### Pontos de extensão do Strix (sem tocar no fork)

| Mecanismo | Para quê |
|---|---|
| `--mcp-server` / `--mcp-config` | Capacidade NOVA para o agente (servidor MCP nosso, processo à parte) |
| `--instruction` / `--instruction-file` | Orientar o agente sem mexer em prompt do upstream — já usamos `--instruction` no `droplet_worker.py` |
| Ler artifacts (`coverage.json`, `vulnerabilities.json`) | Consumir o que o Strix já escreve, em vez de fazê-lo escrever outra coisa — é como a cobertura de teste foi resolvida |

**Sem lacuna conhecida hoje** neste fork. A tabela existe pra que a
próxima lacuna encontrada já tenha caminho, em vez de alguém editar o
upstream por falta de alternativa. Os outros dois forks já exercitam a
política: `backend/infra/deploy/cloud/checks/` (checks próprios do
Prowler via `--checks-folder`) e
`backend/infra/deploy/cloud/complemento_cartography.py` (coleta que o
Cartography não faz).

Quando a edição direta for MESMO inevitável, documentar aqui e abrir PR
upstream, pra que a divergência tenha rota de saída.

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
