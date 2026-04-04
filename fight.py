# ═══════════════════════════════════════════════════════════════
#  FIGHT.PY  —  Moteur de simulation d'équipe
# ═══════════════════════════════════════════════════════════════
#
#  Corrections :
#    - Attribution des positions front/back selon l'ordre des slots
#      (slots 0-2 = front, slots 3-5 = back)
#    - Appel de fighter.on_battle_start(allies, enemies) si la méthode existe
#      (nécessaire pour Laguna, Chancer, etc.)
#    - Appel de fighter.on_self_death(allies) quand un fighter meurt
#      (nécessaire pour le Bubble Mark de Laguna)
#    - tick_debuffs + tick_buffs en fin de round (debuffs avec durée)
# ═══════════════════════════════════════════════════════════════

from debuffs import tick_debuffs, tick_buffs


def simulate_team(team_build: dict, nb_rounds: int = 10, nb_simulations: int = 8) -> float:
    """
    Simule nb_simulations combats pour une équipe et retourne le DPS moyen total.
    """
    total = sum(
        _run_once(team_build, nb_rounds)
        for _ in range(nb_simulations)
    )
    return total / nb_simulations


def _run_once(team_build: dict, nb_rounds: int) -> float:
    """Un seul combat complet. Retourne les dégâts totaux de l'équipe."""

    # ── Instanciation de l'équipe ──────────────────────────────
    fighters = []
    for slot_idx, slot in team_build.items():
        f = slot["fighter_cls"]()
        f.character.weapon  = [w() for w in slot["weapons"]]
        f.character.dragons = [d(f.character) for d in slot["dragons"]]

        # Attribution de la position selon l'index du slot
        # Slots 0-2 → front-line, slots 3-5 → back-line
        f.character.position = "front" if slot_idx < 3 else "back"

        fighters.append(f)

    allies  = fighters
    dummy   = team_build[0]["fighter_cls"]()
    dummy.character.hp       = 9_999_999_999
    dummy.character.position = "back"
    enemies = [dummy]

    # ── Battle start ──────────────────────────────────────────
    for f in fighters:
        char = f.character
        for w in char.weapon:
            w.on_battle_start(char)
        for d in char.dragons:
            d.on_battle_start(char)
        # Hook fighter (Laguna, Chancer, etc.)
        if hasattr(f, "battle_start"):
            f.battle_start(allies, enemies)

    total_dmg = 0

    # ── Boucle de combat ─────────────────────────────────────
    for round_num in range(1, nb_rounds + 1):

        # 1. Round start — armes, dragons, puis fighter si hook défini
        for f in fighters:
            if not f.character.is_alive:
                continue
            char = f.character
            for w in char.weapon:
                w.on_round_start(char, allies)
            for d in char.dragons:
                d.on_round_start(char, allies)
            if hasattr(f, "on_round_start"):
                f.on_round_start(allies)

        # 2. Actions des fighters
        for f in fighters:
            char = f.character
            if not char.is_alive or char.is_stunned:
                continue

            # Bubble active = immunisé aux dégâts ce round
            if getattr(f, "_bubble_active", False):
                continue

            if char.energy >= 100:
                char.energy = 0
                total_dmg += f.ult(enemies, allies)
            else:
                total_dmg += f.basic_atk(enemies, allies)

        # 3. Round end — armes, dragons, fighter si hook défini
        for f in fighters:
            if not f.character.is_alive:
                continue
            char = f.character
            tick_debuffs(char)
            tick_buffs(char)
            for w in char.weapon:
                w.on_round_end(char, allies, round_num)
            for d in char.dragons:
                d.on_round_end(char, allies, round_num)
            if hasattr(f, "on_round_end"):
                f.on_round_end(allies, round_num)

        # 4. Vérification des morts
        for f in fighters:
            char = f.character
            if char.hp <= 0 and char.is_alive:
                char.is_alive = False

                # Hook mort sur le fighter lui-même (ex: Laguna Bubble Mark)
                if hasattr(f, "on_self_death"):
                    f.on_self_death(allies)

                # Callbacks sur les alliés survivants
                for other in fighters:
                    if not other.character.is_alive:
                        continue
                    for w in other.character.weapon:
                        w.on_ally_die(other.character, allies)
                    for d in other.character.dragons:
                        d.on_ally_die(other.character, allies)
                    if hasattr(other, "on_ally_die"):
                        other.on_ally_die(allies)

    return total_dmg