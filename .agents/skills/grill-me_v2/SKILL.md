---
name: grill-me_v2
description: >-
  Enterprise Requirements & Architecture Interview Protocol (v2). Employs Hierarchical Decision
  Trees, NFR/SLA extraction, and automatically synthesizes a formal ADR (Architecture Decision Record).
---

# Enterprise Requirements & Architecture Interview Protocol (`grill-me_v2`)

`grill-me_v2` é o padrão corporativo para alinhamento e refinamento de requisitos técnicos entre o agente de IA e o desenvolvedor/arquiteto sênior. Ele resolve ambiguidades sistematicamente descendo ramos de uma **árvore de decisão hierárquica** e sintetiza automaticamente o resultado em um **ADR formal**.

---

## 🎯 When to Activate
- Invocado via `/grill-me_v2` ou no início de demandas com escopo em aberto, tickets com múltiplos caminhos técnicos ou decisões de arquitetura de alto impacto.

---

## 🧭 Diretrizes de Execução

### 1. Uma Pergunta por Vez (One Question at a Time)
- Nunca sobrecarregue o usuário com listas longas de perguntas em um único turno.
- Faça perguntas atômicas e sequenciais.
- Se a resposta puder ser inferida inspecionando o repositório ou arquivos de configuração existentes, **leia os arquivos primeiro em vez de perguntar**.

### 2. Uso Obrigatório da Ferramenta `ask_question`
- Formate cada pergunta com opções claras e objetivas.
- A opção tecnicamente mais recomendada deve vir sempre em primeiro lugar, prefixada com `(Recommended)`.

### 3. Descida na Árvore de Decisão Hierárquica
Conduza a entrevista na seguinte ordem estrita de precedência:
1. **Nível 1 - Escopo e Fronteiras**: O que está dentro e o que está expressamente fora do escopo?
2. **Nível 2 - Padrão de Arquitetura & Stack**: Síncrono vs Assíncrono, persistência, frameworks e bibliotecas centrais.
3. **Nível 3 - Requisitos Não-Funcionais (NFRs)**: SLAs de latência, tolerância a falhas, throughput e retenção de dados.
4. **Nível 4 - Segurança e Compliance**: Autenticação, mascaramento de PII, RBAC e segredos.
5. **Nível 5 - Estratégia de Rollout & Testes**: Feature flags, migração de banco e critérios de aceitação.

---

## 📝 Síntese Automática de ADR (Architecture Decision Record)

Ao concluir a última pergunta da árvore de decisão e alcançar alinhamento total, a skill **deve automaticamente**:
1. Criar um arquivo no diretório de documentação do projeto:
   `docs/adr/ADR-<NUM>-<slug>.md` (ou `.agents/skills/corp-pipeline/templates/adr_template.md`).
2. Preencher formalmente:
   - Status: `Aceito`
   - Contexto e Drivers de Decisão
   - Opções consideradas com prós e contras
   - Decisão tomada e trade-offs acordados
   - Consequências e ações subsequentes
3. Apresentar o link do ADR ao usuário como insumo direto para a **Fase 1 do `corp-pipeline`**.
