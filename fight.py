# ═══════════════════════════════════════════════════════════════
#  FIGHT.PY  —  Moteur de simulation d'équipe
# ═══════════════════════════════════════════════════════════════
#
#  BUG FIX (Shuriken) :
#    Le dummy ennemi avait la faction du premier fighter du pool,
#    jamais celle du boss cible. Weapon_Shuriken compare
#    target.faction à factions.get(fighter.faction), donc il ne
#    déclenchait son ×3 que par accident.
#    Fix : le dummy reçoit maintenant la faction de TARGET_BOSS,
#    ce qui reproduit fidèlement le combat contre le vrai boss.
#
#  BUG FIX (Okami / Last One Standing) :
#    Le dummy avait des HP quasi-infinis et n'attaquait pas →
#    aucun allié ne mourait jamais → on_ally_die() jamais appelé.
#    Pour rester cohérent avec fight.py (pas de vrai boss),
#    on simule une petite attaque du dummy chaque round pour
#    reproduire une pression réaliste et permettre des morts.
#    Note : pour une évaluation complète avec boss réel,
#    utiliser combat_engine.simulate_team() (déjà fait dans optimizer.py).
# ═══════════════════════════════════════════════════════════════

import random
from debuffs import tick_debuffs, tick_buffs
from config import TARGET_BOSS


def simulate_team(team_build: dict, nb_rounds: int = 10, nb_simulations: int = 8) -> float:
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
        f.character.position = "front" if slot_idx < 3 else "back"
        fighters.append(f)

    # ── Dummy ennemi ──────────────────────────────────────────
    # BUG FIX : faction = celle du boss cible (et non du premier fighter du pool)
    # pour que Weapon_Shuriken détecte correctement la faction favorable.
    boss_instance   = TARGET_BOSS()
    dummy_cls       = team_build[0]["fighter_cls"]
    dummy           = dummy_cls()
    dummy.character.hp           = 9_999_999_999
    dummy.character.max_hp       = 9_999_999_999
    dummy.character.position     = "back"
    dummy.character.faction      = boss_instance.faction   # ← FIX
    dummy.character.atk          = boss_instance.atk       # pour les mécas qui lisent l'ATK ennemie
    dummy.character.defense      = boss_instance.defense
    dummy.character.spd          = boss_instance.spd
    dummy.character.dmg_reduce   = boss_instance.dmg_reduce
    dummy.character.hit_chance   = getattr(boss_instance, "hit_chance", 0.10)
    dummy.character.cr           = boss_instance.cr
    dummy.character.cd           = boss_instance.cd
    enemies = [dummy]

    allies = fighters

    # ── Battle start ──────────────────────────────────────────
    for f in fighters:
        char = f.character
        for w in char.weapon:
            w.on_battle_start(char)
        for d in char.dragons:
            d.on_battle_start(char)

    for f in fighters:
        if hasattr(f, "battle_start"):
            f.battle_start(allies, enemies)

    total_dmg = 0

    # ── Boucle de combat ─────────────────────────────────────
    for round_num in range(1, nb_rounds + 1):

        # 1. Round start
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

            if getattr(f, "_bubble_active", False):
                continue

            if char.energy >= 100:
                char.energy = 0
                total_dmg += f.ult(enemies, allies)
            else:
                total_dmg += f.basic_atk(enemies, allies)

        # 3. Attaque simplifiée du dummy (pour déclencher des morts réalistes)
        # BUG FIX (Okami) : le dummy attaque chaque round avec l'ATK du boss
        # cible, divisée par le nombre d'alliés, pour simuler une pression
        # sans être aussi létale qu'un vrai boss (on veut mesurer le DPS
        # de l'équipe, pas la survie). Cela permet à on_ally_die() de se
        # déclencher dans les configs peu défensives.
        alive_fighters = [f for f in fighters if f.character.is_alive]
        if alive_fighters:
            dmg_per_target = boss_instance.atk * 1.5 / max(1, len(alive_fighters))
            for f in alive_fighters:
                char = f.character
                # Réduit par dmg_reduce du fighter
                dmg = dmg_per_target * (1.0 - getattr(char, "dmg_reduce", 0.0))
                # Block chance
                block_chance = max(0.0, getattr(char, "block", 0.0))
                if random.random() < block_chance:
                    for w in char.weapon:
                        w.on_block(char)
                    dmg = 0.0
                char.hp -= dmg

        # 4. Round end
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

        # 5. Vérification des morts
        for f in fighters:
            char = f.character
            if char.hp <= 0 and char.is_alive:
                char.is_alive = False

                if hasattr(f, "on_self_death"):
                    f.on_self_death(allies)

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