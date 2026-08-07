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
  — ver variável `LLM_PROVIDER`/`LLM_BASE_URL` injetada pelo Job Kubernetes
  em `backend/infra/k8s/job-template.yaml` (repo `backend`, não este).
- Este fork é empacotado como imagem de container e rodado como Job
  Kubernetes efêmero por scan — não como processo de longa duração. Ver
  `backend/infra/k8s/orchestrator.py` para o ciclo de vida completo.
- Egress de rede deste container é restrito por
  `backend/infra/k8s/network-policy-template.yaml` (CiliumNetworkPolicy) —
  qualquer novo domínio que o agente precise acessar tem que ser adicionado
  lá, ou a chamada falha silenciosamente por bloqueio de rede.
