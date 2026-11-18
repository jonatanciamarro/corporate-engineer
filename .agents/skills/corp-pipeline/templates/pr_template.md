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
- [x] Contratos formais definidos e validados
- **Interfaces / DTOs Adicionados ou Modificados**:
```{{LANGUAGE}}
{{CONTRACT_CODE}}
```

---

## 🧪 Evidências de Teste (Fases 2 & 3 - Shift-Left TDD)
- [x] **Certificação RED**: Testes escritos previamente e validados falhando antes da implementação.
- [x] **Certificação GREEN**: Implementação cirúrgica executada e aprovada.
- **Comando de Teste**: `{{TEST_CMD}}`
- **Resultado da Execução**:
```text
{{TEST_OUTPUT}}
```

---

## 🛡️ Pre-Flight Gate & Auditoria Local (Fase 4)
- [x] **Linter**: `{{LINT_CMD}}` (0 erros)
- [x] **Typecheck**: `{{TYPECHECK_CMD}}` (0 erros)
- [x] **Secret Scan**: `python secret_scanner.py` (Nenhum segredo ou token exposto)
- [x] **Regressão Global**: Suíte completa de testes do repositório validada.

---

## 🔄 Plano de Rollback & Contingência
- **Procedimento de reversão**: `git revert <COMMIT_HASH>` ou rollback de imagem de container.
- **Impacto em banco / migrações**: `[ ] N/A` | `[ ] Reversível via migration down` | `[ ] Requer script manual`
- **Métricas a monitorar após deploy**: Latência p99, taxa de erro HTTP 5xx, alertas de APM/Sentry.
