# ADR-018: Context-Aware Metaprompt Engine & Prompt Refiner (IMP-0018)

## Status
Aceito (Accepted)

## Data
2026-11-22

## Contexto & Motivação
Em sistemas autônomos de engenharia de software guiados por agentes de IA, a causa raiz de mais de 80% das falhas, retrabalhos, loops de TDD e alucinações de escopo é a brevidade e ambiguidade do prompt de entrada fornecido pelo usuário ("garbage in, garbage out").

O framework `corporate-engineer` opera com rigor corporativo (Shift-Left TDD, contratos estritos Pydantic v2, invariantes de segurança, orquestração de DAGs e governança contínua). No entanto, quando um comando curto ou informal é submetido diretamente ao pipeline (ex.: *"arrume a autenticação do MCP"* ou *"adicione timeout nas chamadas"*), o orquestrador e os subagentes downstream precisam despender ciclos cognitivos excessivos para inferir intenção, escopo, módulos afetados e critérios de aceite.

A proposta **IMP-0018** introduz uma camada formal de pré-processamento denominada **Fase 0.5: Context-Aware Metaprompter**, que transforma o prompt bruto do usuário em uma especificação técnica estruturada e contextualizada (*Revised Prompt / Metaprompt*) antes de acionar o pipeline downstream.

## Decisão de Arquitetura

1. **Modelos DTO Pydantic v2 (`src/corporate_engineer/models.py`)**:
   - `RevisedPromptSpec`: Contrato tipado contendo `raw_prompt`, `target_domain`, `core_intent`, `functional_requirements`, `non_functional_requirements` (invariantes corporativas), `affected_modules`, `out_of_scope` (guardrails anti-overengineering), `tdd_test_scenarios`, `metaprompt` sintetizado, `confidence_score`, flags de bypass (`is_bypassed`, `bypass_reason`) e `timestamp`.

2. **Roteamento Condicional Dual-Speed (Gating com Sistema 1)**:
   - Identificação determinística de comandos operacionais e queries triviais (ex.: `pytest`, `git status`, `/preflight`) para ativação de **Fast-Path Bypass** (latência zero, sem reescrita desnecessária).
   - Possibilidade de override explícito via flag `--bypass-gate`.

3. **Enriquecimento Contextual com RAG & AST (`ContextAwarePromptRefiner`)**:
   - Análise léxica e semântica do prompt cruzando com domínios do framework (`mcp`, `orchestrator`, `quality`, `rag`, `system_one`, `cli`);
   - Mapeamento dinâmico de módulos afetados e injeção de contratos e invariantes corporativas reais;
   - Extração e síntese de critérios de aceite e cenários específicos para a fase RED do TDD.

4. **Interface CLI Corporativa (`src/corporate_engineer/cli.py`)**:
   - Subcomando oficial `corporate-engineer prompt refine <prompt>` com suporte a flags:
     - `--bypass-gate` / `-b`: Força refinamento ignorando o gating operacional;
     - `--format [text|json|markdown]`: Formatação padronizada para integração no terminal ou CI/CD;
     - `--workspace` / `-w`: Caminho do workspace para contextualização de código;
     - `--output` / `-o`: Exportação estruturada para arquivo.

## Consequências
- **Positivas**:
  - Elimina ambiguidades logo na entrada do pipeline, fornecendo especificações prontas para o `/grill-me_v2` e `/plan_v2`;
  - Aumenta a taxa de aprovação direta no TDD cirúrgico (Fase 2 e 3);
  - Previne desvios de escopo (*scope creep*) por meio de delimitação explícita de `out_of_scope`;
  - Zero sobrecarga para comandos operacionais do dia a dia devido ao Fast-Path Bypass.
- **Mitigações**:
  - Gating determinístico para evitar chamadas lentas ou reescritas indesejadas em comandos simples;
  - Saída transparente e estruturada (Markdown / JSON) com exibição de diff de intenção para validação humana (*Human-in-the-Loop*).
