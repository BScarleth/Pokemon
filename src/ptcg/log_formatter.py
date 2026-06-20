"""
Human-readable formatting for game logs and agent actions.

Converts raw cabt log dicts and option dicts — which use integer IDs for
everything — into plain English using card_db for names and the schema
enums for type labels.

Falls back gracefully when card_db is not loaded: shows "Card#ID" /
"Attack#ID" instead of real names so output is still parseable.
"""

from ptcg import card_db
from ptcg.rules.schema import AreaType, LogType, OptionType


# ── Name lookups ──────────────────────────────────────────────────────────────

def _card_name(card_id: int | None) -> str:
    if card_id is None:
        return "unknown"
    card = card_db.get_card(card_id)
    return card.get("name") or f"Card#{card_id}"


def _attack_name(attack_id: int | None) -> str:
    if attack_id is None:
        return "unknown"
    atk = card_db.get_attack(attack_id)
    return atk.get("name") or f"Attack#{attack_id}"


def _area_name(area: int | None) -> str:
    if area is None:
        return "unknown"
    try:
        return AreaType(area).name.lower()
    except ValueError:
        return f"area#{area}"


def _agent(player_index: int | None) -> str:
    return f"Agent {player_index}" if player_index is not None else "unknown"


# ── Single log entry formatter ────────────────────────────────────────────────

def format_log(log: dict) -> str | None:
    """
    Return a human-readable string for one log entry, or None for entries
    that are too noisy to display (shuffle, draw, etc.).
    """
    t   = log.get("type")
    who = _agent(log.get("playerIndex"))

    if t == LogType.TURN_START:
        return f"\n{'─' * 50}\nTurn {log.get('value', '?')}"

    if t == LogType.TURN_END:
        return f"{who}: ends turn"

    if t == LogType.ATTACK:
        attacker = _card_name(log.get("cardIdActive"))
        move     = _attack_name(log.get("attackId"))
        target   = _card_name(log.get("cardIdTarget"))
        return f"{who}: {attacker} uses {move} → {target}"

    if t == LogType.HP_CHANGE:
        pokemon = _card_name(log.get("cardId"))
        value   = log.get("value", 0)
        sign    = "+" if value > 0 else ""
        label   = "heals" if (log.get("isRecover") or value > 0) else "takes"
        amount  = abs(value)
        return f"  {pokemon} {label} {amount} damage  (HP {sign}{value})"

    if t == LogType.PLAY:
        card = _card_name(log.get("cardId"))
        return f"{who}: plays {card}"

    if t == LogType.ATTACH:
        card   = _card_name(log.get("cardId"))
        target = _card_name(log.get("cardIdTarget"))
        return f"{who}: attaches {card} to {target}"

    if t == LogType.EVOLVE:
        before = _card_name(log.get("cardIdBefore"))
        after  = _card_name(log.get("cardIdAfter"))
        return f"{who}: {before} evolves → {after}"

    if t == LogType.DEVOLVE:
        before = _card_name(log.get("cardIdBefore"))
        after  = _card_name(log.get("cardIdAfter"))
        return f"{who}: {before} devolves → {after}"

    if t == LogType.SWITCH:
        active = _card_name(log.get("cardIdActive"))
        bench  = _card_name(log.get("cardIdBench"))
        return f"{who}: switches {active} ↔ {bench}"

    if t == LogType.MOVE_CARD:
        card      = _card_name(log.get("cardId"))
        from_area = _area_name(log.get("fromArea"))
        to_area   = _area_name(log.get("toArea"))
        return f"{who}: moves {card}  {from_area} → {to_area}"

    if t == LogType.MOVE_ATTACHED:
        card   = _card_name(log.get("cardId"))
        target = _card_name(log.get("cardIdTarget"))
        return f"{who}: moves attached {card} to {target}"

    if t == LogType.POISONED:
        return f"  {_card_name(log.get('cardId'))} is now poisoned"

    if t == LogType.BURNED:
        return f"  {_card_name(log.get('cardId'))} is now burned"

    if t == LogType.ASLEEP:
        return f"  {_card_name(log.get('cardId'))} fell asleep"

    if t == LogType.PARALYZED:
        return f"  {_card_name(log.get('cardId'))} is paralyzed"

    if t == LogType.CONFUSED:
        return f"  {_card_name(log.get('cardId'))} is confused"

    if t == LogType.COIN:
        flip = "heads" if log.get("head") else "tails"
        return f"  coin flip → {flip}"

    if t == LogType.RESULT:
        r = log.get("result")
        if r == 0:
            return "\n🏆  Agent 0 wins!"
        if r == 1:
            return "\n🏆  Agent 1 wins!"
        return "\n  Draw"

    # Suppress noisy bookkeeping events
    if t in (LogType.SHUFFLE, LogType.DRAW, LogType.DRAW_REVERSE,
             LogType.HAS_BASIC_POKEMON, LogType.CHANGE):
        return None

    # Fallback for unknown / future log types
    return f"  [event: {LogType(t).name if t in LogType._value2member_map_ else t}]"


# ── Full history formatter ────────────────────────────────────────────────────

def format_history(history: list) -> str:
    """
    Format the full visualize history returned by cabt into a readable
    game replay. Each entry in history has 'obs' (observation) and
    optionally 'action' (selected option indices for each player).

    Returns a single multi-line string ready for print().
    """
    lines: list[str] = []

    for entry in history:
        obs  = entry.get("obs") or {}
        logs = obs.get("logs") or []

        for log in logs:
            text = format_log(log)
            if text is not None:
                lines.append(text)

    return "\n".join(lines)
