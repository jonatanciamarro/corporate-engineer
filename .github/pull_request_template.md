## 📋 Identificação da Demanda
- **Ticket / Issue**: `{{TICKET_ID}}`
- **Tipo**: `feat` | `fix` | `refactor` | `perf` | `chore`
- **Módulo Afetado**: `{{MODULE_NAME}}`
- **Classificação de Risco**: `[ ] Baixo` | `[ ] Médio` | `[ ] Alto` | `[ ] Crítico`

---

## 🎯 Resumo da Mudança
> Descrição executiva e concisa do que foi implementado, resolvido ou refatorado.

{{SUMMARY}}

---

## 📐 Contratos e DTOs (Fase 1)
- [x] Contratos formais definidos e validados via Pydantic
- **Interfaces / DTOs Adicionados ou Modificados**:
```python
{{CONTRACT_CODE}}
```

---

## 🧪 Evidências de Teste (Fases 2 & 3 - Shift-Left TDD)
- [x] **Certificação RED**: Testes escritos previamente e validados falhando antes da implementação.
- [x] **Certificação GREEN**: Implementação cirúrgica executada e aprovada.
- **Comando de Teste**: `pytest tests/`

---

## 🛡️ Pre-Flight Gate & Auditoria Local (Fase 4)
- [x] **Linter**: `ruff check src tests` (0 erros)
- [x] **Typecheck**: `mypy src` (0 erros)
- [x] **Secret Scan**: `python .agents/skills/corp-pipeline/scripts/secret_scanner.py .` (Zero credenciais expostas)
- [x] **Regressão Global**: Suíte completa de testes unitários e de integração validada.

---

## 🔄 Plano de Rollback & Contingência
- **Procedimento de reversão**: `git revert <COMMIT_HASH>`
- **Impacto em banco / migrações**: N/A
