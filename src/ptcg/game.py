"""
Thin wrappers around the kaggle_environments / cabt engine.

kaggle_environments is the runtime used for both local testing and competition
submission.  The cabt environment is registered inside that package.
"""

from kaggle_environments import make


def create_environment(deck0: list[int], deck1: list[int]):
    """Create a cabt environment configured with the two decks."""
    return make("cabt", configuration={"decks": [deck0, deck1]})


def run_battle(env, agent0, agent1) -> list:
    """Run a full battle and return the step history."""
    env.run([agent0, agent1])
    return env.steps


def render_board(env) -> str:
    """Return a human-readable string of the current board state."""
    return env.render(mode="ansi")


def get_rewards(env) -> list[float]:
    """Return the final rewards for [agent0, agent1]."""
    last_step = env.steps[-1]
    return [player["reward"] for player in last_step]
