# Manual Operacional do Corp-Pipeline Master Orchestrator

> **Guia de Operação e Runbook para Desenvolvedores e Agentes**  
> *Procedimentos padronizados para execução de tarefas, gestão de capacidades e ciclo de melhorias.*

---

## 1. Como Funciona a Orquestração no Dia a Dia

Como usuário ou engenheiro trabalhando no repositório, **você não precisa invocar manualmente agentes ou skills para tarefas cotidianas**.

### Exemplo de Fluxo Típico:
1. **Você submete um prompt**:
   > *"Preciso criar uma nova função que exporte métricas de latência para o cliente MCP SSE."*
2. **O Corp-Pipeline entra em ação automaticamente**:
   - **Fase 0**: Lê `state.md` e confirma que a suíte de testes está com 48 testes verdes.
   - **Fase 1**: Disseca a demanda: nova feature em `src/corporate_engineer/mcp/client.py` com testes em `tests/test_mcp_client.py`.
   - **Fase 2 & 3**: Descobre e roteia:
     - Skill primária: `mcp-server-patterns` e `tdd-workflow`.
     - Subagentes: `architect` (para contrato Pydantic), `tdd-guide` (para testes RED), `python-reviewer` (revisão de tipagem).
   - **Fase 4**: Executa TDD (escreve o teste falho primeiro, implementa o código mínimo, alcança GREEN).
   - **Fase 5**: Roda Pre-Flight (Ruff, Mypy, Pytest, Secret Scanner). 0 erros obtidos.
   - **Fase 6**: Verifica se alguma oportunidade de melhoria foi identificada e atualiza `state.md`.

---

## 2. Como Interagir com o Backlog de Melhorias

Quando o orquestrador identifica uma oportunidade de otimização, arquitetura ou confiabilidade, ele exibe uma notificação padronizada:

```text
[CORP-PIPELINE / IMPROVEMENT DETECTED]

ID: IMP-0004
Category: EFFICIENCY | PERFORMANCE
Observation: O indexador AST analisa todos os arquivos a cada execução.
Current Limitation: Reindexações redundantes consomem tempo de CPU desnecessariamente.
Proposed Improvement: Implementar cache baseado em SHA-256 do arquivo.
Expected Benefits: Redução de até 90% no tempo de reindexação subsequente.
Affected Components: src/corporate_engineer/rag/ast_indexer.py
Estimated Complexity: Média (M)
Risks: Possível invalidação incorreta de cache se não houver testes com Hypothesis.
Evidence: Benchmarks de reanálise estática.
Recommendation: Implementar cache incremental.

Action:
[ SAVE FOR LATER ]  [ DISMISS ]  [ IMPLEMENT ]
```

### O que você pode responder:
- **"Salvar para depois" / "Save for later"**: O orquestrador grava a proposta em `.agents/orchestration/improvement-backlog.md` com status `SAVED_NOT_APPROVED`. Ela fica salva para sessões futuras e nada no código é alterado.
- **"Descartar" / "Dismiss"**: A ideia é descartada e o orquestrador não repete a mesma recomendação.
- **"Implementar" / "Implement"**: O orquestrador inicia imediatamente a Fase 1 do Corp-Pipeline para aquela melhoria, solicitando as confirmações normais de escopo e qualidade.

---

## 3. Comandos Úteis do Operador

### Execução de Pre-Flight Local Completo:
```powershell
.venv\Scripts\python -m corporate_engineer.cli audit --strict
```

### Inspeção de Recursos e Capacidades:
```powershell
# Inspecionar nós e checkpoints da máquina de estados:
.venv\Scripts\python -m corporate_engineer.cli dag --show-phases --checkpoints

# Testar conectividade com servidor MCP local ou remoto:
.venv\Scripts\python -m corporate_engineer.cli mcp ping --transport stdio --command "python -m dummy"

# Scanner corporativo de segredos:
.venv\Scripts\python .agents/skills/corp-pipeline/scripts/secret_scanner.py .
```

---

## 4. Adicionando Novos Recursos ao Ecossistema

Quando novos agentes, skills ou ferramentas forem introduzidos:
1. **Novo Subagente**: Criar `.agents/agents/<nome>.md` e adicionar entrada correspondente em `.agents/orchestration/agent-registry.md`.
2. **Nova Skill**: Criar `.agents/skills/<nome>/SKILL.md` com frontmatter YAML e registrar em `.agents/orchestration/skills-registry.md`.
3. **Novo Workflow**: Criar `.agents/workflows/<nome>.md` e registrar em `.agents/orchestration/workflow-registry.md`.
4. **Novo Conector / Integração**: Registrar em `.agents/orchestration/integration-registry.md` indicando o status de autenticação e limitações.
5. **Atualizar Registros**: Sincronizar `capability-registry.md` e atualizar o `state.md`.
