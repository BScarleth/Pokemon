"""
Generate a self-contained submission.py from an agent class.

The generated file has no imports from src/ptcg/ — safe to submit as a
single .py file to Kaggle.

To switch agents, change AGENT_CLASS and AGENT_MODULE, then re-run.

Usage:
    python scripts/build_submission.py
    kaggle competitions submit pokemon-tcg-ai-battle -f submission.py -m "..."
"""

import importlib
import inspect
import os
import sys
import textwrap

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

# ── Configure which agent to bundle ──────────────────────────────────────────
AGENT_CLASS = "RandomAgent"
AGENT_MODULE = "ptcg.agents.random_agent"

# obs_utils calls to replace with direct dict access in the generated file.
# Add entries here when your agent uses more helpers from observation.py.
OBS_UTILS_INLINE = {
    "obs_utils.get_options(obs)":               'obs["select"]["option"]',
    "obs_utils.get_max_count(obs)":             'obs["select"]["maxCount"]',
    "obs_utils.has_select(obs)":                '(obs.get("select") is not None)',
    "obs_utils.get_logs(obs)":                  'obs.get("logs", [])',
    "obs_utils.get_current_state(obs)":         'obs.get("current")',
    "obs_utils.get_players(obs)":               '(obs.get("current") or {}).get("players", [])',
    "obs_utils.get_active_pokemon(obs, 0)":     '((obs.get("current") or {}).get("players", [{}, {}])[0].get("active") or [None])[0]',
    "obs_utils.get_active_pokemon(obs, 1)":     '((obs.get("current") or {}).get("players", [{}, {}])[1].get("active") or [None])[0]',
    "obs_utils.get_bench(obs, 0)":              '((obs.get("current") or {}).get("players", [{}, {}])[0].get("bench", []))',
    "obs_utils.get_bench(obs, 1)":              '((obs.get("current") or {}).get("players", [{}, {}])[1].get("bench", []))',
    "obs_utils.get_hand(obs, 0)":               '((obs.get("current") or {}).get("players", [{}, {}])[0].get("hand", []))',
    "obs_utils.get_hand_count(obs, 0)":         '((obs.get("current") or {}).get("players", [{}, {}])[0].get("handCount", 0))',
    "obs_utils.get_prize_cards(obs, 0)":        '((obs.get("current") or {}).get("players", [{}, {}])[0].get("prize", []))',
    "obs_utils.get_deck_count(obs, 0)":         '((obs.get("current") or {}).get("players", [{}, {}])[0].get("deckCount", 0))',
    "obs_utils.get_discard(obs, 0)":            '((obs.get("current") or {}).get("players", [{}, {}])[0].get("discard", []))',
}
# ─────────────────────────────────────────────────────────────────────────────


def load_agent_class():
    mod = importlib.import_module(AGENT_MODULE)
    return getattr(mod, AGENT_CLASS)


def get_deck(cls) -> list[int]:
    return cls().get_deck()


def get_select_action_body(cls) -> str:
    source = inspect.getsource(cls.select_action)
    lines = source.splitlines()
    body = textwrap.dedent("\n".join(lines[1:]))  # strip the def line
    for call, inline in OBS_UTILS_INLINE.items():
        body = body.replace(call, inline)
    if "obs_utils." in body:
        remaining = [l for l in body.splitlines() if "obs_utils." in l]
        raise ValueError(
            f"Uninlined obs_utils calls remain in {AGENT_CLASS}.select_action:\n"
            + "\n".join(remaining)
            + "\nAdd them to OBS_UTILS_INLINE in build_submission.py."
        )
    return body.strip()


def format_deck(deck: list[int]) -> str:
    rows = [deck[i:i + 10] for i in range(0, len(deck), 10)]
    inner = "\n".join("    " + ", ".join(str(c) for c in row) + "," for row in rows)
    return f"DECK: list[int] = [\n{inner}\n]  # {len(deck)} cards"


def generate(agent_class: str, deck: list[int], body: str) -> str:
    deck_str = format_deck(deck)
    indented_body = textwrap.indent(body, "    ")
    return (
        f'"""\n'
        f"Auto-generated from {agent_class} by scripts/build_submission.py.\n"
        f"Do not edit manually — run the script to regenerate.\n"
        f'"""\n'
        f"import random\n\n"
        f"{deck_str}\n\n\n"
        f"def agent(obs: dict, *args) -> list[int]:\n"
        f"    if obs.get(\"select\") is None:\n"
        f"        return DECK\n"
        f"{indented_body}\n"
    )


def write(content: str) -> None:
    path = os.path.join(ROOT, "submission.py")
    with open(path, "w") as f:
        f.write(content)


def main() -> None:
    cls = load_agent_class()
    deck = get_deck(cls)
    body = get_select_action_body(cls)
    content = generate(AGENT_CLASS, deck, body)
    write(content)
    print(f"Generated submission.py from {AGENT_CLASS} ({len(deck)} cards)")
    print("Submit: kaggle competitions submit pokemon-tcg-ai-battle -f submission.py -m \"...\"")


if __name__ == "__main__":
    main()
