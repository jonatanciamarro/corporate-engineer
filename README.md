# Corporate Engineer

Framework Python (3.10+) para **engenharia de software assistida por agentes**, análise estática baseada em AST, testes cirúrgicos por *blast radius*, *mutation testing* em sandbox, auditoria de segurança e governança de entrega.

---

## Arquitetura do Pacote (`src/corporate_engineer/`)

| Subsistema | Responsabilidade | Módulos Principais |
|---|---|---|
| **Code Intelligence (`rag/`)** | Indexação AST de classes/herança/chamadas, cache persistente por SHA-256 e análise de *blast radius* via BFS | `ast_indexer.py`, `cached_ast_indexer.py`, `impact.py` |
| **Qualidade & Segurança (`quality/`)** | Sandbox de *mutation testing* com isolamento de `PYTHONPATH`, seleção cirúrgica de testes via `git diff`, scanner canônico de segredos, auditoria de *auto-wiring* e limpeza segura de caches | `mutation.py`, `surgical_runner.py`, `secret_scanner.py`, `wiring_auditor.py`, `storage_cleaner.py`, `gate.py` |
| **Eval & Auto-Remediação (`eval/`)** | Scorecard semântico em 5 eixos e refatorações AST determinísticas (`-> None` em `__init__`, remoção de defaults mutáveis e `pass` redundante) | `scorecard.py`, `fixer.py` |
| **MCP & Resiliência (`mcp/`)** | Adaptador local sandboxed (`shell=False`, allowlist e bloqueio de path traversal), cliente HTTP/JSON-RPC remoto com Bearer auth, `CircuitBreaker` e hub multi-servidor | `client.py`, `hub.py`, `circuit_breaker.py` |
| **Orquestração & Telemetria (`orchestrator/`, `telemetry/`)** | Máquina de estados FSM com checkpoints (`PLANNING → TDD → IMPLEMENT → AUDIT → DELIVER`), antecipador de escopo, loop adversarial e tracing compatível com OpenTelemetry via `ContextVar` | `graph.py`, `anticipator.py`, `swarm.py`, `adversarial.py`, `tracer.py` |
| **System One & LoRA (`system_one/`, `lora/`, `prompt/`)** | Roteamento determinístico por heurísticas, harness de benchmark, refinador contextual de prompts e gerador/validador/exportador JSONL para Vertex AI SFT | `router.py`, `heuristic_engine.py`, `benchmark.py`, `refiner.py`, `lora/` |
| **Contratos & CLI (`models.py`, `cli/`)** | Modelos Pydantic v2 e CLI modular dividida por domínio | `models.py`, `cli/parser.py`, `cli/commands/` |

---

## Instalação & Quickstart

```bash
python -m venv .venv
# Windows (PowerShell): .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate

pip install -e ".[dev,test]"
```

### Comandos Principais da CLI

```bash
# Auditoria de auto-wiring (verifica exportação, testes e orfandade em src/)
corporate-engineer audit --wiring

# Scorecard semântico AST (complexidade, tipagem, contratos)
corporate-engineer eval src/corporate_engineer/

# Indexação AST e cálculo de blast radius
corporate-engineer index --path src/
corporate-engineer blast-radius --target src/corporate_engineer/mcp/client.py

# Seleção e execução cirúrgica de testes afetados pelo git diff
corporate-engineer test-surgical

# Auto-remediação AST determinística (dry-run ou aplicando alterações)
corporate-engineer fix --auto --path src/

# Simulação completa do pipeline com checkpoints em disco
corporate-engineer run --ticket DEMO-101 --task "Auditar módulo MCP" --dry-run
```

---

## Status de Maturidade dos Módulos

Transparência sobre o estado atual de implementação (detalhes e roadmap em [improvement-backlog.md](./.agents/orchestration/improvement-backlog.md)):

- **Determinísticos / Prontos para Uso**:
  - `rag/` (`ASTCodebaseIndexer`, `CachedASTCodebaseIndexer`, `BlastRadiusAnalyzer`)
  - `quality/` (`ASTMutationEngine`, `SurgicalTestRunner`, `CanonicalSecretScanner`, `SafeStorageCleaner`, `CapabilityWiringAuditor`, `QualityGateRunner`)
  - `eval/` (`SemanticCodeEvaluator`, `ASTSelfHealingFixer`)
  - `mcp/` (`LocalMCPToolAdapter` com `shell=False` e proteção de traversal, `CircuitBreaker`, `MCPEnterpriseHub`)
  - `telemetry/` (`AgentTracer` com `contextvars.ContextVar`)
- **Protótipos / Heurísticos (Roadmap P1–P2)**:
  - `system_one/`: `HeuristicDecisionEngine` está funcional e offline; `ONNXNLIDecisionEngine` e `OutlinesDecisionEngine` atualmente operam com fallback heurístico (`IMP-0036`).
  - `orchestrator/swarm.py` & `graph.py`: operam em modo determinístico/simulado com templates e análise local até a integração de executores plugáveis (`IMP-0038`).
  - `mcp/client.py` (`RemoteMCPSSEClient`): atualmente consome respostas JSON-RPC HTTP síncronas; suporte nativo a streaming `text/event-stream` está mapeado em `IMP-0037`.

---

## Qualidade, Testes & CI

O projeto mantém gate estrito local e no GitHub Actions ([ci.yml](./.github/workflows/ci.yml) e [self-heal.yml](./.github/workflows/self-heal.yml)):

```bash
ruff check .
ruff format --check .
mypy .
python .agents/skills/corp-pipeline/scripts/secret_scanner.py .
pytest -q
```

---

## Governança & Documentação

- **Decisões de Arquitetura (ADRs)**: [docs/adr/](./docs/adr/)
- **Backlog Contínuo de Melhorias**: [.agents/orchestration/improvement-backlog.md](./.agents/orchestration/improvement-backlog.md)
- **Pipeline Corporativo & Skills**: [.agents/skills/corp-pipeline/SKILL.md](./.agents/skills/corp-pipeline/SKILL.md)
