"""
Human-readable game replay formatter.

Converts raw cabt log dicts into plain English commentary using card_db
for names. Suppresses bookkeeping noise (shuffles, draws, turn ends) and
surfaces the meaningful events with clear visual structure.

Falls back gracefully when card_db is not loaded: shows "Card#ID" /
"Attack#ID" placeholders instead of real names.
"""

from ptcg import card_db
from ptcg.rules.schema import AreaType, LogType


# ── Name helpers ──────────────────────────────────────────────────────────────

def _card_name(card_id: int | None) -> str:
    if card_id is None:
        return "?"
    card = card_db.get_card(card_id)
    return card.get("name") or f"Card#{card_id}"


def _attack_name(attack_id: int | None) -> str:
    if attack_id is None:
        return "?"
    atk = card_db.get_attack(attack_id)
    return atk.get("name") or f"Attack#{attack_id}"


# ── Single log entry ──────────────────────────────────────────────────────────

# Events suppressed entirely — too noisy, no strategic content.
_SUPPRESSED = {
    LogType.SHUFFLE,
    LogType.DRAW,
    LogType.DRAW_REVERSE,
    LogType.HAS_BASIC_POKEMON,
    LogType.CHANGE,
    LogType.TURN_END,
}


def format_log(log: dict, player_name) -> str | None:
    """
    Return a formatted string for one log entry, or None to suppress it.
    player_name(index) must return the display name for a given player index.
    """
    t   = log.get("type")
    idx = log.get("playerIndex")
    who = player_name(idx)

    if t in _SUPPRESSED:
        return None

    # ── Turn boundary ─────────────────────────────────────────────────────────
    if t == LogType.TURN_START:
        turn = log.get("value", "?")
        return f"\n{'━' * 52}\n  Turn {turn}  ·  {who}\n{'━' * 52}"

    # ── Actions ───────────────────────────────────────────────────────────────
    if t == LogType.ATTACK:
        attacker = _card_name(log.get("cardIdActive"))
        move     = _attack_name(log.get("attackId"))
        target   = _card_name(log.get("cardIdTarget"))
        return f"  ▶  {who}'s {attacker} uses {move} on {target}"

    if t == LogType.PLAY:
        card = _card_name(log.get("cardId"))
        return f"  ▶  {who} plays {card}"

    if t == LogType.ATTACH:
        card   = _card_name(log.get("cardId"))
        target = _card_name(log.get("cardIdTarget"))
        return f"  ▶  {who} attaches {card} to {target}"

    if t == LogType.EVOLVE:
        before = _card_name(log.get("cardIdBefore"))
        after  = _card_name(log.get("cardIdAfter"))
        return f"  ▶  {who}'s {before} evolves into {after}"

    if t == LogType.DEVOLVE:
        before = _card_name(log.get("cardIdBefore"))
        after  = _card_name(log.get("cardIdAfter"))
        return f"  ▶  {who}'s {before} devolves to {after}"

    if t == LogType.SWITCH:
        active = _card_name(log.get("cardIdActive"))
        bench  = _card_name(log.get("cardIdBench"))
        return f"  ▶  {who} retreats {active} — {bench} comes in"

    if t == LogType.MOVE_ATTACHED:
        card   = _card_name(log.get("cardId"))
        target = _card_name(log.get("cardIdTarget"))
        return f"  ▶  {who} moves attached {card} to {target}"

    # ── Card movements (selective — only meaningful ones) ─────────────────────
    if t == LogType.MOVE_CARD:
        from_a = log.get("fromArea")
        to_a   = log.get("toArea")
        card   = _card_name(log.get("cardId"))

        if from_a in (AreaType.ACTIVE, AreaType.BENCH) and to_a == AreaType.DISCARD:
            return f"  💥  {card} is knocked out!"

        if from_a == AreaType.PRIZE and to_a == AreaType.HAND:
            return f"  🏅  {who} takes a prize card"

        return None   # suppress all other card movements

    # ── Damage and healing ────────────────────────────────────────────────────
    if t == LogType.HP_CHANGE:
        card   = _card_name(log.get("cardId"))
        value  = log.get("value", 0)
        amount = abs(value)
        if log.get("isRecover") or value > 0:
            return f"       ❤️  {card} heals {amount} HP"
        return f"       💔 {card} takes {amount} damage"

    # ── Status conditions ─────────────────────────────────────────────────────
    if t == LogType.POISONED:
        return f"       🟣 {_card_name(log.get('cardId'))} is poisoned"
    if t == LogType.BURNED:
        return f"       🔥 {_card_name(log.get('cardId'))} is burned"
    if t == LogType.ASLEEP:
        return f"       💤 {_card_name(log.get('cardId'))} fell asleep"
    if t == LogType.PARALYZED:
        return f"       ⚡ {_card_name(log.get('cardId'))} is paralyzed"
    if t == LogType.CONFUSED:
        return f"       😵 {_card_name(log.get('cardId'))} is confused"

    # ── Misc ──────────────────────────────────────────────────────────────────
    if t == LogType.COIN:
        flip = "heads ✓" if log.get("head") else "tails ✗"
        return f"       🪙 Coin flip → {flip}"

    if t == LogType.RESULT:
        r = log.get("result")
        winner = player_name(r) if r in (0, 1) else None
        line   = f"  🏆  {winner} wins!" if winner else "  Draw"
        border = "═" * 52
        return f"\n{border}\n{line}\n{border}"

    # Unknown log type — show raw so nothing is invisible
    try:
        name = LogType(t).name
    except ValueError:
        name = str(t)
    return f"  [?  {name}]"


# ── Full history ──────────────────────────────────────────────────────────────

def format_history(
    history: list,
    agent_names: list[str] | None = None,
) -> str:
    """
    Format the complete visualize history into a readable game replay.

    Parameters
    ----------
    history      : list returned by env.steps[0][0]["visualize"]
    agent_names  : optional [name_agent0, name_agent1] shown in the output
                   instead of generic "Agent 0" / "Agent 1"
    """
    names = (agent_names or [])

    def player_name(idx: int | None) -> str:
        if idx is None:
            return "?"
        if idx < len(names):
            return names[idx]
        return f"Agent {idx}"

    lines: list[str] = []

    for entry in history:
        obs  = entry.get("obs") or {}
        logs = obs.get("logs") or []
        for log in logs:
            text = format_log(log, player_name)
            if text is not None:
                lines.append(text)

    return "\n".join(lines)
