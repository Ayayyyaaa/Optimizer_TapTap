# ═══════════════════════════════════════════════════════════════
#  COMBAT_ENGINE.PY  —  Moteur de combat réaliste
# ═══════════════════════════════════════════════════════════════
#
#  BUG FIX (DoT / Knife) :
#    tick_debuffs() retourne maintenant les dégâts DoT infligés
#    ce round. Ces dégâts sont accumulés dans total_dmg_to_boss
#    afin que l'optimiseur voie leur contribution réelle.
#    Weapon_Knife multiplie ces dégâts × 3 automatiquement via
#    modify_dot_damage(), appelé dans tick_debuffs().
# ═══════════════════════════════════════════════════════════════

import random
from debuffs import apply_debuff, tick_debuffs, has_debuff, tick_buffs
from boss import Boss, BossDefault, _apply_incoming_damage
from data import factions as FACTION_COUNTER


def run_combat(
    fighters:       list,
    boss:           Boss  = None,
    nb_rounds:      int   = 10,
    verbose:        bool  = True,
) -> float:
    if boss is None:
        boss = BossDefault()

    allies  = fighters
    enemies = [boss]

    # ── Battle start ─────────────────────────────────────────
    for f in allies:
        char = f.character
        if FACTION_COUNTER.get(char.faction) == boss.faction:
            char.hit_chance = getattr(char, "hit_chance", 0.15) + 0.15
            char._faction_hit_bonus = True
        else:
            char._faction_hit_bonus = False

        for w in char.weapon:
            w.on_battle_start(char)
        for d in char.dragons:
            d.on_battle_start(char)

    # Hook battle_start fighters (après armes/dragons)
    for f in allies:
        if hasattr(f, "battle_start"):
            f.battle_start(allies, enemies)

    total_dmg_to_boss = 0.0

    # ── Boucle de combat ─────────────────────────────────────
    for round_num in range(1, nb_rounds + 1):
        if verbose:
            print(f"\n──── Round {round_num} ────")

        # 1. Round start
        for f in allies:
            if not f.character.is_alive:
                continue
            for w in f.character.weapon:
                w.on_round_start(f.character, allies)
            for d in f.character.dragons:
                d.on_round_start(f.character, allies)
            if hasattr(f, "on_round_start"):
                f.on_round_start(allies)
            if hasattr(f, "on_orb_attack") and f.character.is_alive:
                orb_dmg = f.on_orb_attack(enemies)
                if orb_dmg > 0:
                    final_orb = boss.take_damage(orb_dmg, f.character, is_skill=False)
                    total_dmg_to_boss += final_orb

        # 2. Actions des fighters
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

            if not _roll_hit(char):
                if verbose:
                    print(f"  [{char.name}] rate son attaque !")
                continue

            if char.energy >= 100:
                char.energy = 0
                raw_dmg  = f.ult(enemies, allies)
                is_skill = True
            else:
                char.energy+=50
                raw_dmg  = f.basic_atk(enemies, allies)
                is_skill = False

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
            for f in allies:
                char = f.character
                if not char.is_alive:
                    continue
                block_chance = max(0.0, getattr(char, "block", 0.0))
                if block_chance > 0 and random.random() < block_chance:
                    for w in char.weapon:
                        w.on_block(char)

        # 4. Round end : tick debuffs + callbacks
        # BUG FIX : tick_debuffs retourne les dégâts DoT infligés au boss.
        # On les ajoute à total_dmg_to_boss pour que l'optimiseur valorise
        # les armes et fighters qui posent des DoT (ex: Knife sur Chancer).
        dot_dmg_on_boss = tick_debuffs(boss)
        total_dmg_to_boss += dot_dmg_on_boss

        for f in allies:
            char = f.character
            tick_debuffs(char)   # dégâts DoT sur les alliés (boss attaque)
            tick_buffs(char)
            for w in char.weapon:
                w.on_round_end(char, allies, round_num)
            for d in char.dragons:
                d.on_round_end(char, allies, round_num)
            if hasattr(f, "on_round_end"):
                f.on_round_end(allies, round_num)

        tick_buffs(boss)
        for f in allies:
            if f.character.hp <= 0 and f.character.is_alive:
                f.character.is_alive = False
                if verbose:
                    print(f"  [{f.character.name}] est mort !")
                if hasattr(f, "on_self_death"):
                    f.on_self_death(allies)
                for other in allies:
                    if other.character.is_alive:
                        for w in other.character.weapon:
                            w.on_ally_die(other.character, allies)
                        for d in other.character.dragons:
                            d.on_ally_die(other.character, allies)
                        if hasattr(other, "on_ally_die"):
                            other.on_ally_die(allies)

    # ── Nettoyage bonus faction ───────────────────────────────
    for f in allies:
        if getattr(f.character, "_faction_hit_bonus", False):
            f.character.hit_chance -= 0.15

    return total_dmg_to_boss


def _roll_hit(char) -> bool:
    miss_chance = max(0.0, getattr(char, "hit_chance", 0.15))
    return random.random() >= miss_chance


def simulate_team(team_build: dict, nb_rounds: int = 10, nb_simulations: int = 8,
                  boss_cls=None) -> float:
    if boss_cls is None:
        boss_cls = BossDefault

    total = 0.0
    for _ in range(nb_simulations):
        fighters = []
        for slot_idx, slot in team_build.items():
            f = slot["fighter_cls"]()
            f.character.weapon    = [w() for w in slot["weapons"]]
            f.character.dragons   = [d(f.character) for d in slot["dragons"]]
            # La position est définie par le génome (slots 0-2 = front, 3-5 = back)
            f.character.position  = slot.get("position", "front" if slot_idx < 3 else "back")
            fighters.append(f)

        boss  = boss_cls()
        total += run_combat(fighters, boss, nb_rounds=nb_rounds, verbose=False)

    return total / nb_simulations