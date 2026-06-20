from abc import ABC, abstractmethod


class BaseAgent(ABC):

    @abstractmethod
    def get_deck(self) -> list[int]:
        """Return the 60-card deck list this agent plays."""

    @abstractmethod
    def select_action(self, obs: dict) -> list[int]:
        """Return action indices given the current observation."""

    @abstractmethod
    def on_game_start(self) -> None:
        """Called once before a battle begins."""

    @abstractmethod
    def on_game_end(self, result: dict) -> None:
        """Called once after a battle ends."""

    def __call__(self, obs: dict, *args) -> list[int]:
        # First call per game has select=None: agent must return its deck.
        # All subsequent calls have select set: agent picks action indices.
        if obs.get("select") is None:
            return self.get_deck()
        return self.select_action(obs)
