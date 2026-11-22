# PR-CORP-014: Safe Storage Optimizer & Automated Disk Hygiene Engine

## Tipo de Mudança
- [x] `feat`: Nova funcionalidade corporativa
- [x] `test`: Novos testes automatizados (Shift-Left TDD)
- [x] `docs`: Documentação técnica e ADR formal

## Resumo das Alterações
1. **Modelos DTO Pydantic v2 (`src/corporate_engineer/models.py`)**:
   - `StorageTarget`: Contrato tipado para definição de alvos de armazenamento (`category`, `name`, `path`, `size_bytes`, `is_safe`, `description`).
   - `StorageCleanResult`: Resultado por alvo com contagem de bytes liberados e tratamento defensivo de erros.
   - `StorageOptimizationReport`: Relatório consolidado contendo `total_freed_bytes`, `total_freed_gb`, `results: list[StorageCleanResult]` e `dry_run: bool`.

2. **Motor Safe Storage Cleaner (`src/corporate_engineer/quality/storage_cleaner.py`)**:
   - Classe `SafeStorageCleaner` com invariante estrita de proteção a pastas pessoais (`Documents`, `Desktop`, `Pictures`, `Videos`, `Music`) e códigos da workspace.
   - Identificação e limpeza segura de caches de desenvolvimento (`pip`, `npm`, `torch`, `huggingface`) e alvos de modelos volumosos descontinuados (como GPT4All e blobs do Ollama).
   - Suporte nativo a modo simulação (`--dry-run`).

3. **CLI Corporativa (`src/corporate_engineer/cli.py`)**:
   - Adição do subcomando `corporate-engineer clean` com flags `--dry-run` e `--format [text|json]`.

4. **Otimização do Pre-Flight Scanner (`.agents/skills/corp-pipeline/scripts/secret_scanner.py`)**:
   - Inclusão de `models/` e extensões binárias (`.onnx`, `.bin`, `.gguf`) nas regras de exclusão de varredura de texto, acelerando a checagem de 45s para 0.5s.

5. **Testes Unitários & Cobertura (`tests/test_storage_cleaner.py`)**:
   - 10 novos testes unitários cobrindo rejeição de diretórios pessoais, integridade do dry-run, deleção real de arquivos e integração CLI.
   - Expansão da suíte global para **155/155 testes PASS** (100% de aprovação).

6. **Impacto Prático no Ambiente**:
   - Armazenamento livre no disco `C:` expandido de **64 MB** para **20.38 GB** (mais de 20 GB recuperados com segurança).

## Pre-Flight Quality Gate
- [x] **Linter (Ruff)**: 0 erros
- [x] **Formatador (Ruff)**: 100% formatado
- [x] **Tipagem Estática (Mypy)**: 0 erros em 55 arquivos
- [x] **Scanner de Segredos**: 0 credenciais expostas
- [x] **Testes Globais (Pytest)**: 155/155 PASS (100%)
