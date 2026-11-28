# ADR-036: Alinhamento de Runtime Antigravity, Servidor MCP Stdio Nativo & Honestidade de Execução da CLI

- **Status**: Aceito (Accepted) — Implementado via IMP-0042
- **Data**: 2026-11-27
- **Autores / Decisores**: Corp-Pipeline Master Orchestrator & Engenheiro Responsável
- **Ticket / Contexto**: `IMP-0042` / Diagnóstico Estrutural de Amnésia, Subutilização e Simulação Silenciosa

---

## 1. Contexto e Declaração do Problema

Uma auditoria empírica no repositório `corporate-engineer` identificou três falhas estruturais interligadas que degradam o comportamento real do agente e da CLI:

1. **Amnésia e Incompatibilidade de Runtime (`.agents/`)**:
   - `.agents/hooks.json` não dispara sem confiança explícita do workspace e utiliza comando `py` (específico do Windows Python Launcher), divergindo do ADR-027 (`python`).
   - Quando `PreInvocation` (`proactive_advisor.py` / `hooks_runner.py`) é acionado, injeta ~4,9 KB de boilerplate repetitivo + URL de PR com o corpo inteiro de `PR-CORP-*.md` a cada chamada do modelo, poluindo a trajetória da conversa.
   - `session_start.py` não injeta um resumo vivo de `state.md`, enquanto `state.md` atingiu 90,7 KB (590 linhas).
   - Workflows em `.agents/workflows/` (`quality-gate.md`, `plan.md`, `feature-dev.md`, `security-scan.md`) ainda referenciam artefatos de Claude Code inexistentes (`scripts/hooks/quality-gate.js`, `.claude/plans/`, `ecc-agentshield`, `code-explorer`, `code-architect`), e `.agents/agents/*.md` são tratados como subagentes nativos inexistentes no Antigravity.

2. **Desconexão entre o Agente e o Pacote Python (`src/corporate_engineer/`)**:
   - Não há servidor MCP configurado no workspace (`integration-registry.md` confirmava ausência de servidores persistentes; segundo `agy-customizations/docs/mcp_servers.md` e `plugins.md`, servidores MCP com escopo de projeto devem ser declarados via plugin em `.agents/plugins/<nome>/mcp_config.json` com `plugin.json`).
   - Consequentemente, os analisadores determinísticos reais (`BlastRadiusAnalyzer`, `SemanticCodeEvaluator`, `CapabilityWiringAuditor`, `CanonicalSecretScanner`, `SurgicalTestRunner`, `CachedASTCodebaseIndexer`) permanecem isolados na CLI manual.

3. **Simulação Silenciosa na CLI (`run`, `swarm`, `dialectic`, `system_one`, `audit --wiring`)**:
   - `corporate-engineer run` executado sem `--dry-run` e sem `code_executor` retorna `status="SUCCESS"` e `final_phase="DELIVER"` gravando apenas um comentário placeholder em `CodeDiff` e chamando `generate_pr_url(..., ensure_pushed=False)`.
   - `SwarmCoordinator` sem `role_executor` retorna `OK` para papéis sem analisador real (ex.: `tdd-guide`, `planner`), enquanto `ONNXNLIDecisionEngine` e `OutlinesDecisionEngine` caem silenciosamente em `HeuristicDecisionEngine` por falta de dependências (`onnxruntime`/`outlines`) e artefatos esperados (`models/model_int8.onnx`, `models/tokenizer.json`) sem registrar o motivo explícito.
   - `CapabilityWiringAuditor` valida apenas `__all__` e referências AST em `tests/`, deixando sem verificação os elos reais da Invariante 9 (registro em `cli/parser.py`/`cli/main.py` e validade de caminhos em `ContextAwarePromptRefiner.DOMAIN_KEYWORDS`).

---

## 2. Drivers de Decisão
- [x] Confiabilidade e Tolerância a Falhas
- [x] Latência e Escalabilidade (SLAs de Contexto e Latência de Hooks)
- [x] Facilidade de Manutenção e Débito Técnico
- [x] Segurança e Compliance Corporativo (Least Privilege em MCP)
- [x] Transparência Operacional (Zero Simulação Mascarada)

---

## 3. Opções Consideradas

### Opção A: Pacote Completo Integrado em 3 Pilares (Escolhida)
- **Descrição**:
  1. **Pilar 1 (MCP Server Nativo + Plugin Workspace)**: Implementar `CorporateEngineerMCPServer` (`stdio` JSON-RPC 2.0 sem dependências externas) em `src/corporate_engineer/mcp/server.py`, exposto via `corporate-engineer mcp serve` com política **read/audit por padrão** (`allow_mutations=False`) e registrado via plugin `.agents/plugins/corporate-engineer/`.
  2. **Pilar 2 (Higienização `.agents/` + Hooks Enxutos)**: Eliminar spam do `PreInvocation` (emitir apenas no 1º turno com `<=300` caracteres), injetar resumo curto de `state.md` no `SessionStart`, compactar `state.md` arquivando histórico antigo em `docs/history/`, remover referências quebradas de Claude Code dos workflows e alinhar registros de agentes/integrações com o Antigravity.
  3. **Pilar 3 (Honestidade da CLI & Auditoria Real)**: Exigir executor ou `--dry-run` em `run_pipeline()` (`status="BLOCKED_NO_EXECUTOR"` quando `dry_run=False` e `code_executor is None`), marcar papéis sem analisador real no `SwarmCoordinator` sem falsos `OK`, adicionar `fallback_reason` em `SystemOneReport`, tratar `dubious ownership` do Git sem cascade de `exit 129`, e expandir `CapabilityWiringAuditor` para auditar parser/dispatcher CLI e `DOMAIN_KEYWORDS`.
- **Prós**:
  - (+) Conecta o agente LLM diretamente aos motores reais via MCP nativo.
  - (+) Elimina desperdício de contexto e instruções fantasmas em `.agents/`.
  - (+) Erradica falsos positivos de `SUCCESS`/`APPROVED` na CLI mantendo compatibilidade explícita para `--dry-run`.
- **Contras**:
  - (-) Exige atualização controlada de testes legados que assumiam sucesso em papéis não implementados do `SwarmCoordinator`.

### Opção B: Apenas Camada `.agents/` + MCP (Sem Refatorar CLI)
- **Descrição**: Criar o servidor MCP e limpar `.agents/`, mantendo `cli run`, `swarm` e `system_one` com o comportamento atual.
- **Prós**:
  - (+) Menor superfície de mudança em `src/`.
- **Contras**:
  - (-) Mantém a CLI emitindo `SUCCESS`/`APPROVED` enganosos quando operada diretamente ou por automações.

### Opção C: Simplificação Minimalista (Sem MCP Server)
- **Descrição**: Remover `PreInvocation`, enxugar regras/workflows e documentar uso manual via terminal.
- **Prós**:
  - (+) Zero código novo em `src/corporate_engineer/mcp/`.
- **Contras**:
  - (-) O framework continua invisível como ferramenta nativa para o agente Antigravity.

---

## 4. Decisão Escolhida & Justificativa

Escolhida a **Opção A (Pacote Completo em 3 Pilares)** por resolver simultaneamente a **causa de amnésia/ruído** (hooks e `.agents/`), a **causa de subutilização** (exposição nativa via plugin + servidor MCP `stdio` com menor privilégio) e a **causa de simulação silenciosa** (contratos honestos na CLI e auditoria real dos elos da Invariante 9).

Trade-offs assumidos:
- O servidor MCP exporá apenas ferramentas de leitura e auditoria determinística por padrão (`allow_mutations=False`); qualquer operação mutável exigirá habilitação explícita (`--allow-mutations`).
- O modo `--dry-run` em `AutonomousEngineeringGraph.run_pipeline()` continuará funcional para simulações e testes de pipeline, mas marcado explicitamente como `is_simulated=True` e sem fabricar URLs falsas de PR em caso de erro.

---

## 5. Consequências & Impactos
- **Positivas**:
  - Ferramentas AST, Blast Radius, Scorecard, Secret Scan e Wiring Audit passam a ser invocáveis nativamente pelo agente via MCP.
  - Economia drástica de tokens por turno (`PreInvocation` reduzido de ~4,9 KB/chamada para `<=300` chars no 1º turno ou `{}`) e `state.md` compacto (`<12 KB`).
  - Transparência total entre execução determinística/simulada e execução com executor real na CLI.
- **Negativas / Riscos a Mitigar**:
  - **Segurança MCP**: Mitigada por confinamento estrito de caminhos ao `workspace_root`, ausência de `shell=True` e bloqueio de mutações por padrão.
  - **Quebra de Framing Stdio**: Mitigada garantindo zero escrita em `sys.stdout` além de frames JSON-RPC 2.0 válidos (logs direcionados a `sys.stderr`).
  - **Testes Existentes**: Mitigado via Shift-Left TDD e preservação dos contratos explícitos de `--dry-run` onde aplicável.
