"""
Named deck definitions.

Each entry in DECKS is a list of exactly 60 card IDs.
Import and use in any agent via:

    from ptcg.decks import DECKS
    my_deck = DECKS["default"]

To add a new deck, append a new key/value pair to the dict.
Card IDs can be discovered by running `card_db.load()` and inspecting
`card_db._cards`, or by checking the notebook's "Deck contents" section.
"""


DECKS: dict[str, list[int]] = {

    # ── Default deck (bundled with the cabt engine) ───────────────────────────
    # Source: kaggle_environments/envs/cabt/cabt.py
    "default": [
        721, 721,
        722, 722, 722, 722,
        723, 723, 723, 723,
        1092,
        1121, 1121,
        1145, 1145,
        1163, 1163,
        1219, 1219, 1219, 1219,
        1227, 1227, 1227, 1227,
        1262, 1262,
        3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
        3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
        3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
        3, 3, 3,
    ],  # 60 cards

    # ── Mega Lucario ex deck ──────────────────────────────────────────────────
    # Source: Kaggle sample notebook by kiyotah
    # https://www.kaggle.com/code/kiyotah/a-sample-rule-based-agent-mega-lucario-ex-deck
    #
    # Strategy: Mega Lucario ex as main attacker; Hariyama and Solrock as
    # secondary attackers. Switches battle plan based on board state.
    # Lunatone's ability refills the hand. Boss Orders targets high-value bench.
    #
    # Card IDs:
    #   673  Makuhita          ×2
    #   674  Hariyama          ×2
    #   675  Lunatone          ×2
    #   676  Solrock           ×3
    #   677  Riolu             ×3
    #   678  Mega Lucario ex   ×4
    #   1102 Dusk Ball         ×4
    #   1123 Switch            ×2
    #   1141 Premium Power Pro ×4
    #   1142 Fighting Gong     ×4
    #   1152 Poké Pad          ×4
    #   1159 Hero Cape         ×1
    #   1182 Boss Orders       ×2
    #   1192 Carmine           ×4
    #   1227 Lillie's Determination ×4
    #   1252 Gravity Mountain  ×2
    #   6    Basic Fighting Energy ×13
    "mega_lucario_ex": [
        673, 673,
        674, 674,
        675, 675,
        676, 676, 676,
        677, 677, 677,
        678, 678, 678, 678,
        1102, 1102, 1102, 1102,
        1123, 1123,
        1141, 1141, 1141, 1141,
        1142, 1142, 1142, 1142,
        1152, 1152, 1152, 1152,
        1159,
        1182, 1182,
        1192, 1192, 1192, 1192,
        1227, 1227, 1227, 1227,
        1252, 1252,
        6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6,
    ],  # 60 cards

}
