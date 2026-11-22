# ADR-023: Autonomous Proactive Intelligence & Full E2E Lifecycle Hook Suite (IMP-0025)

## Status
Aceito (Accepted)

## Data
2026-11-22

## Contexto & Motivação
O framework `corporate-engineer` desenvolveu diversos componentes de inteligência de ponta ao longo de 24 melhorias:
1. `ContextAwarePromptRefiner`: extração semântica de intenção, ancoragem AST e refinamento de requisitos.
2. `SystemOneRouter`: classificação ultrarrápida de intenção, seleção de agentes e estimativa de risco.
3. `ASTSelfHealingFixer`: auto-remediação sintática de anti-padrões AST em código Python.
4. `ChangePropagationAnalyzer` / `BlastRadius`: rastreamento de impacto de alterações e testes afetados.
5. `SafeStorageCleaner`: auditoria de espaço e higiene de armazenamento.
6. `QualityGateRunner` / `secret_scanner.py`: contenção contra vazamento de credenciais e validação estrita.
7. `git_utils`: geração de link de PR 1-clique com push remoto mandatório.

Contudo, muitos desses mecanismos operavam de forma sob demanda ou manual via CLI. Faltava amarrar esses componentes em um ciclo contínuo, automático e proativo, no qual a inteligência opera **sempre 2 passos à frente**:
- **Antes da resposta do modelo (`PreInvocation`)**: antecipa intenção, riscos, domínios, AST symbols, subagentes ideais e planeja os passos +1 (imediato: contratos e TDD) e +2 (subsequente: implementação cirúrgica, auto-cura e gates de entrega).
- **Antes da escrita em disco (`PreToolUse`)**: Zero-Secret Guard ativo para bloquear qualquer tentativa de persistir segredos em arquivos de código.
- **Após a escrita em disco (`PostToolUse`)**: auto-cura de AST imediata (`fixer.py`), formatação automática (`ruff format`) e cálculo automático de blast radius para orientar testes cirúrgicos.
- **Na inicialização de sessão (`SessionStart`)**: diagnóstico de saúde, higiene de armazenamento e estado vivo.
- **Na finalização de tarefas (`Stop`)**: verificação de atualização do `state.md` e árvores de trabalho pendentes.
- **No Git local (`pre-commit` e `pre-push`)**: garantia inquebrável de pre-flight limpo antes de qualquer commit ou push.

## Decisão de Arquitetura

1. **Modelos DTO Pydantic v2 (`src/corporate_engineer/models.py`)**:
   - `AnticipationStep`: Contrato estruturado com `step_index`, `title`, `phase`, `action_summary`, `target_files`, `tdd_scenario`.
   - `AnticipationPlan`: Contrato com `raw_prompt`, `target_domain`, `risk_level`, `recommended_agents`, `step_immediate_1`, `step_subsequent_2`, `blast_radius_estimate`, `structured_metaprompt`, `timestamp`.

2. **Motor de Antecipação Proativa (`src/corporate_engineer/orchestrator/anticipator.py`)**:
   - Classe `ProactiveAnticipator`:
     - Integração com `ContextAwarePromptRefiner` e `SystemOneRouter`.
     - Síntese da matriz "2 Passos à Frente" com análise de risco, domínios corporativos e AST symbols.
     - Produção de relatórios estruturados e blocos de mensagem de sistema.

3. **Suíte Completa de Lifecycle Hooks Antigravity (`.agents/orchestration/hooks/`)**:
   - `session_start.py` (SessionStart): Diagnóstico completo de saúde, armazenamento, git e estado vivo.
   - `proactive_advisor.py` (PreInvocation): Injeção do motor de antecipação 2 passos à frente e link de PR 1-clique com push remoto mandatório.
   - `pre_tool_security_guard.py` (PreToolUse em `write_file|edit_file`): Bloqueio ativo de vazamento de segredos em tempo de tool-use.
   - `post_tool_auto_healer.py` (PostToolUse em `write_file|edit_file`): Auto-cura imediata de AST, formatação via Ruff e cálculo de blast radius.
   - `session_turnover_gate.py` (Stop): Alerta de governança para atualização mandatória de `state.md`.

4. **Configuração Unificada (`.agents/hooks.json`)**:
   - Registro de todos os eventos de ciclo de vida (`SessionStart`, `PreInvocation`, `PreToolUse`, `PostToolUse`, `Stop`) mapeados para os scripts correspondentes.

5. **Instalador de Git Hooks (`scripts/install_git_hooks.py`)**:
   - Geração e ativação de scripts `pre-commit` (segredos, ruff e testes cirúrgicos) e `pre-push` (`corporate-engineer audit --strict`) em `.git/hooks/`.

6. **CLI Corporativa (`src/corporate_engineer/cli.py`)**:
   - Subcomando `corporate-engineer anticipate <prompt>` com suporte a saída em text, json ou markdown.

## Consequências

- **Positivas**:
  - O sistema passa a antecipar proativamente as necessidades de engenharia antes que erros ocorram.
  - O pipeline E2E torna-se 100% automático: edição de código gera auto-cura, formatação e verificação de blast radius em tempo real.
  - Blindagem contra vazamento de segredos na origem da escrita de ferramentas.
  - Zero dependência de memória: hooks e registros garantem que o orquestrador esteja perenemente instruído.
- **Negativas / Riscos**:
  - Ligeiro overhead de milissegundos nas chamadas de ferramentas e invocações, mitigado por bypasses rápidos para comandos triviais.
