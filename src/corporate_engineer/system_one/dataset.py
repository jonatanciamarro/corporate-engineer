"""
Synthetic Dataset Generator for Free System-One SLM Fine-Tuning (IMP-0014).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import ClassVar

from corporate_engineer.models import DatasetReport, TrainingSample


class SystemOneDatasetGenerator:
    """Gerador e exportador determinístico de datasets sintéticos para o Sistema 1."""

    AGENT_TEMPLATES: ClassVar[list[tuple[str, str]]] = [
        ("Desenhe os modelos de dados e ADR para nova funcionalidade de pagamento", "architect"),
        ("Elabore um Architecture Decision Record (ADR) para o novo pipeline", "architect"),
        ("Escreva um teste que falhe antes de implementar a lógica de cálculo", "tdd-guide"),
        ("Aplique a metodologia Shift-Left TDD para a função de checkout", "tdd-guide"),
        ("Revise o código para verificar imutabilidade e possíveis vazamentos", "code-reviewer"),
        ("Analise o diff do PR para apontar smells e padrões limpos", "code-reviewer"),
        ("Verifique os type hints e convenções PEP 8 no módulo de telemetria", "python-reviewer"),
        ("Ajuste as anotações de tipo estrito para Python 3.11", "python-reviewer"),
        ("Escanear repositório em busca de chaves de API e tokens expostos", "security-reviewer"),
        ("Auditar headers de autenticação Bearer Token e OWASP compliance", "security-reviewer"),
        (
            "Indexe a hierarquia de classes e a árvore de chamadas do repositório",
            "rag-pipeline-reviewer",
        ),
        ("Gere o grafo semântico e analise os imports circulares", "rag-pipeline-reviewer"),
        ("Corrija o erro de build e a falha de importação no pytest", "build-error-resolver"),
        (
            "Resolva a quebra do teste unitário decorrente da mudança de assinatura",
            "build-error-resolver",
        ),
        ("Refatore o módulo de clientes MCP preservando 100% o comportamento", "refactor-cleaner"),
        ("Elimine código duplicado sem quebrar os testes existentes", "refactor-cleaner"),
    ]

    RISK_TEMPLATES: ClassVar[list[tuple[str, str]]] = [
        ("diff --git a/docs/README.md b/docs/README.md\n+Atualiza instruções", "False"),
        ("diff --git a/docs/adr/ADR-001.md\n+Nova documentação de arquitetura", "False"),
        (
            "diff --git a/src/corporate_engineer/mcp/client.py\n-token_secret = env\n+token = hardcoded_123",
            "True",
        ),
        (
            "diff --git a/src/corporate_engineer/models.py\n-class ChoiceDecision\n+class RemovedContract",
            "True",
        ),
        ("diff --git a/tests/test_demo.py\n+def test_pass(): assert True", "False"),
        (
            "diff --git a/src/core.py\n-def authenticate_user():\n+def authenticate_user(): return True",
            "True",
        ),
        ("diff --git a/.agents/rules/state-tracking.md\n+Texto descritivo", "False"),
        ("diff --git a/pyproject.toml\n-[dependencies]\n+drop_all_security = true", "True"),
        ("diff --git a/tests/conftest.py\n+@pytest.fixture\ndef sample(): return 1", "False"),
        (
            "diff --git a/src/corporate_engineer/cli.py\n-def parse_args\n+def rm_rf_everything",
            "True",
        ),
    ]

    COMMIT_TEMPLATES: ClassVar[list[tuple[str, str]]] = [
        ("Adiciona suporte a telemetria e rastreamento de spans OpenTelemetry", "feat"),
        ("Implementa novo subcomando decide na CLI corporativa", "feat"),
        ("Corrige bug de concorrência e deadlock no cliente MCP SSE", "fix"),
        ("Resolve falha de importação no Python 3.10 para datetime.UTC", "fix"),
        ("Refatora o motor de DAG desacoplando transições de estado", "refactor"),
        ("Simplifica as funções auxiliares de git sem alterar comportamento", "refactor"),
        ("Adiciona suíte de testes unitários para o módulo de mutação AST", "test"),
        ("Cria testes de propriedade com Hypothesis para contratos Pydantic", "test"),
        ("Atualiza documentação no README.md e formaliza o ADR-009", "docs"),
        ("Adiciona guia de instalação e boas práticas no manual de operação", "docs"),
        ("Atualiza dependências no pyproject.toml e remove pacotes obsoletos", "chore"),
        ("Configura regras do ruff e alinha linter de estilo", "chore"),
    ]

    SKIP_TEMPLATES: ClassVar[list[tuple[str, str, str]]] = [
        ("security_scan", "Modificações apenas em arquivos README.md e docs/adr/", "True"),
        (
            "security_scan",
            "Alteração em src/corporate_engineer/mcp/client.py alterando Bearer Token auth",
            "False",
        ),
        ("rag_reindex", "Edição exclusiva em arquivo .gitignore e .env.example", "True"),
        ("rag_reindex", "Criação de novos arquivos em src/corporate_engineer/system_one/", "False"),
        ("test_execution", "Atualização cosmética de comentários em docs/", "True"),
        (
            "test_execution",
            "Modificação funcional em src/corporate_engineer/orchestrator/graph.py",
            "False",
        ),
        ("lint_audit", "Arquivo de documentação estática .md criado", "True"),
        ("lint_audit", "Código Python adicionado com 200 novas linhas", "False"),
    ]

    def generate_agent_samples(self, count: int = 16) -> list[TrainingSample]:
        """Gera amostras de treino para roteamento de subagentes especialistas."""
        samples: list[TrainingSample] = []
        templates = self.AGENT_TEMPLATES
        for i in range(count):
            prompt, agent = templates[i % len(templates)]
            samples.append(
                TrainingSample(
                    instruction="Selecione o subagente especialista mais indicado para atender a esta solicitação.",
                    input=prompt,
                    output=agent,
                    task_type="classification",
                    metadata={"target": "agent_routing", "sample_index": i},
                )
            )
        return samples

    def generate_risk_samples(self, count: int = 10) -> list[TrainingSample]:
        """Gera amostras de treino para classificação de risco de diffs."""
        samples: list[TrainingSample] = []
        templates = self.RISK_TEMPLATES
        for i in range(count):
            diff_text, is_risk = templates[i % len(templates)]
            samples.append(
                TrainingSample(
                    instruction="Avalie se a alteração de código ou diff introduz alto risco estrutural ou de segurança.",
                    input=diff_text,
                    output=is_risk,
                    task_type="noul",
                    metadata={"target": "risk_assessment", "sample_index": i},
                )
            )
        return samples

    def generate_commit_samples(self, count: int = 12) -> list[TrainingSample]:
        """Gera amostras de treino para classificação de Conventional Commits."""
        samples: list[TrainingSample] = []
        templates = self.COMMIT_TEMPLATES
        for i in range(count):
            message_or_diff, commit_type = templates[i % len(templates)]
            samples.append(
                TrainingSample(
                    instruction="Classifique o tipo de commit convencional adequado para a mudança (feat, fix, refactor, test, docs, chore).",
                    input=message_or_diff,
                    output=commit_type,
                    task_type="classification",
                    metadata={"target": "commit_classification", "sample_index": i},
                )
            )
        return samples

    def generate_skip_samples(self, count: int = 8) -> list[TrainingSample]:
        """Gera amostras de treino para descarte condicional (skipping) de nós da DAG."""
        samples: list[TrainingSample] = []
        templates = self.SKIP_TEMPLATES
        for i in range(count):
            node_name, context, should_skip = templates[i % len(templates)]
            samples.append(
                TrainingSample(
                    instruction=f"Determine se o nó de pipeline '{node_name}' pode ser ignorado no contexto fornecido.",
                    input=f"NÓ: {node_name}\nCONTEXTO: {context}",
                    output=should_skip,
                    task_type="noul",
                    metadata={"target": "dag_node_skip", "sample_index": i},
                )
            )
        return samples

    def export_dataset(
        self,
        output_path: str | Path,
        agent_samples: int = 10,
        risk_samples: int = 10,
        commit_samples: int = 10,
        skip_samples: int = 10,
    ) -> DatasetReport:
        """Gera e exporta o dataset unificado no formato JSONL com checksum SHA-256."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        all_samples: list[TrainingSample] = []
        all_samples.extend(self.generate_agent_samples(agent_samples))
        all_samples.extend(self.generate_risk_samples(risk_samples))
        all_samples.extend(self.generate_commit_samples(commit_samples))
        all_samples.extend(self.generate_skip_samples(skip_samples))

        hasher = hashlib.sha256()
        with open(path, "w", encoding="utf-8") as f:
            for s in all_samples:
                line = json.dumps(s.model_dump(), ensure_ascii=False)
                f.write(line + "\n")
                hasher.update(line.encode("utf-8"))

        task_distribution: dict[str, int] = {}
        for s in all_samples:
            target = str(s.metadata.get("target", s.task_type))
            task_distribution[target] = task_distribution.get(target, 0) + 1

        return DatasetReport(
            total_samples=len(all_samples),
            task_distribution=task_distribution,
            source="corporate-engineer-synthetic",
            export_path=str(path.resolve()),
            hash_sha256=hasher.hexdigest(),
        )
