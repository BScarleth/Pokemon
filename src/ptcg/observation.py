"""
Stateless helper functions for reading fields out of a cabt observation dict.

Observation shape (from the cabt engine):
  {
    "logs":    [...],          # event history
    "current": State | None,   # None during deck-selection phase
    "select":  Select | None,  # None during deck-selection phase
  }

State shape:
  {
    "players": [PlayerState, PlayerState],
    "stadium": ...,
    ...
  }

PlayerState shape:
  {
    "active":            list,   # 0-1 items; item may be None (face-down)
    "bench":             list,   # up to 5
    "hand":              list,   # visible only to owner
    "handCount":         int,
    "prize":             list,   # face-down cards are None
    "deckCount":         int,
    "discard":           list,
    "benchMax":          int,
    "poisoned":          bool,
    "burned":            bool,
    "asleep":            bool,
    "paralyzed":         bool,
    "confused":          bool,
  }

Select shape:
  {
    "option":   list,   # available choices
    "maxCount": int,    # how many indices the agent must return
  }
"""


# --------------------------------------------------------------------------- #
# Select / action helpers
# --------------------------------------------------------------------------- #

def get_options(obs: dict) -> list:
    return obs["select"]["option"]


def get_max_count(obs: dict) -> int:
    return obs["select"]["maxCount"]


def has_select(obs: dict) -> bool:
    return obs.get("select") is not None


# --------------------------------------------------------------------------- #
# Top-level observation fields
# --------------------------------------------------------------------------- #

def get_logs(obs: dict) -> list:
    return obs.get("logs", [])


def get_current_state(obs: dict) -> dict | None:
    return obs.get("current")


# --------------------------------------------------------------------------- #
# Players
# --------------------------------------------------------------------------- #

def get_players(obs: dict) -> list:
    current = get_current_state(obs)
    if current is None:
        return []
    return current.get("players", [])


def get_player_state(obs: dict, player_index: int) -> dict | None:
    players = get_players(obs)
    if player_index >= len(players):
        return None
    return players[player_index]


# --------------------------------------------------------------------------- #
# Perspective helpers
#
# The "players" array is absolute (player 0 / player 1). "yourIndex" tells us
# which of the two the acting agent is, so "me" is players[yourIndex] — NOT
# always players[0]. Always resolve me/opponent through these helpers.
# --------------------------------------------------------------------------- #

def get_your_index(obs: dict) -> int:
    current = get_current_state(obs)
    if current is None:
        return 0
    return current.get("yourIndex", 0)


def get_opponent_index(obs: dict) -> int:
    return 1 - get_your_index(obs)


def my_active(obs: dict) -> dict | None:
    return get_active_pokemon(obs, get_your_index(obs))


def opponent_active(obs: dict) -> dict | None:
    return get_active_pokemon(obs, get_opponent_index(obs))


def my_bench(obs: dict) -> list:
    return get_bench(obs, get_your_index(obs))


def opponent_bench(obs: dict) -> list:
    return get_bench(obs, get_opponent_index(obs))


def my_player_state(obs: dict) -> dict | None:
    return get_player_state(obs, get_your_index(obs))


def my_hand_cards(obs: dict) -> list:
    return get_hand(obs, get_your_index(obs))


def my_prize_cards(obs: dict) -> list:
    return get_prize_cards(obs, get_your_index(obs))


def opponent_prize_cards(obs: dict) -> list:
    return get_prize_cards(obs, get_opponent_index(obs))


def my_status_conditions(obs: dict) -> dict:
    return get_status_conditions(obs, get_your_index(obs))


# --------------------------------------------------------------------------- #
# Per-player board state
# --------------------------------------------------------------------------- #

def get_active_pokemon(obs: dict, player_index: int) -> dict | None:
    player = get_player_state(obs, player_index)
    if player is None:
        return None
    active = player.get("active", [])
    return active[0] if active else None


def get_bench(obs: dict, player_index: int) -> list:
    player = get_player_state(obs, player_index)
    if player is None:
        return []
    return player.get("bench", [])

def get_hand(obs: dict, player_index: int) -> list:
    player = get_player_state(obs, player_index)
    if player is None:
        return []
    return player.get("hand", [])


def get_hand_count(obs: dict, player_index: int) -> int:
    player = get_player_state(obs, player_index)
    if player is None:
        return 0
    return player.get("handCount", 0)


def get_prize_cards(obs: dict, player_index: int) -> list:
    player = get_player_state(obs, player_index)
    if player is None:
        return []
    return player.get("prize", [])


def get_deck_count(obs: dict, player_index: int) -> int:
    player = get_player_state(obs, player_index)
    if player is None:
        return 0
    return player.get("deckCount", 0)


def get_discard(obs: dict, player_index: int) -> list:
    player = get_player_state(obs, player_index)
    if player is None:
        return []
    return player.get("discard", [])


def get_status_conditions(obs: dict, player_index: int) -> dict:
    player = get_player_state(obs, player_index)
    if player is None:
        return {}
    return {
        "poisoned":  player.get("poisoned", False),
        "burned":    player.get("burned", False),
        "asleep":    player.get("asleep", False),
        "paralyzed": player.get("paralyzed", False),
        "confused":  player.get("confused", False),
    }
