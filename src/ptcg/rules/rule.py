from abc import ABC, abstractmethod


class Rule(ABC):

    @abstractmethod
    def matches(self, obs: dict) -> bool:
        """Return True if this rule applies to the current game state."""

    @abstractmethod
    def select(self, obs: dict) -> list[int]:
        """Return the action indices to play. Only called when matches() is True."""
