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
    team = False

    # ── Tracker de dégâts par fighter ────────────────────────
    # Structure : { nom : {"direct": 0, "dot": 0, "orb": 0} }
    dmg_tracker: dict[str, dict[str, float]] = {
        f.character.name: {"direct": 0.0, "dot": 0.0, "orb": 0.0}
        for f in allies
    }

    # ── Tracker d'impact des supports ────────────────────────
    # Enregistre les buffs appliqués par chaque fighter sur ses alliés.
    # Structure : { source_name : { target_name : { buff_type : delta_total } } }
    support_tracker: dict[str, dict] = {
        f.character.name: {} for f in allies
    }
    if team:
        print(f"fighters: {[f.character.name for f in allies]}, boss: {boss.name}")
    # ── Battle start ─────────────────────────────────────────
    for f in allies:
        char = f.character
        if FACTION_COUNTER.get(char.faction) == boss.faction:
            char._faction_dmg_bonus = 0.30   # +30% dégâts directs
            char._faction_hit_bonus = True
        else:
            char._faction_dmg_bonus = 0.0
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
        #print(f"\n──── Round {round_num} ────")
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
                    dmg_tracker[f.character.name]["orb"] += final_orb

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

            if char.energy >= 100:
                char.energy = 0
                raw_dmg  = f.ult(enemies, allies)
                is_skill = True
            else:
                raw_dmg  = f.basic_atk(enemies, allies)
                is_skill = False
                char.energy += 50
            if not _roll_hit(char):
                raw_dmg *= 0.5
            if getattr(char, "_faction_dmg_bonus", 0.0) > 0:
                raw_dmg *= (1.0 + char._faction_dmg_bonus)
            final_dmg = boss.take_damage(raw_dmg, char, is_skill=is_skill)
            total_dmg_to_boss += final_dmg
            dmg_tracker[char.name]["direct"] += final_dmg

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
        # Les dégâts DoT sur le boss sont attribués à leur source (fighter).
        # tick_debuffs() retourne le total DoT du round ; on reventile
        # par debuff via une boucle sur boss.debuffs AVANT le tick.
        dot_per_source = _collect_dot_sources(boss)
        dot_dmg_on_boss = tick_debuffs(boss)
        total_dmg_to_boss += dot_dmg_on_boss

        # Ventilation des dégâts DoT vers chaque fighter source
        if dot_dmg_on_boss > 0 and dot_per_source:
            total_weight = sum(dot_per_source.values())
            for name, weight in dot_per_source.items():
                if name in dmg_tracker and total_weight > 0:
                    dmg_tracker[name]["dot"] += dot_dmg_on_boss * (weight / total_weight)

        for f in allies:
            char = f.character
            tick_debuffs(char)
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
        if getattr(f.character, "_faction_dmg_bonus", 0.0) > 0:
            f.character._faction_dmg_bonus = 0.0

    # ── Snapshot final des buffs actifs (contribution des supports) ──
    _collect_support_impact(allies, support_tracker)

    if verbose:
        _print_dmg_breakdown(dmg_tracker, total_dmg_to_boss, nb_rounds)
        _print_support_impact(support_tracker)

    return total_dmg_to_boss, dmg_tracker


def _collect_dot_sources(boss: Boss) -> dict[str, float]:
    """
    Parcourt les debuffs actifs sur le boss AVANT le tick et retourne,
    pour chaque fighter source, le poids DoT qu'il représente ce round
    (atk_source × dot_multiplier). Utilisé pour ventiler les dégâts DoT.
    """
    sources: dict[str, float] = {}
    for debuff in boss.debuffs:
        multi = debuff.get("dot_multiplier")
        if multi is None:
            continue
        source = debuff.get("source")
        source_char = getattr(source, "character", source) if source else None
        name = getattr(source_char, "name", None) or getattr(source, "name", "?")
        atk  = getattr(source_char, "atk", 0.0) if source_char else 0.0
        sources[name] = sources.get(name, 0.0) + atk * multi
    return sources


def _print_dmg_breakdown(
    tracker:   dict[str, dict[str, float]],
    total:     float,
    nb_rounds: int,
):
    """Affiche un tableau récapitulatif des dégâts par fighter."""
    print(f"\n{'═'*62}")
    print(f"  BREAKDOWN DES DÉGÂTS ({nb_rounds} rounds)")
    print(f"{'═'*62}")
    print(f"  {'Perso':<14} {'Direct':>14} {'DoT':>12} {'Orb':>10} {'Total':>13} {'%':>6}")
    print(f"  {'─'*14} {'─'*14} {'─'*12} {'─'*10} {'─'*13} {'─'*6}")

    rows = []
    for name, d in tracker.items():
        fighter_total = d["direct"] + d["dot"] + d["orb"]
        rows.append((name, d["direct"], d["dot"], d["orb"], fighter_total))

    rows.sort(key=lambda r: r[4], reverse=True)

    for name, direct, dot, orb, ftotal in rows:
        pct = (ftotal / total * 100) if total > 0 else 0.0
        print(f"  {name:<14} {direct:>14,.0f} {dot:>12,.0f} {orb:>10,.0f} "
              f"{ftotal:>13,.0f} {pct:>5.1f}%")

    print(f"  {'─'*14} {'─'*14} {'─'*12} {'─'*10} {'─'*13} {'─'*6}")
    print(f"  {'TOTAL':<14} {'':<14} {'':<12} {'':<10} {total:>13,.0f} {'100.0':>5}%")
    print(f"{'═'*62}\n")


def _roll_hit(char) -> bool:
    miss_chance = max(0.0, getattr(char, "hit_chance", 0.15))
    return random.random() >= miss_chance


def _collect_support_impact(allies: list, support_tracker: dict):
    """
    En fin de combat, lit les buffs encore actifs sur chaque fighter
    et les attribue à leur source dans le support_tracker.
    Permet de voir l'impact réel de chaque support sur ses alliés.
    """
    for fighter in allies:
        char = fighter.character
        for buff in char.buffs:
            source = buff.get("source")
            if source is None:
                continue
            source_char = getattr(source, "character", source)
            source_name = getattr(source_char, "name", "?")
            if source_name == char.name:
                continue   # buff auto-appliqué, pas un support
            if source_name not in support_tracker:
                support_tracker[source_name] = {}
            target_data = support_tracker[source_name].setdefault(char.name, {})
            btype = buff["type"]
            delta = buff.get("delta", 0.0)
            target_data[btype] = target_data.get(btype, 0.0) + delta


def _print_support_impact(support_tracker: dict):
    """Affiche le tableau d'impact des supports (buffs donnés à leurs alliés)."""
    # Filtre les sources qui n'ont rien bufféé
    active = {src: targets for src, targets in support_tracker.items() if targets}
    if not active:
        return

    print(f"\n{'═'*62}")
    print(f"  IMPACT DES SUPPORTS (buffs actifs en fin de combat)")
    print(f"{'═'*62}")

    STAT_LABELS = {
        "skill_dmg":   "Skill DMG",
        "cd":          "Crit DMG",
        "cr":          "Crit Chance",
        "atk":         "ATK",
        "armor_break": "Armor Break",
        "dmg_reduce":  "DMG Reduce",
        "spd":         "SPD",
        "defense":     "Defense",
        "heal_effect": "Heal Effect",
    }

    # Map buff_type → stat via BUFF_DEFS
    from debuffs import BUFF_DEFS
    buff_to_stat = {btype: defn.get("stat") for btype, defn in BUFF_DEFS.items()}

    for source_name, targets in sorted(active.items()):
        print(f"\n  ▶ {source_name}")
        for target_name, buffs in sorted(targets.items()):
            lines = []
            for btype, delta in buffs.items():
                stat = buff_to_stat.get(btype)
                label = STAT_LABELS.get(stat, stat or btype)
                if abs(delta) >= 1:
                    lines.append(f"{label} +{delta:,.0f}")
                else:
                    lines.append(f"{label} +{delta*100:.0f}%")
            if lines:
                print(f"    → {target_name:<14} : {' | '.join(lines)}")

    print(f"\n{'═'*62}\n")


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
        dmg, _ = run_combat(fighters, boss, nb_rounds=nb_rounds, verbose=True)
        total += dmg

    return total / nb_simulations


def simulate_team_with_breakdown(team_build: dict, nb_rounds: int = 10,
                                  nb_simulations: int = 8, boss_cls=None
                                  ) -> tuple[float, dict[str, dict[str, float]]]:
    """
    Comme simulate_team, mais retourne aussi le breakdown de dégâts moyen par fighter.
    Structure retournée : (fitness_moyenne, {nom: {"direct": x, "dot": x, "orb": x}})
    """
    if boss_cls is None:
        boss_cls = BossDefault

    total = 0.0
    merged: dict[str, dict[str, float]] = {}

    for _ in range(nb_simulations):
        fighters = []
        for slot_idx, slot in team_build.items():
            f = slot["fighter_cls"]()
            f.character.weapon   = [w() for w in slot["weapons"]]
            f.character.dragons  = [d(f.character) for d in slot["dragons"]]
            f.character.position = slot.get("position", "front" if slot_idx < 3 else "back")
            fighters.append(f)

        boss = boss_cls()
        run_total, tracker = run_combat(fighters, boss, nb_rounds=nb_rounds, verbose=False)
        total += run_total

        for name, d in tracker.items():
            if name not in merged:
                merged[name] = {"direct": 0.0, "dot": 0.0, "orb": 0.0}
            merged[name]["direct"] += d["direct"]
            merged[name]["dot"]    += d["dot"]
            merged[name]["orb"]    += d["orb"]

    # Moyenne sur les simulations
    for name in merged:
        for k in merged[name]:
            merged[name][k] /= nb_simulations

    return total / nb_simulations, merged