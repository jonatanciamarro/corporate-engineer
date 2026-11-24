# ADR-025: Conexão Total de Módulos Desconectados, Unificação de Cache AST SHA-256 e Enriquecimento do Pipeline E2E (IMP-0026)

## Status
Aceito (Accepted)

## Data
2026-11-22

## Contexto & Motivação
A auditoria técnica concorrente conduzida via Swarm Max com 4 agentes especialistas (`audit-rag-cache`, `audit-pipeline-conn`, `audit-eval-quality`, `audit-dead-obsolete`) identificou que, embora o framework possua 25 melhorias de alta sofisticação, diversos componentes operavam de forma isolada ou desconectada:
1. **Desconexão de Cache AST**:
   - `BlastRadiusAnalyzer` (IMP-0008) declarava `self.indexer = ASTCodebaseIndexer(...)` sem uso real, re-parseando todos os arquivos da base com `ast.parse` síncrono e `rglob("*.py")`, sem usufruir do `CachedASTCodebaseIndexer` baseado em hash SHA-256 (IMP-0004).
   - `SurgicalTestRunner` chamava `analyze_file()` em loop para cada arquivo modificado, re-varrendo a base inteira repetidamente.
   - `ContextAwarePromptRefiner.find_ast_symbols()` realizava leituras textuais ingênuas em disco em vez de consultar os símbolos do cache AST em memória.
2. **Desconexão no `AutonomousEngineeringGraph.run_pipeline`**:
   - O pipeline autônomo não acionava o `ProactiveAnticipator` (IMP-0025) na fase de planejamento.
   - Não executava auto-cura sintática via `ASTSelfHealingFixer` (IMP-0012) na fase de implementação.
   - Não executava testes cirúrgicos via `SurgicalTestRunner` (IMP-0010) na fase TDD.
   - Não avaliava o código gerado via `SemanticCodeEvaluator` (IMP-0007 / Scorecard EDD) no portão de auditoria.
   - Não gerava a URL de PR 1-clique com garantia de push remoto na fase de entrega (`DELIVER`).
3. **Fragmentação de Scanners de Segredos e Gates**:
   - Havia 3 implementações de regexes de segredos (`QualityGateRunner`, `tool_security_guard`, `secret_scanner.py`).
   - `SemanticCodeEvaluator` e `SafeStorageCleaner` rodavam apenas em subcomandos isolados da CLI (`eval` e `clean`), ausentes do `QualityGateRunner`.
4. **Omissões de Exportações Públicas**:
   - Pacotes com `__init__.py` sem símbolos exportados e imports mortos em arquivos de teste.

## Decisão de Arquitetura

1. **Unificação do Cache AST SHA-256**:
   - `BlastRadiusAnalyzer` passa a consumir `CachedASTCodebaseIndexer` nativamente, reaproveitando árvores sintáticas baseadas em hash de conteúdo e fornecendo método de análise em lote `analyze_files(changed_files)`.
   - `ContextAwarePromptRefiner.find_ast_symbols()` passa a consultar o conjunto de símbolos do `CachedASTCodebaseIndexer`, atingindo resolução O(1) em memória sem I/O repetitivo.

2. **Amarração E2E Completa em `AutonomousEngineeringGraph.run_pipeline`**:
   - **PLANNING**: Integração com `ProactiveAnticipator` gerando o `AnticipationPlan` (Passos 1 e 2, risco e subagentes).
   - **TDD**: Identificação de testes afetados via `SurgicalTestRunner`.
   - **IMPLEMENT**: Aplicação do `ASTSelfHealingFixer` para auto-remediação sintática e formatação pós-escrita.
   - **AUDIT**: Verificação de qualidade semântica via `SemanticCodeEvaluator` integrada à validação estrita de testes e segredos.
   - **DELIVER**: Instrumentação do relatório de execução com URL pré-preenchida de PR via `git_utils.generate_pr_url(ensure_pushed=True)`.

3. **Unificação de Qualidade**:
   - Criação de `corporate_engineer.quality.secret_scanner` como Single Source of Truth para padrões de credenciais.
   - Enriquecimento de `QualityGateRunner` para executar verificação de complexidade semântica via `SemanticCodeEvaluator`.

4. **Normalização de `__init__.py` e Limpeza de Código Morto**:
   - Exportação formal dos componentes públicos em `corporate_engineer/__init__.py` e subpacotes.
   - Remoção de imports não utilizados (ex: `import os` em testes).

## Consequências
- Desempenho significativamente superior em tempo de indexação e cálculo de blast radius (eliminação de I/O redundante).
- O pipeline autônomo passa a usar 100% dos motores construídos, elevando a inteligência, confiabilidade e sinergia do framework.
- Zero impacto regressivo na suíte de testes.
