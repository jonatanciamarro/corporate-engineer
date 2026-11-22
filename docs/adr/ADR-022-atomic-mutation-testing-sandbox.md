# ADR-022: Isolamento Atômico do Motor de Testes de Mutação (Safe Sandbox & Atomic Reversion)

## Status
Aceito (Accepted)

## Data
2026-11-22

## Contexto & Motivação
Na auditoria técnica profunda realizada pelo Swarm (`relatorio_auditoria_swarm.md`), identificou-se um ponto crítico de risco no motor de testes de mutação (`src/corporate_engineer/quality/mutation.py`):
1. **Risco de Corrupção Permanente de Código em Disco**:
   O `ASTMutationEngine` aplicava mutações sobrescrevendo o arquivo-alvo diretamente no disco (`target_path.write_text(...)`) e dependia exclusivamente de um bloco `finally` síncrono para restaurar o código original. Se o processo fosse interrompido abruptamente por `SIGINT` (Ctrl+C), `SIGTERM`, timeout de CI ou crash prematuro do runner, o código de produção permanecia corrompido em disco sem restauração.
2. **Desalinhamento de Travessia entre Scanner e Mutator**:
   O scanner de pontos de mutação (`scan_mutation_points`) utilizava `ast.walk(tree)`, cujo percurso em fila/largura diverge da ordem de visita em profundidade do `_SingleNodeMutator(ast.NodeTransformer)`. Em expressões com geradores, *list comprehensions* ou comparações aninhadas, a numeração `node_id` sofria descompasso (*drift*), gerando mutações não aplicadas ou divergentes.
3. **Erros Silenciosos no Registro de Mutantes**:
   Em `mutation.py:243`, capturas genéricas `except Exception:` marcavam o status como `"ERROR"`, mas descartavam completamente a mensagem e stack trace da exceção, impedindo a identificação de `SyntaxError` induzidos por mutações inválidas.

A proposta **IMP-0021** introduz o `AtomicFileSandbox`, garantia de reversão via traps de sinais do sistema operacional (`atexit` / `signal`), alinhamento estrito de AST via `NodeVisitor` e rastreamento granular de erros no modelo `Mutant`.

## Decisão de Arquitetura

1. **Context Manager `AtomicFileSandbox` (`src/corporate_engineer/quality/mutation.py`)**:
   - Criação de backup temporário `.bak` do arquivo original antes de qualquer escrita.
   - Registro de handlers para `signal.SIGINT`, `signal.SIGTERM` e `atexit` que garantem a restauração do arquivo original mesmo em encerramentos abruptos.
   - Restauração garantida do código original e expurgo limpo do backup temporário no encerramento normal ou excepcional.
   - Suporte opcional a `use_temp_sandbox=True` para execução em diretório temporário totalmente isolado via `tempfile.TemporaryDirectory`.

2. **Alinhamento Estrito de Travessia AST com `_MutationScannerVisitor`**:
   - Substituição de `ast.walk(tree)` por `_MutationScannerVisitor(ast.NodeVisitor)`.
   - Implementação dos mesmos métodos de visitação (`visit_Compare`, `visit_BinOp`, `visit_Constant`) na mesma ordem do `_SingleNodeMutator`, assegurando mapeamento 1:1 exato e determinístico dos identificadores de nós.

3. **Enriquecimento do Modelo `Mutant` (`src/corporate_engineer/models.py`)**:
   - Inclusão do campo opcional `error_message: str | None = None` no modelo DTO `Mutant`.
   - Em caso de falha durante a execução de mutantes, a mensagem da exceção é preservada no relatório para diagnóstico.

4. **Shift-Left TDD (`tests/test_atomic_mutation_sandbox.py`)**:
   - Validação da reversão automática do arquivo em disco sob exceções intencionais.
   - Validação da recuperação sob sinais de interrupção e traps de encerramento.
   - Validação de consistência de IDs de mutação em estruturas aninhadas e *comprehensions*.
   - Validação de captura e serialização de `error_message` no relatório `MutationReport`.

## Consequências

- **Positivas**:
  - Imunidade comprovada contra corrupção acidental do repositório durante testes de mutação.
  - Consistência matemática determinística na geração e aplicação de mutantes na árvore sintática.
  - Rastreabilidade detalhada de causas de erro em mutantes com status `ERROR`.
  - Compatibilidade retroativa integral com a CLI `corporate-engineer audit` e fluxos de mutação existentes.
- **Negativas / Riscos**:
  - Pequeno overhead de cópia em disco na criação do arquivo `.bak` por execução de suíte, insignificante diante do ganho de resiliência.
