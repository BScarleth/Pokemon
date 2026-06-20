# Pokemon TCG Ruleset Reference

Sources: Bulbapedia, official Pokemon TCG rulebook (pokemon.com/us/pokemon-tcg/rules),
Kaggle competition discussion #708586

This document covers the rules as they apply to the cabt engine simulation.
Status condition mechanics exactly match the engine's `SpecialConditionType` enum.

> **Simulator is authoritative.** Where the simulator behavior differs from the official
> TCG rules, the simulator behavior is what counts in this competition. Known differences
> are documented in the section below.

---

## Simulator Differences from Official Rules

Source: https://www.kaggle.com/competitions/pokemon-tcg-ai-battle/discussion/708586

### 1. Some attacks are not selectable even when legal under official rules

In the official game, a player may declare an attack whose effect cannot fully resolve;
the turn simply ends after declaration. In the simulator, those attacks are instead treated
as **not selectable at all** from the beginning.

Affected cases:

| Scenario | Official rule | Simulator behavior |
|---|---|---|
| Attack benches a Basic from deck, but Bench is full | Declarable; effect fails silently | Attack not offered as an option |
| Attack draws cards, but deck is empty | Declarable; effect fails silently | Attack not offered as an option |
| Attack interacts with opponent's hand, but opponent has 0 cards | Declarable; effect fails silently | Attack not offered as an option |

**Impact on agent logic:** Do not assume an attack is always available just because the Pokémon
has the energy to use it. Only acts listed in `obs["select"]["option"]` can be chosen.

---

### 2. Mega Zygarde-ex — Nullifying Zero: automatic target order

**Official rule:** The attacking player may choose the order in which damage is assigned
to multiple targets.

**Simulator behavior:** Target order cannot be chosen. Coins are flipped and damage is
assigned automatically **left to right**.

**Competition impact:** Knock Out processing is simultaneous, so the order does not affect
match outcomes.

---

### 3. Simultaneous KO — prize-taking order differs

When both players' Active Pokémon are Knocked Out at the same time, the sequence differs:

| Step | Official rules | Simulator |
|---|---|---|
| 1 | Next player chooses their prizes | Next player chooses their prizes |
| 2 | Opposing player chooses their prizes | **Next player takes their prizes** |
| 3 | Both players take prizes simultaneously | Opposing player chooses their prizes |
| 4 | Next player promotes a Pokémon | Opposing player takes their prizes |
| 5 | — | Next player promotes a Pokémon |

**Competition impact:** If both players take all remaining Prize cards from a simultaneous
double KO, the result is treated as a **draw** regardless of order, so match outcomes are
unaffected.

---

---

## Deck Construction

- Exactly **60 cards** per deck.
- Maximum **4 copies** of any single card by name, except Basic Energy (unlimited).
- Must include at least **1 Basic Pokémon** (required to start the game).
- Cards are identified by integer ID in the engine; use `all_card_data()` to inspect them.

---

## Card Types

### Pokémon Cards (`CardType.POKEMON`)

The core of the game. Each Pokémon has HP, attacks, and optionally abilities.

| Subtype | Rule |
|---|---|
| **Basic** (`basic=True`) | Played directly from hand to the Bench. The only Pokémon that can start in the Active Spot. |
| **Stage 1** (`stage1=True`) | Evolved from a Basic. Requires the Basic to have been in play for at least one full turn. |
| **Stage 2** (`stage2=True`) | Evolved from a Stage 1. Same timing restriction applies. |
| **Pokémon-EX** (`ex=True`) | When KO'd, the opponent takes **2 Prize cards** instead of 1. |
| **Mega-EX** (`megaEx=True`) | Evolves from EX. Ends your turn when you Mega Evolve (unless a Spirit Link is in play). |
| **Tera** (`tera=True`) | Special variant; check card text for specific rules. |
| **ACE SPEC** (`aceSpec=True`) | Maximum **1 ACE SPEC card** across the entire deck. |

**Key Pokémon fields in the engine:**
- `hp` / `maxHp` — current and maximum HP.
- `energies` / `energyCards` — attached energy (type list and card list).
- `tools` — attached Pokémon Tool cards.
- `preEvolution` — cards that were evolved over (underneath this card).
- `appearThisTurn` — `True` if placed or promoted to Active this turn (freshness rule).

### Trainer Cards

Trainer cards are played from hand and then discarded (unless they say otherwise).

| Subtype | `CardType` value | Rule |
|---|---|---|
| **Item** | `ITEM` (1) | Play as many as you like per turn. |
| **Pokémon Tool** | `TOOL` (2) | Attach to a Pokémon. One Tool per Pokémon at a time. |
| **Supporter** | `SUPPORTER` (3) | **Only 1 per turn.** Powerful hand/deck effects. Cannot be played on the first turn by the first player. |
| **Stadium** | `STADIUM` (4) | **Only 1 per turn.** Stays in play; applies ongoing effects to both players. A new Stadium replaces the old one. |

### Energy Cards

Energy is required to pay attack costs and retreat costs.

| Subtype | `CardType` value | Rule |
|---|---|---|
| **Basic Energy** | `BASIC_ENERGY` (5) | Provides 1 energy of its type. No deck limit. |
| **Special Energy** | `SPECIAL_ENERGY` (6) | Provides variable or multiple energy; has additional effects. Limited to 4 per deck. |

Energy types map to `EnergyType`: COLORLESS, GRASS, FIRE, WATER, LIGHTNING, PSYCHIC, FIGHTING, DARKNESS, METAL, DRAGON, RAINBOW, TEAM_ROCKET.

A **Colorless** energy requirement can be satisfied by any single energy card of any type.

---

## Game Setup

1. Each player shuffles their 60-card deck.
2. Each player draws **7 cards** as their opening hand.
3. **Mulligan:** If a player has no Basic Pokémon in their opening hand, they reveal it, shuffle back, and redraw 7. The opponent may draw 1 extra card for each mulligan taken.
4. Each player sets aside **6 Prize cards** face-down from the top of their deck.
5. Each player places 1 Basic Pokémon face-down in the **Active Spot**; up to 5 more face-down on the **Bench**.
6. Both players flip their starting Pokémon face-up simultaneously.
7. The player who goes first is determined (e.g., coin flip). **The first player cannot attack or play Supporter cards on their first turn.**

---

## Turn Structure

Each turn follows this order:

### 1. Draw
Draw 1 card from the top of your deck. If you cannot draw (deck is empty), you **lose**.

### 2. Main Phase (any order, any number of times unless noted)

| Action | Limit |
|---|---|
| Play Basic Pokémon from hand to Bench | Unlimited (up to bench capacity, usually 5) |
| Evolve a Pokémon | Unlimited; Pokémon must have been in play since **before this turn** |
| Attach 1 Energy card from hand | **Once per turn** — tracked by `State.energyAttached` |
| Play Item cards | Unlimited |
| Play 1 Supporter card | **Once per turn** — tracked by `State.supporterPlayed` |
| Play 1 Stadium card | **Once per turn** — tracked by `State.stadiumPlayed` |
| Use Pokémon Abilities | As allowed by card text |
| Retreat Active Pokémon | **Once per turn** — tracked by `State.retreated` |

### 3. Attack (optional, ends the turn)

- Declare an attack on your Active Pokémon.
- Pay the energy cost by having the required energy attached.
- Apply damage and effects.
- **Attacking always ends your turn**, regardless of other actions taken.
- The first player **cannot attack on their very first turn**.

### 4. Pokémon Checkup (between turns)

After the active player's turn ends and before the next player's turn begins:
- **Poisoned:** Place 1 damage counter (10 damage) on the Pokémon.
- **Burned:** Place 2 damage counters (20 damage), then flip a coin — heads cures the Burn, tails it persists.
- **Asleep:** Flip a coin — heads wakes the Pokémon, tails it stays Asleep.
- **Paralyzed:** Cured automatically at the beginning of the owner's next turn (after one opponent turn passes).

---

## Combat

### Damage Calculation

```
Final damage = (attack base damage ± modifiers) × weakness multiplier − resistance reduction
```

- **Weakness:** If the defending Pokémon is weak to the attack's type, damage is **×2**.
- **Resistance:** If the defending Pokémon resists the attack's type, reduce damage by **−30** (value may vary by card).
- Damage is applied to the defending Pokémon's `hp`. When `hp` reaches 0, that Pokémon is **Knocked Out**.

### Type Matchups (Weakness & Resistance)

There is **no universal type chart** in the Pokemon TCG. Unlike the video games, there is no
fixed hierarchy of which types beat which. Instead, each card individually declares its own
weakness and resistance in its printed stats.

- Each Pokémon has **at most one weakness** and **at most one resistance** (or none).
- These are fixed per card and never change during a game.
- The same Pokémon species can have different weakness/resistance across different card sets.

**In the engine**, both are fields on `CardData`:

```python
card.weakness    # EnergyType | None — type this card takes ×2 damage from
card.resistance  # EnergyType | None — type this card takes −30 damage from
```

**Agent strategy note:** to exploit type matchups at runtime, build a lookup from
`all_card_data()` once (cache it — the card pool never changes mid-match), then check the
opponent's active Pokémon's weakness against the energy types you have attached:

```python
card_lookup = {c.cardId: c for c in all_card_data()}

opponent_active = obs_utils.get_active_pokemon(obs, 1)
if opponent_active:
    card = card_lookup[opponent_active["id"]]
    if card.weakness == EnergyType.FIRE:
        # prioritise fire attacks — they deal double damage
```

The energy types available in the engine (`EnergyType` enum):

| Type | Value | Type | Value |
|---|---|---|---|
| COLORLESS | 0 | FIGHTING | 6 |
| GRASS | 1 | DARKNESS | 7 |
| FIRE | 2 | METAL | 8 |
| WATER | 3 | DRAGON | 9 |
| LIGHTNING | 4 | RAINBOW | 10 |
| PSYCHIC | 5 | TEAM_ROCKET | 11 |

**COLORLESS** is not a Pokémon type that appears as a weakness or resistance — it is only
used as an energy requirement (any single energy satisfies it). RAINBOW and TEAM_ROCKET are
Special Energy types and also do not appear as weaknesses.

### Knocking Out a Pokémon

- The KO'd Pokémon and all cards attached to it go to the owner's **discard pile**.
- The opponent who caused the KO takes **1 Prize card** (2 if it was a Pokémon-EX).
- If the Active Pokémon is KO'd, the owner must immediately promote a Benched Pokémon to Active.

---

## Retreating

- Pay the retreat cost (discard energy from the Active Pokémon equal to `retreatCost`).
- Move the Active Pokémon to the Bench (if there is bench space).
- Choose a Bench Pokémon to become the new Active.
- All Special Conditions on the retreating Pokémon are **cured**.
- Only once per turn (`State.retreated`).
- An **Asleep** or **Paralyzed** Pokémon **cannot retreat**.

---

## Evolution

- A Pokémon can only evolve into the card that names it in `evolvesFrom`.
- You **cannot evolve** a Pokémon on the same turn it was put into play (it must have been in play since before this turn — check `appearThisTurn == False`).
- You **cannot evolve** on your first turn of the game.
- You can evolve as many Pokémon as you like in a single turn.
- Stage 1 → Stage 2 evolution follows the same timing rule.
- Evolving **cures all Special Conditions** on that Pokémon.
- Evolving does not remove attached Energy or Tools.

---

## Status Conditions (`SpecialConditionType`)

Only one Special Condition can be active on a Pokémon at a time (the newer one replaces the older).
All conditions are cured when the Pokémon retreats or evolves.

| Condition | Engine value | Effect |
|---|---|---|
| **Poisoned** | `POISON` (0) | During Pokémon Checkup: place **1 damage counter** (10 damage). |
| **Burned** | `BURN` (1) | During Pokémon Checkup: place **2 damage counters** (20 damage), then flip — heads cures it, tails persists. |
| **Asleep** | `SLEEP` (2) | Cannot attack or retreat. During Pokémon Checkup: flip — heads wakes it, tails stays Asleep. |
| **Paralyzed** | `PARALYZE` (3) | Cannot attack or retreat for **one turn**. Automatically cured at the start of the owner's next turn. |
| **Confused** | `CONFUSE` (4) | When attempting to attack: flip — heads the attack proceeds normally, tails place **3 damage counters** on the Confused Pokémon and end the turn. |

In the engine, the active conditions on each player's Active Pokémon are surfaced as booleans
in `PlayerState`: `poisoned`, `burned`, `asleep`, `paralyzed`, `confused`.

---

## Prize Cards

- Each player starts with **6 Prize cards** face-down.
- Each time you Knock Out an opponent's Pokémon, you take **1 Prize card** from your Prize pile (2 for Pokémon-EX).
- Prize cards are drawn to your hand and are usable immediately.
- Prize cards in the engine: `PlayerState.prize` is a list of 6 `Card | None`. Face-down prizes show as `None`.

---

## Win Conditions

You win if **any** of these occur:

1. You take your last **Prize card** (all 6 taken).
2. Your opponent has **no Pokémon in play** (Active + Bench all KO'd, with no Basic in hand to replace).
3. Your opponent **cannot draw** a card at the start of their turn (deck is empty).
4. A card effect explicitly declares you the winner.

---

## Board Zones (`AreaType`)

| Zone | Description |
|---|---|
| `DECK` | Your shuffled deck (face-down) |
| `HAND` | Cards in your hand |
| `DISCARD` | Your discard pile (face-up) |
| `ACTIVE` | Your Active Pokémon slot (1 Pokémon) |
| `BENCH` | Your Bench (up to 5 Pokémon) |
| `PRIZE` | Your 6 Prize cards (face-down) |
| `STADIUM` | The Stadium card in play (shared) |
| `ENERGY` | Energy attached to a Pokémon |
| `TOOL` | Tool card attached to a Pokémon |
| `PRE_EVOLUTION` | Pokémon cards underneath an evolved Pokémon |
| `LOOKING` | Cards currently being looked at (e.g. by a card effect) |

---

## First-Turn Restrictions (Summary)

The player who goes first on turn 1:
- **Cannot attack.**
- **Cannot play Supporter cards.**
- Can still bench Pokémon, attach energy, play Items, and evolve (though evolution requires prior turns to have played the Basic).