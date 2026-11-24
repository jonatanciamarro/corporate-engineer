# ADR-029: Invariante Arquitetural de Auto-Conexão e Verificação Contínua de Potência Máxima (IMP-0029)

## Status
Aceito (Accepted)

## Data
2026-11-24

## Contexto & Motivação
O framework `corporate-engineer` atingiu mais de 287 testes unitários e de integração, 28 melhorias registradas e uma arquitetura multicamada avançada (Core Orchestrator, Intelligence, Governance, RAG com AST Cache SHA-256, MCP Hub, System One, Observabilidade OTel, Runner Autônomo e CLI modular).

No entanto, em ambientes ágeis de engenharia de software autônoma com agentes de IA, existe um risco recorrente de **"dívida de desconexão" (disconnected module debt)**:
1. Módulos ou capacidades podem ser implementados e testados isoladamente em subpastas de `src/`, mas nunca exportados na API pública (`__all__`), deixando-os invisíveis para outros subsistemas.
2. Comandos CLI ou submódulos podem ser criados sem serem integrados ao despachante do `parser.py`.
3. Domínios de negócio novos podem não ser registrados no `ContextAwarePromptRefiner`, impedindo que novos prompts humanos se beneficiem da capacidade construída.
4. O pipeline autônomo (`run_pipeline`) pode evoluir sem acionar as novas ferramentas de auditoria e qualidade.

O usuário determinou formalmente a seguinte filosofia mandatória:
> *"Precisamos garantir que toda nova implementação já esteja conectada e funcionando automaticamente em potência máxima 100%."*

## Decisão de Arquitetura

Decidiu-se estabelecer uma **Invariante de Auto-Conexão e Potência Máxima Mandatória** e criar um motor estático de auditoria contínua de integridade do ecossistema:

### 1. Os 5 Elos Obrigatórios de Auto-Conexão (Cadeia de Potência Máxima)
Para qualquer módulo ou classe criada em `src/corporate_engineer/`:
- **Elo 1: Contratos Tipados Pydantic v2**: Entradas e saídas modeladas estritamente em `src/corporate_engineer/models.py`.
- **Elo 2: Exportação Pública**: Re-exportação explícita no `__all__` do subpacote ou no nível de topo `src/corporate_engineer/__init__.py`.
- **Elo 3: Exposição de Comando CLI**: Se a capacidade for acionável pelo usuário ou por agentes, deve possuir parser registrado em `src/corporate_engineer/cli/parser.py` e handler em `src/corporate_engineer/cli/commands/`.
- **Elo 4: Ancoragem de Contexto & Metaprompt**: O domínio e símbolos devem ser reconhecidos pelo `ContextAwarePromptRefiner` e indexados pelo `CachedASTCodebaseIndexer`.
- **Elo 5: Auditoria de Conexão no Quality Gate**: Validação contínua através do `CapabilityWiringAuditor` integrado ao `QualityGateRunner`.

### 2. Motor de Auditoria: `CapabilityWiringAuditor` (`src/corporate_engineer/quality/wiring_auditor.py`)
- Varre recursivamente `src/corporate_engineer/` via AST nativo do Python (`ast.parse`).
- Identifica classes e funções públicas (que não começam com `_`).
- Cruza com a base de testes em `tests/` para assegurar que não existam módulos de produção sem suíte de testes dedicada.
- Cruza com `src/corporate_engineer/__init__.py` e os `__init__.py` de subpacotes para detectar exportações órfãs ou faltantes.
- Valida o registro de comandos na CLI e no mapa de domínios do Prompt Refiner.
- Emite relatório fortemente tipado `WiringAuditReport` (Pydantic v2).

### 3. Integração no Quality Gate e na CLI
- `QualityGateRunner.run_wiring_audit()` adicionado aos pre-flight checks oficiais.
- Flag `--wiring` adicionada ao comando `corporate-engineer audit`, e inclusão automática na execução com `--strict`.
- Falha com código diferente de zero caso qualquer módulo desconectado seja detectado.

### 4. Integração no Pipeline Autônomo (`AutonomousEngineeringGraph.run_pipeline`)
- A Fase AUDIT do ciclo de vida FSM executa a auditoria de auto-conexão antes de permitir a transição para a Fase DELIVER.

## Consequências

### Positivas:
- **Zero Módulos Órfãos**: Nenhuma funcionalidade pode ser commitada no repositório em estado "desconectado" ou esquecido.
- **Potência Máxima Garantida**: Cada nova linha de código estende imediatamente a inteligência de prompt, a CLI e o pipeline FSM.
- **Conformidade Shift-Left Automatizada**: Se um desenvolvedor ou agente esquecer de exportar ou registrar uma capacidade, a suíte de testes falha imediatamente no CI e no pre-flight local.

### Trade-offs:
- Requer disciplina estrita ao criar novos módulos (exportação em `__init__.py`, cobertura em `tests/` e registro no mapa de domínios).
