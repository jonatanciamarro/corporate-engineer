# ADR-028: Tri-Phase Adversarial Loop (Red Team 1.5 → Transcendência 1.6 → Verificação 1.7) (IMP-0026)

## Status
Aceito (Accepted)

## Data
2026-11-24

## Contexto & Motivação
No desenvolvimento autônomo conduzido por agentes de inteligência artificial, o planejamento tradicional (Fase 1) elabora planos, modelos e metaprompts que fluem diretamente para implementação (Fase 4 e Swarm). Embora rápido, esse padrão sofre criticamente com a **sicoferência (*sycophancy*) dos LLMs**: planos contendo premissas frágeis de concorrência, tolerância a falhas, permissões excessivas de ferramentas MCP, timeouts de rede ou efeitos colaterais são aceitos sem contestação rigorosa.

Quando esses planos defeituosos são despachados para um enxame de agentes (`SwarmCoordinator`) ou pipelines de codificação autônoma (`AutonomousEngineeringGraph`), manifestam-se sintomas nocivos:
1. Desperdício massivo de tokens com refações e alucinações de auto-remediação.
2. Criação de mocks complacentes e testes superficiais apenas para forçar a suíte a passar (*greenwashing*).
3. Efeitos colaterais em produção por ausência de modelagem de ameaças e cenários adversos de caos.

## Decisão de Arquitetura

Decidiu-se instituir o **Loop Dialético Tri-Fásico Always-On (Fases 1.5 → 1.6 → 1.7)** no núcleo de orquestração do `corporate-engineer`, assegurando que nenhum plano de risco elevado seja executado sem estresse adversarial prévio e transcendência arquitetural formal:

### 1. As Três Fases Dialéticas

```text
[Fase 1: Plano Inicial / Metaprompt]
                │
                ▼
┌──────────────────────────────────────────────┐
│ Fase 1.5: Adversarial Red Team Attack        │ ◄── Varredura em 5 vetores de ameaça
└───────────────────────┬──────────────────────┘
                        │ RedTeamAttackReport (vulnerabilidades CRITICAL/HIGH/MEDIUM/LOW)
                        ▼
┌──────────────────────────────────────────────┐
│ Fase 1.6: Architecture Transcendence         │ ◄── Síntese dialética, invariantes
└───────────────────────┬──────────────────────┘      estruturais e imunidade sistêmica
                        │ TranscendencePlan (matriz de resolução formal)
                        ▼
┌──────────────────────────────────────────────┐
│ Fase 1.7: Adversarial Re-Verification        │ ◄── Passada 2 de estresse adversarial
└───────────────────────┬──────────────────────┘
                        │ AdversarialVerdict (VERIFIED / HARDEN_REQUIRED)
                        ▼ + Matriz Obrigatória de Chaos Tests (TDD)
[Fase 2 & Swarm: Execução Blindada]
```

#### Fase 1.5 — Adversarial Red Team Attack (Passada 1):
O motor `AdversarialRedTeam` ataca a especificação contra 5 eixos de vulnerabilidade estrutural:
- **CONCURRENCY**: Race conditions, locks não reentrantes, contenção de recursos e deadlocks.
- **FAULT_TOLERANCE**: Ausência de fallbacks, ponto único de falha (SPOF) e ausência de rollback em falha.
- **PRIVILEGE_MCP**: Escopo excessivo de ferramentas, falta de circuit breakers e vazamento potencial de credenciais.
- **NETWORK_TIMEOUTS**: Timeouts não configuráveis, processos suspensos e swallowing silencioso de exceções.
- **DATA_INTEGRITY**: Mutação acidental de estruturas, falta de validação de esquemas Pydantic e efeitos colaterais em disco.
Emite `RedTeamAttackReport`. Se `highest_severity` for `CRITICAL` ou `HIGH`, o plano é bloqueado para avanço direto (`is_blocked=True`).

#### Fase 1.6 — Architecture Transcendence & Hardening:
O motor `ArchitectureTranscender` não aplica remendos superficiais (*band-aids*); ele eleva a arquitetura para um nível superior de robustez:
- Converte pontos de falha em **invariantes estruturais formais**.
- Introduz estruturas estritamente **imutáveis** (`frozen=True` ou cópias defensivas).
- Implementa **circuit breakers**, **timeouts com backoff exponencial** e **sandboxes atômicos de reversão**.
Emite `TranscendencePlan`.

#### Fase 1.7 — Adversarial Re-Verification (Passada 2) & Matriz de Chaos Tests:
O `AdversarialRedTeam` executa a segunda passada sobre o plano transcendido:
- Verifica se as vulnerabilidades foram extintas sem adição de complexidade acidental.
- Emite `AdversarialVerdict` (`VERIFIED`, `HARDEN_REQUIRED` ou `REJECTED`, limitado a 2 iterações máximas).
- Gera automaticamente a **Matriz de Chaos Tests** (`list[ChaosTestCase]`), contendo cenários de falha e caminhos negativos que o `tdd-guide` DEVE implementar antes do código funcional.

### 2. Fast-Path Bypass Inteligente (Sistema 1)
Tarefas rotineiras de baixa complexidade ou baixo risco (`risk_level == "LOW"`, consultas `index`, `telemetry`, comandos `pytest`) contam com *Fast-Path Bypass* imediato, preservando latência sub-milisegundo sem token burn desnecessário.

### 3. Integração com o Pipeline de Engenharia & Swarm
- **`AutonomousEngineeringGraph.run_pipeline`**: Aciona automaticamente o `AdversarialLoopCoordinator` na fase `PLANNING` antes da fase `TDD`. A matriz de testes de caos gerada é injetada em `report.details["chaos_matrix"]`.
- **`SwarmCoordinator`**: O gate dialético valida o objetivo e os subagentes antes de disparar o `fanout` de workers.
- **CLI**: Adicionado subcomando oficial `corporate-engineer dialectic <prompt>` para uso interativo.

## Consequências

### Positivas
- **Imunidade Arquitetural**: Eliminação na raiz de designs ingênuos ou vulneráveis antes de gastar recursos de implementação.
- **Economia Drástica de Tokens no Swarm**: Agentes do swarm recebem planos já endurecidos e com limites claros de contenção.
- **TDD Rigoroso por Design**: O `tdd-guide` passa a receber obrigatoriamente cenários negativos e de injeção de caos além dos caminhos felizes.

### Neutras / Mitigações
- Adição de latência leve na fase de planejamento de alto risco (~0.05s a 0.2s em inferência local heurística/estrutural), amplamente compensada pela prevenção de refações.
