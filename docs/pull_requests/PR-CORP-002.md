# Pull Request: feat: add venv stack detection, mcp circuit breaker and ast sha256 caching

## 📋 Identificação da Demanda
- **Ticket / Issue**: `IMP-0001`, `IMP-0002`, `IMP-0004` (Ref: `CORP-002`)
- **Tipo**: `feat`
- **Módulos Afetados**:
  - `.agents/skills/corp-pipeline/scripts/`
  - `src/corporate_engineer/mcp/`
  - `src/corporate_engineer/rag/`
  - `.agents/orchestration/`
  - `tests/`
  - `state.md`
- **Classificação de Risco**: `[x] Baixo` | `[ ] Médio` | `[ ] Alto` | `[ ] Crítico`
- **Branch**: `feat/corp-pipeline-enhancements-imp001-002-004` ➔ `main`
- **Commit**: `a456cf36f09a104f2a64b9d393f425bafeca6dc0`

---

## 🎯 Resumo Executivo da Mudança

Esta entrega implementa formalmente três melhorias de alta prioridade catalogadas no backlog contínuo de melhorias (`improvement-backlog.md`) do framework `corporate-engineer`, consolidando automação, resiliência e performance:

### 1. `IMP-0001` — Detecção Automática de `.venv` no `stack_detector.py`
- **Problema Resolvido**: Execuções fora do ambiente virtual ativo podiam invocar ferramentas globais desprovidas de pacotes necessários (`hypothesis`, `pytest-cov`, `pydantic`), gerando falsos negativos no pipeline.
- **Implementação**:
  - Inspeciona o diretório raiz em busca de `.venv` ou `venv`.
  - Resolve caminhos relativos determinísticos para os binários: `.venv\Scripts\<tool>` em Windows e `.venv/bin/<tool>` em ambientes POSIX.
  - Exporta `venv_detected: bool` e `venv_path: str` no payload JSON retornado pela ferramenta.
- **Testes**: Cobertura completa em [tests/test_stack_detector.py](file:///c:/Users/WDAGUtilityAccount/Downloads/Nova%20pasta%20%282%29/tests/test_stack_detector.py).

### 2. `IMP-0002` — Padrão Circuit Breaker com Reconexão em `circuit_breaker.py`
- **Problema Resolvido**: Ausência de proteção contra sobrecarga em endpoints MCP degradados e lentidão em falhas de rede em streaming SSE.
- **Implementação**:
  - Implementada a máquina de estados finita completa do Circuit Breaker:
    - `CLOSED`: Operação normal; falhas consecutivas incrementam contador até o limiar (`failure_threshold`).
    - `OPEN`: Chamadas rejeitadas imediatamente com `CircuitBreakerOpenError`, poupando recursos de rede.
    - `HALF_OPEN`: Período de teste transitório após o tempo de recuperação (`recovery_timeout`); sucesso fecha o circuito, nova falha reabre.
  - Integração sem quebras com [RemoteMCPSSEClient](file:///c:/Users/WDAGUtilityAccount/Downloads/Nova%20pasta%20%282%29/src/corporate_engineer/mcp/client.py).
  - Cobertura de 100% de linhas no módulo [src/corporate_engineer/mcp/circuit_breaker.py](file:///c:/Users/WDAGUtilityAccount/Downloads/Nova%20pasta%20%282%29/src/corporate_engineer/mcp/circuit_breaker.py).
- **Testes**: Suíte dedicada em [tests/test_circuit_breaker.py](file:///c:/Users/WDAGUtilityAccount/Downloads/Nova%20pasta%20%282%29/tests/test_circuit_breaker.py).

### 3. `IMP-0004` — Cache de Indexação AST Baseado em SHA-256 (`cached_ast_indexer.py`)
- **Problema Resolvido**: Custo de re-parsing via `ast.parse` em repositórios grandes para arquivos não modificados.
- **Implementação**:
  - Criada a classe `CachedASTCodebaseIndexer` herdando de `ASTCodebaseIndexer`.
  - Cálculo de hash SHA-256 de conteúdo (`content-hash-cache-pattern`).
  - Persistência estruturada em `.cache/ast_index_cache.json`.
  - Cache hits evitam re-parsing completo de símbolos e importações; invalidação automática imediata se o conteúdo do arquivo for alterado.
  - Métodos `clear_cache()` e `get_cache_stats()` para introspecção e métricas de hits/misses.
- **Testes**: Suíte dedicada em [tests/test_cached_ast_indexer.py](file:///c:/Users/WDAGUtilityAccount/Downloads/Nova%20pasta%20%282%29/tests/test_cached_ast_indexer.py).

---

## 🧪 Evidências de Teste (Shift-Left TDD)

- [x] **Certificação RED**: Todos os 3 novos componentes foram precedidos de testes com falhas comprovadas antes da codificação.
- [x] **Certificação GREEN**: 100% dos testes aprovados após a implementação cirúrgica.
- [x] **Expansão da Suíte**: De 48 para **62 testes passando**.
- [x] **Cobertura Global**: **92%** de cobertura de código (`pytest-cov`).

### Relatório de Execução do Pytest
```text
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.2.0, pluggy-1.7.0
rootdir: C:\Users\WDAGUtilityAccount\Downloads\Nova pasta (2)
configfile: pyproject.toml
testpaths: tests
plugins: hypothesis-6.170.16, cov-7.1.0
collected 62 items

tests\test_ast_indexer.py ......                                         [  9%]
tests\test_cached_ast_indexer.py ....                                    [ 16%]
tests\test_circuit_breaker.py .......                                    [ 27%]
tests\test_cli.py ................                                       [ 53%]
tests\test_mcp_client.py .........                                       [ 67%]
tests\test_models.py ........                                            [ 80%]
tests\test_orchestrator.py .......                                       [ 91%]
tests\test_quality_gate.py ..                                            [ 95%]
tests\test_stack_detector.py ...                                         [100%]

=============================== tests coverage ================================
_______________ coverage: platform win32, python 3.11.9-final-0 _______________

Name                                               Stmts   Miss  Cover   Missing
--------------------------------------------------------------------------------
src\corporate_engineer\__init__.py                     1      0   100%
src\corporate_engineer\cli.py                        192     14    93%   197, 213, 241, 249, 261-263, 269-271, 274, 285, 301, 324
src\corporate_engineer\mcp\__init__.py                 3      0   100%
src\corporate_engineer\mcp\circuit_breaker.py         74      0   100%
src\corporate_engineer\mcp\client.py                 126     16    87%   115, 134, 146, 164, 170, 184, 203-204, 252, 262-271, 283-284
src\corporate_engineer\models.py                      46      0   100%
src\corporate_engineer\orchestrator\__init__.py        0      0   100%
src\corporate_engineer\orchestrator\graph.py          93      4    96%   61, 102, 118-119
src\corporate_engineer\quality\__init__.py             0      0   100%
src\corporate_engineer\quality\gate.py                31      4    87%   41-42, 77-78
src\corporate_engineer\rag\__init__.py                 3      0   100%
src\corporate_engineer\rag\ast_indexer.py             93      6    94%   21-22, 49-50, 77-78
src\corporate_engineer\rag\cached_ast_indexer.py      83     12    86%   34-35, 43-44, 49-50, 58, 86, 115-116, 126-127
--------------------------------------------------------------------------------
TOTAL                                                745     56    92%
============================= 62 passed in 9.96s ==============================
```

---

## 🛡️ Pre-Flight Quality Gate & Auditoria Local

| Verificação | Comando | Resultado |
|---|---|---|
| **Testes Unitários & PBT** | `pytest` | 🟢 **62 passed (100%)** |
| **Linter PEP 8 (Ruff)** | `ruff check .` | 🟢 **0 errors** |
| **Formatador de Código** | `ruff format --check .` | 🟢 **34 files formatted** |
| **Checagem de Tipos (Mypy)** | `mypy .` | 🟢 **0 errors in 22 files** |
| **Secret Scanner Corporativo** | `python .agents/skills/corp-pipeline/scripts/secret_scanner.py .` | 🟢 **Zero segredos expostos** |

---

## 📦 Arquivos Alterados no PR

```text
.agents/orchestration/improvement-backlog.md       |   8 +-
.agents/skills/corp-pipeline/scripts/stack_detector.py |  51 ++++++--
src/corporate_engineer/mcp/__init__.py             |  15 +++
src/corporate_engineer/mcp/circuit_breaker.py      | 117 ++++++++++++++++++
src/corporate_engineer/mcp/client.py               |  30 ++++-
src/corporate_engineer/rag/__init__.py             |   8 ++
src/corporate_engineer/rag/cached_ast_indexer.py   | 135 +++++++++++++++++++++
state.md                                           |  24 ++--
tests/test_cached_ast_indexer.py                   |  85 +++++++++++++
tests/test_circuit_breaker.py                      | 113 +++++++++++++++++
tests/test_stack_detector.py                       |  58 +++++++++
11 files changed, 614 insertions(+), 30 deletions(-)
```

---

## 🔄 Plano de Rollback & Contingência
- **Procedimento de reversão**:
  ```powershell
  git checkout main
  git branch -D feat/corp-pipeline-enhancements-imp001-002-004
  ```
- **Impacto em dados**: Nenhum (arquivos de cache `.cache/ast_index_cache.json` podem ser excluídos a frio sem efeitos colaterais).
- **Compatibilidade Retroativa**: 100% mantida. Todos os métodos originais de `RemoteMCPSSEClient` e `ASTCodebaseIndexer` mantêm as mesmas assinaturas e retornos esperados.
