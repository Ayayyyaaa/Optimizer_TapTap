# ═══════════════════════════════════════════════════════════════
#  COMBAT_ENGINE.PY  —  Moteur de combat réaliste
# ═══════════════════════════════════════════════════════════════
#
#  Remplace l'ancien simulate_team / _run_once.
#  Intègre :
#    - Boss qui attaque chaque tour (pattern configurable)
#    - Réduction d'armure (formula armor / armor+K)
#    - True damage (bypass armor + dmg_reduce)
#    - Block chance pour les alliés
#    - Debuffs avec durée (tick en fin de round)
#    - Bonus de faction : +30% dégâts & +15% hit_chance si faction favorable
#    - hit_chance vs evasion
# ═══════════════════════════════════════════════════════════════

import random
from debuffs import apply_debuff, tick_debuffs, has_debuff, tick_buffs
from boss import Boss, BossDefault, _apply_incoming_damage
from data import factions as FACTION_COUNTER


# ═══════════════════════════════════════════════════════════════
#  POINT D'ENTRÉE PRINCIPAL
# ═══════════════════════════════════════════════════════════════

def run_combat(
    fighters:       list,
    boss:           Boss  = None,
    nb_rounds:      int   = 10,
    verbose:        bool  = False,
) -> float:
    """
    Simule un combat complet et retourne les dégâts totaux infligés au boss.

    fighters  : liste d'objets fighter (avec .character)
    boss      : instance de Boss (BossDefault si None)
    nb_rounds : nombre de tours
    verbose   : affiche les logs détaillés
    """
    if boss is None:
        boss = BossDefault()

    allies  = fighters
    enemies = [boss]   # interface commune avec l'ancien code

    # ── Battle start ─────────────────────────────────────────
    for f in allies:
        char = f.character
        # Bonus de faction vs boss
        if FACTION_COUNTER.get(char.faction) == boss.faction:
            char.hit_chance = getattr(char, "hit_chance", 0.15) + 0.15
            char._faction_hit_bonus = True   # flag pour retirer le bonus à la fin
        else:
            char._faction_hit_bonus = False

        for w in char.weapon:
            w.on_battle_start(char)
        for d in char.dragons:
            d.on_battle_start(char)

    total_dmg_to_boss = 0.0

    # ── Boucle de combat ─────────────────────────────────────
    for round_num in range(1, nb_rounds + 1):
        if verbose:
            print(f"\n──── Round {round_num} ────")

        # 1. Round start (armes, dragons)
        for f in allies:
            if not f.character.is_alive:
                continue
            for w in f.character.weapon:
                w.on_round_start(f.character, allies)
            for d in f.character.dragons:
                d.on_round_start(f.character, allies)

        # 2. Actions des fighters (ordre : spd décroissant)
        acting_fighters = sorted(
            [f for f in allies if f.character.is_alive],
            key=lambda f: f.character.spd,
            reverse=True,
        )

        for f in acting_fighters:
            char = f.character

            if char.is_stunned:
                if verbose:
                    print(f"  [{char.name}] est étourdi, passe son tour.")
                continue

            if not boss.is_alive:
                break

            # Vérification hit_chance
            if not _roll_hit(char):
                if verbose:
                    print(f"  [{char.name}] rate son attaque !")
                continue

            # Choix attaque (ult ou basic)
            if char.energy >= 100:
                char.energy = 0
                raw_dmg = f.ult(enemies, allies)
                is_skill = True
            else:
                raw_dmg = f.basic_atk(enemies, allies)
                is_skill = False

            # Application des dégâts sur le boss
            # (basic_atk / ult retournent le raw_dmg ; on applique la formule ici)
            final_dmg = boss.take_damage(raw_dmg, char, is_skill=is_skill)
            total_dmg_to_boss += final_dmg

            if verbose:
                skill_label = "ULT" if is_skill else "Basic"
                print(f"  [{char.name}] {skill_label} → {final_dmg:,.0f} dmg au boss "
                      f"(HP boss: {boss.hp:,.0f})")

        # 3. Tour du boss
        if boss.is_alive:
            boss_dmg = boss.act(allies)
            if verbose and boss_dmg > 0:
                print(f"  [BOSS {boss.name}] attaque → {boss_dmg:,.0f} dégâts total")

        # 4. Round end : tick debuffs + callbacks armes/dragons
        for f in allies:
            char = f.character
            tick_debuffs(char)
            tick_buffs(char)
            for w in char.weapon:
                w.on_round_end(char, allies, round_num)
            for d in char.dragons:
                d.on_round_end(char, allies, round_num)
        tick_debuffs(boss)

        # 5. Vérification morts
        for f in allies:
            if f.character.hp <= 0 and f.character.is_alive:
                f.character.is_alive = False
                if verbose:
                    print(f"  [{f.character.name}] est mort !")
                # Callbacks dragon/arme/fighter sur mort d'allié
                for other in allies:
                    if other.character.is_alive:
                        for w in other.character.weapon:
                            w.on_ally_die(other.character, allies)
                        for d in other.character.dragons:
                            d.on_ally_die(other.character, allies)
                        # Passive fighter (ex: Last One Standing d'Okami)
                        if hasattr(other, 'on_ally_die'):
                            other.on_ally_die(allies)

    # ── Nettoyage bonus faction ───────────────────────────────
    for f in allies:
        if getattr(f.character, "_faction_hit_bonus", False):
            f.character.hit_chance -= 0.15

    return total_dmg_to_boss


# ═══════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════

def _roll_hit(char) -> bool:
    """
    Vérifie si l'attaque du fighter touche.
    hit_chance = 0.15 par défaut = 15% de chance de RATER.
    Ici on l'interprète comme : rand < (1 - hit_chance) → miss.
    """
    miss_chance = max(0.0, getattr(char, "hit_chance", 0.15))
    return random.random() >= miss_chance


# ═══════════════════════════════════════════════════════════════
#  WRAPPER POUR L'OPTIMISEUR (remplace simulate_team)
# ═══════════════════════════════════════════════════════════════

def simulate_team(team_build: dict, nb_rounds: int = 10, nb_simulations: int = 8,
                  boss_cls=None) -> float:
    """
    Interface compatible avec optimizer.py.
    team_build : dict {idx: {"fighter_cls", "weapons", "dragons"}}
    boss_cls   : classe Boss à instancier (BossDefault si None)
    """
    if boss_cls is None:
        boss_cls = BossDefault

    total = 0.0
    for _ in range(nb_simulations):
        fighters = []
        for slot in team_build.values():
            f = slot["fighter_cls"]()
            f.character.weapon  = [w() for w in slot["weapons"]]
            f.character.dragons = [d(f.character) for d in slot["dragons"]]
            fighters.append(f)

        boss = boss_cls()
        total += run_combat(fighters, boss, nb_rounds=nb_rounds, verbose=False)

    return total / nb_simulations