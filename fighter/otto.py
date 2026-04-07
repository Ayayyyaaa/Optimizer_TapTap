# ═══════════════════════════════════════════════════════════════
#  OTTO.PY  —  Fighter : Otto
# ═══════════════════════════════════════════════════════════════
#
#  SKILLS :
#
#  [ACTIVE] Rapid Bleed :
#    - 4 coups de 250% sur un ennemi aléatoire.
#    - Chaque coup : 90% chance d'appliquer Bleed (50% ATK dmg, 5 rounds).
#    - 75% chance : CR +50% à soi et aux alliés de même rangée (2 rounds).
#    - Si un coup est un crit : ATK +40% pendant 7 rounds.
#
#  [PASSIVE 1] Apex Striker :
#    - ATK +40%, CD +45%, SPD +140, Armor Break +75%.
#    - Immune à Bleed et Speed Reduction.
#
#  [PASSIVE 2] Hemorrhage :
#    - Attaque basique : cible l'ennemi avec le plus d'ATK, 400% dmg.
#    - Si la cible saigne : +125% dmg supplémentaires (total 525%).
#
#  [PASSIVE 3] Killing Drive :
#    - Killing Blow : soin 75% Max HP + DMG Reduce +55% + SPD +100
#      pendant 3 rounds.
#    - Se déclenche à chaque killing blow (pas de limite).
#
#  Stats de base :
#    HP 4 495 412 | ATK 72 988 | DEF 2 400 | SPD 1 230
#    Skill DMG 30% | Block 20% | CR 15% | CD 0
#    DMG Reduce 40% | Hit Chance 0 | Armor Break 0
#    Control Resist 0 | Control Precision 0 | Stealth 0
# ═══════════════════════════════════════════════════════════════

import random
from character import Character
from debuffs import apply_debuff, has_debuff, apply_buff, remove_buff



class Otto:
    """Fighter Otto."""

    BASE_HP          = 4_495_412
    BASE_ATK         = 72_988
    BASE_DEF         = 2_400
    BASE_SPD         = 1_230
    BASE_CR          = 0.15
    BASE_CD          = 1.50   # CD affiché = 0 dans l'image → valeur par défaut
    BASE_SKILL_DMG   = 0.30
    BASE_BLOCK       = 0.20
    BASE_DMG_REDUCE  = 0.40

    def __init__(self):
        self.character = Character(
            name               = "Otto",
            faction            = "Unknown",   # à ajuster
            hp                 = self.BASE_HP,
            atk                = self.BASE_ATK,
            defense            = self.BASE_DEF,
            spd                = self.BASE_SPD,
            skill_dmg          = self.BASE_SKILL_DMG,
            block              = self.BASE_BLOCK,
            cr                 = self.BASE_CR,
            cd                 = self.BASE_CD,
            dmg_reduce         = self.BASE_DMG_REDUCE,
            control_resist     = 0.0,
            hit_chance         = 0.0,
            armor_break        = 0.0,
            control_precision  = 0.0,
            stealth            = False,
            weapon             = [],
            dragons            = [],
            pos                = "front",
        )

        # Immunités (Apex Striker P1)
        self.character._immune = ["bleeding", "spd_reduce"]

    # ══════════════════════════════════════════════════════════
    #  BATTLE START — Apex Striker (P1)
    # ══════════════════════════════════════════════════════════

    def battle_start(self, allies: list, enemies: list):
        char = self.character

        char.atk         += 0.40 * char.base_atk
        char.cd          += 0.45
        char.spd         += 140
        char.armor_break  = getattr(char, "armor_break", 0.0) + 0.75

    # ══════════════════════════════════════════════════════════
    #  ATTAQUE BASIQUE — Hemorrhage (P2)
    # ══════════════════════════════════════════════════════════

    def basic_atk(self, enemies: list, allies: list) -> float:
        """
        Hemorrhage :
        Cible l'ennemi avec le plus d'ATK.
        400% ATK dmg. Si la cible saigne : +125% supplémentaires (525% total).
        """
        char = self.character

        alive_enemies = [e for e in enemies
                         if getattr(getattr(e, "character", e), "is_alive", True)]
        if not alive_enemies:
            return 0.0

        # Cible = ennemi avec le plus d'ATK
        target      = max(alive_enemies,
                          key=lambda e: getattr(getattr(e, "character", e), "atk", 0))
        target_char = getattr(target, "character", target)

        mult = 5.25 if has_debuff(target_char, "bleeding") else 4.00
        raw  = char.atk * char.attack_multiplier * mult
        dmg  = self._calc_damage(char, raw)

        was_killing_blow = False
        target_char.hp -= dmg
        if target_char.hp <= 0:
            target_char.hp       = 0
            target_char.is_alive = False
            was_killing_blow     = True

        char.energy += 20
        for w in char.weapon:
            w.on_basic_attack(char, dmg)

        if was_killing_blow:
            self._on_killing_blow()

        return dmg

    # ══════════════════════════════════════════════════════════
    #  ULT — RAPID BLEED
    # ══════════════════════════════════════════════════════════

    def ult(self, enemies: list, allies: list) -> float:
        """
        Rapid Bleed :
        4 coups de 250% sur un ennemi aléatoire.
        90% chance de Bleed (50% ATK/tour, 5 rounds) par coup.
        75% chance : CR +50% à soi et même rangée (2 rounds).
        Si crit sur un coup : ATK +40% pendant 7 rounds.
        """
        char = self.character

        alive_enemies = [e for e in enemies
                         if getattr(getattr(e, "character", e), "is_alive", True)]
        if not alive_enemies:
            return 0.0

        target      = random.choice(alive_enemies)
        target_char = getattr(target, "character", target)

        total_dmg   = 0.0
        any_crit    = False

        for _ in range(4):
            if not target_char.is_alive:
                break

            raw      = char.atk * char.attack_multiplier * 2.50
            raw     *= (1.0 + char.skill_dmg)
            dmg, is_crit = self._calc_damage_with_crit(char, raw)

            if is_crit:
                any_crit = True

            target_char.hp -= dmg
            total_dmg      += dmg

            if target_char.hp <= 0:
                target_char.hp       = 0
                target_char.is_alive = False
                self._on_killing_blow()

            # 90% chance de Bleed par coup (50% ATK/tour, 5 rounds)
            if random.random() < 0.90:
                apply_debuff(target_char, "bleeding", duration=5,
                             source=self, dot_multiplier=0.50)

        # ATK +40% si au moins un crit (buff re-posable : retire l'ancien d'abord)
        if any_crit:
            bonus = 0.40 * char.base_atk
            if any(b["type"] == "otto_atk_up" for b in char.buffs):
                remove_buff(char, "otto_atk_up")
            apply_buff(char, "otto_atk_up", duration=7,
                       delta_override=bonus, source=self)

        # 75% chance : CR +50% à soi et aux alliés de même rangée (2 rounds)
        if random.random() < 0.75:
            my_pos = getattr(char, "pos", "front")
            for ally in allies:
                a_char = ally.character
                if not a_char.is_alive:
                    continue
                if getattr(a_char, "pos", "front") == my_pos:
                    if any(b["type"] == "otto_cr_up" for b in a_char.buffs):
                        remove_buff(a_char, "otto_cr_up")
                    apply_buff(a_char, "otto_cr_up", duration=2,
                               delta_override=0.50, source=self)

        return total_dmg

    # ══════════════════════════════════════════════════════════
    #  PASSIVE 3 — Killing Drive
    # ══════════════════════════════════════════════════════════

    def _on_killing_blow(self):
        """
        Killing Drive :
        Soin 75% Max HP + DMG Reduce +55% + SPD +100 pendant 3 rounds.
        Se déclenche à chaque killing blow.
        """
        char = self.character

        # Soin 75% Max HP
        char.hp = min(char.max_hp, char.hp + char.max_hp * 0.75)

        # DMG Reduce +55% (retire l'ancien buff si présent pour refresh)
        if any(b["type"] == "otto_dr_up" for b in char.buffs):
            remove_buff(char, "otto_dr_up")
        apply_buff(char, "otto_dr_up", duration=3,
                   delta_override=0.55, source=self)

        # SPD +100 (retire l'ancien buff si présent pour refresh)
        if any(b["type"] == "otto_spd_up" for b in char.buffs):
            remove_buff(char, "otto_spd_up")
        apply_buff(char, "otto_spd_up", duration=3,
                   delta_override=100, source=self)

    # ══════════════════════════════════════════════════════════
    #  HOOKS MOTEUR
    # ══════════════════════════════════════════════════════════

    def on_round_start(self, allies: list):
        pass

    def on_round_end(self, allies: list, round_number: int):
        char = self.character
        for w in char.weapon:
            w.on_round_end(char, allies, round_number)
        for d in char.dragons:
            d.on_round_end(char, allies, round_number)

    def on_ally_die(self, allies: list):
        pass

    def on_self_death(self, allies: list) -> bool:
        return False   # pas de revival

    # ══════════════════════════════════════════════════════════
    #  HELPERS
    # ══════════════════════════════════════════════════════════

    def _calc_damage(self, char, raw_dmg: float) -> float:
        """Calcul standard avec crit."""
        if random.random() < char.cr:
            raw_dmg *= char.cd
        return max(0.0, raw_dmg)

    def _calc_damage_with_crit(self, char, raw_dmg: float) -> tuple[float, bool]:
        """Calcul avec crit, retourne (dmg, was_crit)."""
        is_crit = random.random() < char.cr
        if is_crit:
            raw_dmg *= char.cd
        return max(0.0, raw_dmg), is_crit