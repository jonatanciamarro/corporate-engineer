# PR-CORP-021: Isolamento Atômico do Motor de Testes de Mutação (Safe Sandbox & Atomic Reversion)

## Tipo de Mudança
- [x] `fix`: Prevenção de corrupção de código e alinhamento de AST
- [x] `feat`: Context manager `AtomicFileSandbox` e modo `use_temp_sandbox`
- [ ] `refactor`: Refatoração estrutural
- [x] `test`: Novos testes automatizados (Shift-Left TDD)
- [x] `docs`: Formalização do ADR-022

## Ticket / ID da Proposta
- **ID**: `IMP-0021`
- **Referência ADR**: [ADR-022](../../docs/adr/ADR-022-atomic-mutation-testing-sandbox.md)
- **Status do Backlog**: `IMPLEMENTED`

---

## Descrição do Pull Request

Este Pull Request implementa a blindagem de isolamento atômico no motor de testes de mutação (`src/corporate_engineer/quality/mutation.py`), corrigindo vulnerabilidades identificadas na auditoria técnica profunda via Swarm (`relatorio_auditoria_swarm.md`):

1. **Context Manager `AtomicFileSandbox` (`src/corporate_engineer/quality/mutation.py`)**:
   - Criação de backup temporário `.bak` do arquivo antes de qualquer mutação.
   - Registro de handlers para `signal.SIGINT`, `signal.SIGTERM` e `atexit` para garantir que o código original seja restaurado mesmo em encerramentos abruptos ou crashes do runner.
   - Bloco `finally` atômico que garante a reversão do arquivo e limpeza do arquivo `.bak`.
   - Suporte a `use_temp_sandbox: bool = False` para isolamento completo em `tempfile.TemporaryDirectory`.

2. **Alinhamento Estrito de AST com `_MutationScannerVisitor`**:
   - Substituição de `ast.walk(tree)` por `_MutationScannerVisitor(ast.NodeVisitor)`, percorrendo a árvore na mesma ordem de profundidade que `_SingleNodeMutator`.
   - Elimina desalinhamentos de numeração de nós (`node_id`) em estruturas com geradores, *list comprehensions* e expressões booleanas aninhadas.

3. **Captura Granular de Erros em `Mutant` (`src/corporate_engineer/models.py`)**:
   - Inclusão do campo `error_message: str | None = None` em `Mutant`.
   - Preservação da mensagem de exceção detalhada em mutantes com status `ERROR` em vez de silenciamento genérico.

4. **Suíte Abrangente de Shift-Left TDD (`tests/test_atomic_mutation_sandbox.py`)**:
   - 9 novos testes unitários validando reversão sob exceção, simulação de sinais `SIGINT/SIGTERM`, consistência de ordem de visitação, captura de `error_message` e execução isolada em sandbox temporário.
   - Suíte global expandida para **243/243 testes PASS** em 23.37s.

---

## Verificações de Pre-Flight (100% Aprovadas)

- [x] **Testes Automatizados**: `pytest` (243/243 PASS)
- [x] **Linter & Formatação**: `ruff check .` e `ruff format --check .` (0 erros)
- [x] **Tipagem Estática**: `mypy .` (0 erros em 71 arquivos)
- [x] **Pre-Flight Secret Scan**: `secret_scanner.py` (0 vazamentos)
