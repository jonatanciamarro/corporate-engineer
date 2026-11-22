# ADR-020: Gemini LoRA Modular Pipeline — Motion Graphics & Tool-Calling Dataset, Vertex SFT Formatter & AST Validator

- **Status**: Aceito
- **Data**: 2026-11-22
- **Autor**: Corp-Pipeline Master Orchestrator & Arquiteto de Sistemas
- **Ticket / Item**: IMP-0020 / DarkFactory LoRA Specialization Engine
- **Decisores**: Equipe de Arquitetura e Engenheiro Corporativo

---

## 1. Contexto e Drivers de Decisão

O projeto **DarkFactory** necessita de automação de ponta para a produção de motion graphics de altíssimo nível estético (visando qualidade comparável a modelos de fronteira como Opus, Fable ou Astra), combinada com orquestração determinística de ferramentas (Tool Calling e Function Calling sobre MCP e APIs de renderização).

O modelo fundacional adotado é o **Gemini 3.8 Flash**, reconhecido por sua altíssima velocidade e baixo custo de inferência, mas que em sua forma *zero-shot* genérica pode apresentar inconsistências em sintaxes avançadas de bibliotecas de motion (Remotion, Manim, Blender Python), tempos de interpolação inadequados e desvios esporádicos em schemas JSON complexos.

Ao invés de tentar treinar um modelo monolítico difuso, a estratégia acordada é a **Modularidade por Adapters (PEFT / LoRA)**:
1. **LoRA 1 (Motion Graphics Architect)**: Especialista em código de animação procedural, curvas de física de mola (*spring mechanics*), interpolações cinematográficas e estética DarkFactory em Remotion (React/TypeScript), Manim (Python) e Blender (`bpy`).
2. **LoRA 2 (Deterministic Tool Calling & MCP Orchestrator)**: Especialista em chamadas de ferramentas rigorosas, sem alucinação de schemas JSON e encadeamento multi-turn.

Para viabilizar o treinamento eficiente no ecossistema Google (Vertex AI / Google AI Studio), o framework `corporate-engineer` precisa de uma camada nativa de engenharia de dados: geração sintética de amostras especializadas, validação de sintaxe por AST/regex, sanitização estrita de credenciais/PII, particionamento determinístico (train/val 80/20) e exportação no formato canônico JSONL da Vertex AI.

---

## 2. Opções Consideradas

### Opção 1: Scripts Avulsos Externos (Stand-alone ad-hoc)
- **Descrição**: Criação de scripts soltos em Python fora do framework para montar datasets manualmente.
- **Prós**: Rápido de rascunhar.
- **Contras**: Sem tipagem estrita Pydantic v2, sem validação automatizada de sintaxe, sem cobertura de testes, risco severo de vazamento de credenciais nos datasets e ausência de integração com a CLI corporativa.

### Opção 2: Módulo Completo Integrado no Framework (`corporate_engineer.lora` + CLI `lora`) (ESCOLHIDA)
- **Descrição**: Pacote formal com modelos Pydantic v2, gerador de templates estéticos para Remotion/Manim/Blender e Tool-Calling, validador de sintaxe/AST, scanner de segredos embutido, particionador determinístico e CLI integrada `corporate-engineer lora [generate|validate|export]`.
- **Prós**: 
  - Alinhado aos padrões corporativos de qualidade e Shift-Left TDD.
  - Validação estrita por AST garantindo 0% de código quebrado no dataset de treino.
  - Sanitização nativa contra vazamento de chaves ou PII antes da exportação.
  - Exportação oficial no padrão Vertex AI SFT (`{"contents": [{"role": "user", ...}, {"role": "model", ...}]}`).
  - Estimativa antecipada de tokens e custos de treinamento.
- **Contras**: Exige formalização de contratos DTOs e testes unitários rigorosos (compensado pela confiabilidade do pipeline).

---

## 3. Decisão Arquitetural

Adotar a **Opção 2**. O framework implementará o módulo `src/corporate_engineer/lora/` e expandirá `src/corporate_engineer/models.py` com contratos Pydantic v2 estritos, oferecendo:
1. **Modelos DTO**:
   - `LoraTrainingSample`: Representação estruturada de uma amostra de treino com domínio (`MOTION_REMOTION`, `MOTION_MANIM`, `MOTION_BLENDER`, `TOOL_CALLING`), instrução de sistema, prompt de entrada, código/resposta esperada e metadados.
   - `LoraDatasetConfig`: Parâmetros de geração, proporção de split (default 80/20), seed aleatória determinística e filtros de sanitização.
   - `LoraValidationReport`: Diagnóstico detalhado de amostras aprovadas, rejeitadas e erros de sintaxe identificados.
   - `LoraExportResult`: Relatório de exportação com caminhos dos arquivos JSONL gerados (`train.jsonl`, `validation.jsonl`), contagem total de amostras e estimativa de tokens.
2. **Componentes do Motor**:
   - `LoraDatasetGenerator`: Gerador de amostras de código de motion de elite (DarkFactory aesthetic) e traces de tool calling corporativo.
   - `LoraSyntaxValidator`: Validador de AST em Python (`ast.parse`) para Manim e Blender, validador de estrutura para TypeScript/Remotion e validador de schema JSON para tool-calling.
   - `LoraVertexExporter`: Sanitizador de segredos (regex + scanner) e formatador JSONL no padrão da Google Cloud Vertex AI / AI Studio SFT.
3. **CLI Corporativa**:
   - Subcomando oficial `corporate-engineer lora generate`
   - Subcomando oficial `corporate-engineer lora validate`
   - Subcomando oficial `corporate-engineer lora export`

---

## 4. Consequências e Trade-offs

- **Positivas**:
  - Geração padronizada e reprodutível de datasets de fine-tuning para Gemini Flash.
  - Elevação comprovável da qualidade do código de motion (Remotion/Manim/Blender) e de tool calling.
  - Prevenção ativa de contaminação por dados inválidos ou segredos expostos.
- **Negativas / Mitigações**:
  - Geração sintética de templates exige curadoria constante de exemplos. *Mitigação*: Arquitetura baseada em templates extensíveis e injeção de novas receitas sem alterar o core do validador.

---

## 5. Próximos Passos (Ciclo Corp-Pipeline)

1. Publicar Plano Técnico (`/plan_v2`) com modelagem STRIDE, matriz de trade-offs e DTOs tipados.
2. Aguardar aprovação do **Gate 1**.
3. Implementar suíte Shift-Left TDD em `tests/test_gemini_lora_pipeline.py` (Certificação RED).
4. Implementar código de produção em `src/corporate_engineer/models.py`, `src/corporate_engineer/lora/` e `src/corporate_engineer/cli.py` (GREEN).
5. Executar Pre-Flight Quality Gate (pytest, ruff, mypy, secret scanner) e sincronização com `state.md`.
