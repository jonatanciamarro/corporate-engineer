# Backlog Contínuo de Melhorias (`improvement-backlog.md`)

> **Repositório Persistente de Oportunidades de Evolução do Framework**  
> *Governança estrita: Descoberta → Recomendação → Salvamento com Aprovação do Usuário → Implementação.*

---

## 1. Protocolo de Governança do Backlog

Este catálogo preserva ideias e melhorias identificadas pelo **Corp-Pipeline Master Orchestrator**, garantindo que nenhuma oportunidade valiosa seja perdida ou implementada sem aprovação prévia.

### Estados do Ciclo de Vida:
- `PROPOSED`: Descoberta inicial pela inteligência do orquestrador; aguardando apreciação do usuário.
- `SAVED_NOT_APPROVED`: Usuário aprovou o salvamento para backlog, mas ainda não autorizou a implementação.
- `APPROVED`: Usuário autorizou formalmente o início do desenvolvimento.
- `IN_PROGRESS`: Em desenvolvimento ativo seguindo o Corp-Pipeline (Fase 1 a 5).
- `IMPLEMENTED`: Código implementado e pre-flight aprovado com testes verdes.
- `VERIFIED`: Validado formalmente em produção ou mergeado no branch principal.
- `REJECTED`: Analisado e descartado com justificativa documentada.
- `DEFERRED`: Postergado para milestones futuras.
- `SUPERSEDED`: Substituído por uma proposta ou arquitetura mais moderna.

---

## 2. Tabela de Registro Geral de Melhorias

| ID | Título da Melhoria | Categoria | Complexidade | Status Atual | Data de Descoberta |
|---|---|---|---|---|---|
| `IMP-0001` | Detecção Automática do `.venv` no `stack_detector.py` | `AUTOMATION` | Baixa (S) | `IMPLEMENTED` | `2026-11-19` |
| `IMP-0002` | Circuit Breaker e Reconexão com Backoff no `RemoteMCPSSEClient` | `RELIABILITY` | Média (M) | `IMPLEMENTED` | `2026-11-19` |
| `IMP-0003` | Script de Hook `SessionStart` com Injeção de Contexto Corp-Pipeline | `AUTOMATION` | Baixa (S) | `IMPLEMENTED` | `2026-11-19` |
| `IMP-0004` | Cache de Indexação AST Baseado em Hash SHA-256 de Conteúdo | `EFFICIENCY` | Média (M) | `IMPLEMENTED` | `2026-11-19` |
| `IMP-0005` | Exportação de Diagramas Mermaid Dinâmicos a partir da CLI `dag` | `CAPABILITY` | Baixa (S) | `SAVED_NOT_APPROVED` | `2026-11-19` |

---

## 3. Especificação Detalhada das Propostas

---

### 🔹 IMP-0001: Detecção Automática do `.venv` no `stack_detector.py`
- **Categoria**: `AUTOMATION` | `RELIABILITY`
- **Status**: `SAVED_NOT_APPROVED`
- **Data de Descoberta**: 2026-11-19
- **Problema / Limitação Atual**: No Windows, se o desenvolvedor executa `pytest` ou `python` pelo terminal padrão sem o `.venv` ativado no path, o Python global pode não conter as dependências instaladas (`hypothesis`, `pytest-cov`, `pydantic`), causando falhas falsas. O `stack_detector.py` atualmente emite comandos genéricos como `pytest` ao invés de apontar para `.venv\Scripts\pytest` quando o `.venv` existe localmente.
- **Solução Proposta**: Atualizar `stack_detector.py` para inspecionar se a pasta `.venv` existe no root. Em caso afirmativo no Windows, sugerir `.venv\Scripts\<tool>` ou `.venv/bin/<tool>` em sistemas Unix/macOS.
- **Benefícios Esperados**: Execução determinística dos testes e ferramentas de qualidade sem necessidade de ativação manual do virtualenv.
- **Componentes Afetados**: `.agents/skills/corp-pipeline/scripts/stack_detector.py`.
- **Complexidade**: Baixa (10-15 linhas de código).
- **Riscos**: Mínimos.
- **Critérios de Aceite**: `stack_detector.py` retorna caminhos do virtualenv quando detectado; testes unitários cobrem o comportamento.

---

### 🔹 IMP-0002: Circuit Breaker e Reconexão com Backoff no `RemoteMCPSSEClient`
- **Categoria**: `RELIABILITY` | `CAPABILITY`
- **Status**: `SAVED_NOT_APPROVED`
- **Data de Descoberta**: 2026-11-19
- **Problema / Limitação Atual**: O cliente SSE para MCP (`RemoteMCPSSEClient`) trata desconexões imediatas, mas não possui um padrão de circuit breaker integrado com retentativas automáticas e backoff exponencial quando o endpoint remoto fica intermitente.
- **Solução Proposta**: Implementar padrão Circuit Breaker com três estados (`CLOSED`, `OPEN`, `HALF_OPEN`) e política configurável de reconexão no cliente SSE.
- **Benefícios Esperados**: Resiliência contra flutuações de rede corporativa e proteção contra sobrecarga em endpoints MCP degradados.
- **Componentes Afetados**: `src/corporate_engineer/mcp/client.py`, `tests/test_mcp_client.py`.
- **Complexidade**: Média (estimado: 60-80 linhas com PBT).
- **Riscos**: Complexidade de concorrência em streaming.
- **Critérios de Aceite**: Suíte de testes com simulação de timeout, transição de estados do circuit breaker e 100% dos testes verdes.

---

### 🔹 IMP-0003: Script de Hook `SessionStart` com Injeção de Contexto Corp-Pipeline
- **Categoria**: `AUTOMATION` | `ARCHITECTURE`
- **Status**: `IN_PROGRESS`
- **Data de Descoberta**: 2026-11-19
- **Problema / Limitação Atual**: Antigravity suporta `SessionStart` em `hooks.json`, mas atualmente não havia nenhum hook configurado para alertar a sessão sobre o estado do projeto e o orquestrador Corp-Pipeline ativo.
- **Solução Proposta**: Implementar `.agents/hooks.json` apontando para um script Python em `.agents/orchestration/hooks/session_start.py` que lê o `state.md`, valida a saúde inicial e injeta a mensagem inicial no formato oficial protojson de Antigravity.
- **Benefícios Esperados**: Inicialização consistente e imediata em qualquer nova conversa sem intervenção do usuário.
- **Componentes Afetados**: `.agents/hooks.json`, `.agents/orchestration/hooks/session_start.py`.
- **Complexidade**: Baixa.
- **Riscos**: Saída inválida se o script emitir texto solto. Deve emitir exclusivamente JSON válido no stdout.
- **Critérios de Aceite**: Execução do script com payload de entrada mockado produz JSON estritamente em conformidade com a especificação de hooks do Antigravity.

---

### 🔹 IMP-0004: Cache de Indexação AST Baseado em Hash SHA-256 de Conteúdo
- **Categoria**: `EFFICIENCY` | `PERFORMANCE`
- **Status**: `SAVED_NOT_APPROVED`
- **Data de Descoberta**: 2026-11-19
- **Problema / Limitação Atual**: O indexador AST (`ASTCodebaseIndexer`) re-analisa todos os arquivos `.py` a cada execução de `corporate-engineer index`, mesmo quando os arquivos não foram modificados.
- **Solução Proposta**: Integrar o padrão `content-hash-cache-pattern`, armazenando os nós AST indexados indexados por SHA-256 do arquivo fonte em arquivo `.cache/ast_index.json`.
- **Benefícios Esperados**: Redução de até 90% no tempo de reindexação em repositórios grandes.
- **Componentes Afetados**: `src/corporate_engineer/rag/ast_indexer.py`.
- **Complexidade**: Média.
- **Riscos**: Invalidação incorreta de cache em mudanças de sintaxe.
- **Critérios de Aceite**: Testes com Hypothesis garantem que o resultado com e sem cache é semanticamente idêntico.

---

### 🔹 IMP-0005: Exportação de Diagramas Mermaid Dinâmicos a partir da CLI `dag`
- **Categoria**: `CAPABILITY`
- **Status**: `SAVED_NOT_APPROVED`
- **Data de Descoberta**: 2026-11-19
- **Problema / Limitação Atual**: O comando `corporate-engineer dag` gera tabelas de texto ou JSON dos nós e transições, mas não gera diagramas visuais legíveis para documentação ou PRs.
- **Solução Proposta**: Adicionar flag `--mermaid` ao comando `dag` que produz uma string `flowchart TD` dos estados da FSM e dependências de tarefas.
- **Benefícios Esperados**: Visualização instantânea da topologia do grafo de engenharia e fácil inclusão em ADRs e relatórios.
- **Componentes Afetados**: `src/corporate_engineer/cli.py`, `src/corporate_engineer/orchestrator/graph.py`.
- **Complexidade**: Baixa.
- **Riscos**: Mínimos.
- **Critérios de Aceite**: Flag `--mermaid` gera código Mermaid válido testado via pytest.
