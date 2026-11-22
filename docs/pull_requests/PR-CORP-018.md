# Pull Request: feat(prompt): Context-Aware Metaprompt Engine & Prompt Refiner (IMP-0018)

## 📋 Identificação da Demanda
- **Ticket / Issue**: `IMP-0018`
- **Tipo de Alteração**: `feat`
- **Escopo**: `prompt`
- **ADR Associado**: [ADR-018: Context-Aware Metaprompt Engine & Prompt Refiner](../adr/ADR-018-context-aware-metaprompt-engine.md)

---

## 🎯 Resumo das Modificações

Implementação da **Fase 0.5: Context-Aware Metaprompt Engine & Prompt Refiner (IMP-0018)** para transformar prompts humanos informais ou concisos em especificações de engenharia estruturadas, contextualizadas e ancoradas no código real do repositório antes da submissão ao pipeline completo:

1. **Modelos DTO Pydantic v2 (`src/corporate_engineer/models.py`)**:
   - `RevisedPromptSpec`: Contrato tipado com `raw_prompt`, `target_domain`, `core_intent`, `functional_requirements`, `non_functional_requirements` (invariantes corporativas), `affected_modules`, `out_of_scope` (guardrails anti-overengineering), `tdd_test_scenarios`, `metaprompt` sintetizado, `confidence_score`, flags de bypass (`is_bypassed`, `bypass_reason`) e `timestamp`.

2. **Motor de Refinamento Contextual (`src/corporate_engineer/prompt/refiner.py`)**:
   - **Fast-Path Bypass Condicional**: Identificação determinística de comandos operacionais (`pytest`, `git status`, `/preflight`, queries curtas) para execução imediata sem custo/latência de reescrita.
   - **Bypass Gate Override**: Possibilidade de forçar refinamento com `--bypass-gate`.
   - **Detecção de Domínios Corporativos**: Mapeamento inteligente para `mcp`, `orchestrator`, `rag`, `system_one`, `quality` ou `cli`.
   - **AST & Symbol Grounding**: Extração de símbolos de código e classes referenciadas no repositório.
   - **Síntese de Metaprompt Padronizado**: Geração de markdown com requisitos funcionais, invariantes corporativas, guardrails de escopo e cenários TDD para a fase RED.

3. **CLI Corporativa (`src/corporate_engineer/cli.py`)**:
   - Novo subcomando `corporate-engineer prompt refine <prompt>` com suporte a:
     - `--bypass-gate` / `-b`: ignora fast-path operacional e força refinamento;
     - `--format`: visualizações em `text`, `json` ou `markdown`;
     - `--workspace` / `-w`: caminho do workspace para resolução de AST;
     - `--output` / `-o`: exportação da especificação gerada para arquivo.

4. **Suíte de Testes Automatizados (Shift-Left TDD)**:
   - 9 novos testes unitários e de integração em `tests/test_metaprompt_engine.py` (100% PASS, 95% cobertura no módulo).
   - Expansão da suíte global para **179/179 testes PASS**.

---

## 🧪 Evidências de Teste & Qualidade

```text
============================= test session starts =============================
platform win32 -- Python 3.10.6, pytest-9.2.0, pluggy-1.7.0
plugins: hypothesis-6.168.5, cov-7.1.0
collected 179 items

179 passed in 16.44s (Suíte 100% verde)
Coverage src/corporate_engineer/prompt: 95%
Ruff Linter & Formatter: 0 erros / 105 arquivos formatados
Mypy Strict Type Check: Success: no issues found in 62 source files
Pre-Flight Secret Scanner: PASS (0 segredos ou credenciais expostas)
```

---

## 🔒 Checklist de Qualidade Pre-Flight
- [x] Testes unitários cobrindo caminhos felizes, bypass e erros
- [x] Tipagem estrita Pydantic v2 sem `Any` desnecessário
- [x] Compatibilidade Python 3.10+ / 3.11 assegurada
- [x] Zero erros no linter (`ruff check .`)
- [x] Zero erros no formatador (`ruff format --check .`)
- [x] Zero erros na tipagem estática (`mypy .`)
- [x] Zero credenciais ou segredos expostos (`secret_scanner.py`)
- [x] ADR formalizado em `docs/adr/ADR-018-context-aware-metaprompt-engine.md`
- [x] Atualização de `state.md` e `improvement-backlog.md`
