# Pull Request: feat: add ast auto-refactor and self-healing fixer (IMP-0012)

## 📋 Identificação da Demanda
- **Ticket / Issue**: `IMP-0012` (Ref: `CORP-012`)
- **Tipo**: `feat`
- **Módulos Afetados**:
  - `src/corporate_engineer/models.py`
  - `src/corporate_engineer/eval/fixer.py`
  - `src/corporate_engineer/cli.py`
  - `docs/adr/ADR-012-ast-auto-refactor-fixer.md`
  - `.agents/orchestration/improvement-backlog.md`
  - `tests/test_fixer.py`
  - `state.md`
- **Classificação de Risco**: `[x] Baixo` | `[ ] Médio` | `[ ] Alto` | `[ ] Crítico`
- **Branch**: `feat/IMP-0012-ast-auto-refactor` ➔ `main`

---

## 🎯 Resumo Executivo da Mudança

Esta entrega implementa a proposta **`IMP-0012`** do backlog contínuo de melhorias (`improvement-backlog.md`), consolidando o **AST Auto-Refactor & Self-Healing Fixer** no framework `corporate-engineer`.

O recurso introduz um motor cirúrgico de auto-remediação baseado em `ast.NodeTransformer` que elimina violações sintáticas e de tipagem comuns de forma determinística, segura e em sub-100ms. Cada transformação é protegida por um guardrail de risco do Sistema 1 (`SystemOneRouter.assess_risk`), assegurando que refatorações não degradem contratos de API pública ou introduzam riscos de regressão.

### Principais Entregas:

1. **Modelos DTO Pydantic v2 (`src/corporate_engineer/models.py`)**:
   - `FixDetail`: Registra os detalhes de cada correção aplicada cirurgicamente (`file_path`, `rule_name`, `line_number`, `description`, `original_snippet`, `fixed_snippet`).
   - `FixReport`: Relatório consolidado contendo contadores de arquivos, correções aplicadas, modo dry-run e classificação de risco do Sistema 1.

2. **Motor AST NodeTransformer (`src/corporate_engineer/eval/fixer.py`)**:
   - `InitReturnAnnotationFixer`: Insere automaticamente `-> None` em métodos `__init__` sem tipagem de retorno.
   - `MutableDefaultArgumentFixer`: Substitui argumentos padrão mutáveis (`[]`, `{}`) por `None` e injeta preâmbulo de inicialização segura no corpo preservando docstrings.
   - `RedundantPassCleaner`: Remove comandos `pass` supérfluos em funções e classes que já possuem docstrings ou declarações.
   - `ASTSelfHealingFixer`: Orquestrador com validação sintática pós-remediação (`ast.parse`), preservação de formatação quando inalterado e guardrail de risco do Sistema 1.

3. **Subcomando CLI de Primeira Classe (`src/corporate_engineer/cli.py`)**:
   - `corporate-engineer fix`:
     - `--auto`: Aplica e grava correções nos arquivos fonte.
     - `--dry-run`: Executa simulação em memória exibindo o diff sem alterar disco.
     - `--path <path>`: Alvo das transformações (arquivo individual ou pacote).
     - `--format [text|json]`: Suporte a saída amigável ou JSON estruturado.

---

## 🧪 Evidências de Teste (Shift-Left TDD)

- [x] **Certificação RED**: Testes em `tests/test_fixer.py` foram criados previamente e falharam antes da codificação.
- [x] **Certificação GREEN**: 100% dos testes aprovados após a implementação.
- [x] **Expansão da Suíte**: De 130 para **138 testes passando** em 18.56s.
- [x] **Cobertura Global**: **88%** de cobertura mantida no repositório (`pytest-cov`).

---

## 🛡️ Quality Gate & Pre-Flight Verification

- [x] **Linter (Ruff)**: 0 erros (`ruff check .`).
- [x] **Formatador (Ruff)**: 83 arquivos verificados e formatados (`ruff format --check .`).
- [x] **Tipagem Estática (Mypy)**: 0 erros em 51 arquivos fonte (`mypy .`).
- [x] **Scanner de Segredos**: 0 credenciais ou tokens expostos (`secret_scanner.py .`).
- [x] **Zero Regressões**: 138/138 testes automatizados 100% verdes.
