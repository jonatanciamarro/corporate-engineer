"""
Base abstraction for System-One Decision Engines.
"""

from abc import ABC, abstractmethod
from typing import Any

from corporate_engineer.models import (
    ChoiceDecision,
    NoulDecision,
    ScoreDecision,
    SystemOneReport,
)


class SystemOneEngine(ABC):
    """Contrato abstrato para motores de decisão rápida System One."""

    @abstractmethod
    def is_available(self) -> bool:
        """Indica se o backend e suas dependências estão prontos para execução."""
        ...

    @abstractmethod
    def decide_choice(
        self,
        state: str,
        choices: list[str] | dict[str, str],
        instructions: str | None = None,
    ) -> ChoiceDecision:
        """Seleciona a melhor opção categórica entre as disponíveis."""
        ...

    @abstractmethod
    def decide_noul(
        self,
        state: str,
        hypothesis: str,
        instructions: str | None = None,
    ) -> NoulDecision:
        """Avalia uma hipótese ou condição retornando decisão booleana com probabilidade."""
        ...

    @abstractmethod
    def decide_score(
        self,
        state: str,
        rubric: list[str] | dict[str, Any],
        instructions: str | None = None,
    ) -> ScoreDecision:
        """Avalia o estado contra uma rubrica de níveis ordenados."""
        ...

    @abstractmethod
    def evaluate(
        self,
        state: str,
        questions: dict[str, Any],
    ) -> SystemOneReport:
        """Avalia um conjunto composto de questões tipadas em um único lote."""
        ...
