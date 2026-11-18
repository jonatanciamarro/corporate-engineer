---
name: plan_v2
description: >-
  Enterprise Architecture & Engineering Planning Protocol (v2). Features Trade-off Matrix,
  Rollback & Blast Radius analysis, Threat Modeling (STRIDE), and Formal DTO Contract definition.
---

# Enterprise Engineering Planning Protocol (`plan_v2`)

`plan_v2` é o padrão corporativo avançado para planejamento técnico de alto nível, expandindo o comando `/plan` tradicional com rigor arquitetural, análise de impacto e governança de segurança.

---

## 🎯 When to Activate
- Ativado via `/plan_v2` ou durante a **Fase 1 (Alinhamento, Contratos & Escopo)** do `corp-pipeline`.
- Obrigatório para qualquer mudança que envolva:
  - Criação ou alteração de modelos de dados, endpoints ou integrações.
  - Refatorações estruturais ou mudanças de dependências centrais.
  - Mudanças de infraestrutura ou fluxos de autenticação/autorização.

---

## 📋 Estrutura Obrigatória do Artefato de Plano (`plan_name.md`)

Todo plano gerado com `plan_v2` deve ser gravado como um artefato no diretório de artefatos com `RequestFeedback: true` e `UserFacing: true`, contendo as seguintes seções padronizadas:

### 1. Declaração do Problema & Drivers de Negócio
- Descrição sucinta da necessidade e ticket associado (JIRA/Linear).
- Métricas de sucesso (KPIs técnicos e de negócio).

### 2. Matriz de Trade-offs de Arquitetura (Mínimo 2 Opções)
Tabela comparativa explícita ponderando alternativas técnicas:

| Critério | Opção A (Recomendada) | Opção B (Alternativa) |
| :--- | :--- | :--- |
| **Arquitetura** | Ex: Event-driven com RabbitMQ/Kafka | Ex: Polling síncrono REST |
| **Latência Estimada** | Ex: Baixa (<50ms p99) | Ex: Média-alta (>300ms p99) |
| **Custo de Infra/Tokens** | Ex: Fixo por instância | Ex: Variável por chamada |
| **Complexidade Cognitiva** | Ex: Média (gerenciamento de filas) | Ex: Baixa (endpoints CRUD) |
| **Tolerância a Falhas** | Ex: Alta (dead-letter queue) | Ex: Baixa (requer retry manual) |

### 3. Contratos Formais & DTOs (Shift-Left)
Especificação formal das interfaces e estruturas de dados antes de qualquer código de produção:
- DTOs de Entrada e Saída (Pydantic / TypeScript / Go structs / Dataclasses).
- Mapeamento explícito de códigos de status de erro e payloads de exceção.

### 4. Modelagem de Ameaças & Segurança (STRIDE / OWASP)
Análise preventiva de vetores de ataque:
- **Spoofing**: Como a identidade e autenticação são asseguradas?
- **Tampering**: Como a integridade dos dados e payloads é garantida?
- **Repudiation**: Logs de auditoria são gerados para ações críticas?
- **Information Disclosure**: Dados sensíveis ou PII são mascarados/criptografados?
- **Denial of Service**: Existem limites de taxa (rate limits) e timeouts definidos?
- **Elevation of Privilege**: O princípio do menor privilégio (least privilege) é seguido?

### 5. Estratégia de Rollback & Blast Radius
- **Blast Radius**: Quais outros serviços ou consumidores podem ser impactados por falha?
- **Plano de Rollback Cirúrgico**: Passo a passo exato para reverter a alteração em produção sem indisponibilidade ou corrupção de estado.

### 6. Roteiro Cirúrgico de Execução
Lista sequencial e atômica de arquivos a criar, modificar ou excluir, organizada por camada de dependência.

---

## 🔴 Integração com Gate 1
Após a emissão do artefato `plan_v2`, o agente **obrigatoriamente deve interromper a execução e solicitar aprovação explícita do usuário** antes de iniciar a escrita de qualquer teste ou código.
