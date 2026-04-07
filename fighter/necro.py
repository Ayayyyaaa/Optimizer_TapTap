# ═══════════════════════════════════════════════════════════════
#  NECRO.PY  —  Fighter : Necro
# ═══════════════════════════════════════════════════════════════
#
#  SKILLS :
#
#  [ACTIVE] Dark Affliction :
#    - 450% dmg à 4 ennemis aléatoires.
#    - 75% chance d'appliquer Dark Corruption (3 rounds) par cible.
#    - Dark Corruption : la cible reçoit 20% de dégâts supplémentaires
#      de toutes sources.
#
#  [PASSIVE 1] Dark Warden :
#    - Damage Reduction +45%, Control Resist +40%, Skill Damage +50%.
#    - +40% Skill Damage supplémentaires par allié Mage présent en combat.
#    - Immunité Curse et Dark Corruption.
#
#  [PASSIVE 2] Cursed Strikes :
#    - Attaque basique → 2 ennemis aléatoires à 125% dmg chacun.
#    - Applique Curse (3 rounds) : 125% ATK dmg + Heal Effect -50%.
#    - Crit Chance -40% sur les cibles (3 rounds).
#
#  [PASSIVE 3] Undying Will :
#    - La première fois que Necro meurt → Revient avec 100% Max HP
#      et se purge de tous les effets négatifs.
# ═══════════════════════════════════════════════════════════════

import random
from character import Character
from debuffs import apply_debuff, has_debuff, apply_buff

class Necro:
    """Fighter Necro."""

    BASE_HP          = 2_372_578
    BASE_ATK         = 53_714
    BASE_DEF         = 1_780
    BASE_SPD         = 1_207
    BASE_CR          = 0.15   # Crit Chance : 15 (image)
    BASE_CD          = 1.00   # Crit Damage : non affiché → base 100%
    BASE_SKILL_DMG   = 0.50   # Skill Damage : 90 total → 50% passif + 40% base image
    BASE_DMG_REDUCE  = 0.45   # Damage Reduce : 45 (image)
    BASE_CTRL_RESIST = 0.40   # Control Resist : 40 (image)

    def __init__(self):
        self.character = Character(
            name              = "Necro",
            faction           = "Mage",   # À ajuster si différent
            hp                = self.BASE_HP,
            atk               = self.BASE_ATK,
            defense           = self.BASE_DEF,
            spd               = self.BASE_SPD,
            skill_dmg         = self.BASE_SKILL_DMG,
            block             = 0.0,
            cr                = self.BASE_CR,
            cd                = self.BASE_CD,
            dmg_reduce        = self.BASE_DMG_REDUCE,
            control_resist    = self.BASE_CTRL_RESIST,
            hit_chance        = 0.0,
            armor_break       = 0.0,
            control_precision = 0.0,
            stealth           = False,
            weapon            = [],
            dragons           = [],
            pos               = "back",
        )

        # Immunités Dark Warden (P1)
        self.character._immune = ["cursed", "dark_corruption"]

        # Undying Will (P3) — une seule résurrection par combat
        self._has_revive = True

        # Suivi des alliés Mage (mis à jour au battle_start)
        self._mage_allies_count = 0

    # ══════════════════════════════════════════════════════════
    #  BATTLE START — Dark Warden (P1)
    # ══════════════════════════════════════════════════════════

    def battle_start(self, allies: list, enemies: list):
        char = self.character

        # Compte les alliés Mage (hors Necro lui-même)
        self._mage_allies_count = sum(
            1 for a in allies
            if a is not self and getattr(getattr(a, "character", a), "faction", "") == "Mage"
        )

        # Bonus Skill Damage supplémentaire : +40% par allié Mage
        char.skill_dmg += 0.40 * self._mage_allies_count

    # ══════════════════════════════════════════════════════════
    #  ROUND START
    # ══════════════════════════════════════════════════════════

    def on_round_start(self, allies: list):
        pass

    # ══════════════════════════════════════════════════════════
    #  ATTAQUE BASIQUE — Cursed Strikes (P2)
    # ══════════════════════════════════════════════════════════

    def basic_atk(self, enemies: list, allies: list) -> float:
        char = self.character

        alive_enemies = [e for e in enemies
                         if getattr(getattr(e, "character", e), "is_alive", True)]
        if not alive_enemies:
            return 0.0

        # 2 cibles aléatoires (avec remise si moins de 2 ennemis vivants)
        nb_targets = min(2, len(alive_enemies))
        targets = random.sample(alive_enemies, nb_targets)

        total_dmg = 0.0
        for target in targets:
            target_char = getattr(target, "character", target)
            if not target_char.is_alive:
                continue

            # 125% ATK dmg
            raw = char.atk * char.attack_multiplier * 1.25
            dmg = self._calc_damage(target_char, raw)

            # Bonus Dark Corruption : +20% dégâts reçus
            if has_debuff(target_char, "dark_corruption"):
                dmg *= 1.20

            target_char.hp -= dmg
            total_dmg += dmg

            if target_char.hp <= 0:
                target_char.hp       = 0
                target_char.is_alive = False

            # Curse (3 rounds) : Heal Effect -50% géré par le debuff
            apply_debuff(target_char, "cursed", duration=3, source=self, dot_multiplier=1.25)
            # 125% ATK Curse damage immédiat
            curse_dmg = char.atk * 1.25
            target_char.hp -= curse_dmg
            total_dmg += curse_dmg
            if target_char.hp <= 0 and target_char.is_alive:
                target_char.hp       = 0
                target_char.is_alive = False

            # Crit Chance -40% (3 rounds)
            apply_debuff(target_char, "cr_reduce", duration=3, source=self)

        char.energy = min(100, getattr(char, "energy", 0) + 20)
        for w in char.weapon:
            w.on_basic_attack(char, total_dmg)

        return total_dmg

    # ══════════════════════════════════════════════════════════
    #  ULT — DARK AFFLICTION
    # ══════════════════════════════════════════════════════════

    def ult(self, enemies: list, allies: list) -> float:
        char = self.character

        alive_enemies = [e for e in enemies
                         if getattr(getattr(e, "character", e), "is_alive", True)]
        if not alive_enemies:
            return 0.0

        nb_targets = min(4, len(alive_enemies))
        targets = random.sample(alive_enemies, nb_targets)

        total_dmg = 0.0
        for target in targets:
            target_char = getattr(target, "character", target)
            if not target_char.is_alive:
                continue

            # 450% ATK + bonus Skill DMG
            raw = char.atk * char.attack_multiplier * 4.50
            raw *= (1.0 + char.skill_dmg)
            dmg = self._calc_damage(target_char, raw)

            # Bonus Dark Corruption : +20% dégâts reçus
            if has_debuff(target_char, "dark_corruption"):
                dmg *= 1.20

            target_char.hp -= dmg
            total_dmg += dmg

            if target_char.hp <= 0:
                target_char.hp       = 0
                target_char.is_alive = False

            # 75% chance Dark Corruption (3 rounds)
            if random.random() < 0.75:
                apply_debuff(target_char, "dark_corruption", duration=3, source=self)

        return total_dmg

    # ══════════════════════════════════════════════════════════
    #  ON SELF DEATH — Undying Will (P3)
    # ══════════════════════════════════════════════════════════

    def on_self_death(self, allies: list) -> bool:
        """
        Appelé par le moteur quand Necro tombe à 0 HP.
        Retourne True si résurrection déclenchée (le moteur ne doit pas le marquer mort).
        Retourne False si Necro est définitivement mort.
        """
        if self._has_revive:
            self._has_revive = False
            char = self.character

            # Résurrection à 100% Max HP
            char.hp       = char.max_hp
            char.is_alive = True

            # Purge de tous les effets négatifs
            char.debuffs = []
            if hasattr(char, "is_stunned"):
                char.is_stunned = False
            if hasattr(char, "is_silenced"):
                char.is_silenced = False

            return True  # Résurrection déclenchée

        return False  # Mort définitive

    # ══════════════════════════════════════════════════════════
    #  ROUND END
    # ══════════════════════════════════════════════════════════

    def on_round_end(self, allies: list, round_number: int):
        char = self.character
        for w in char.weapon:
            w.on_round_end(char, allies, round_number)
        for d in char.dragons:
            d.on_round_end(char, allies, round_number)

    # ══════════════════════════════════════════════════════════
    #  HELPER — Calcul dégâts
    # ══════════════════════════════════════════════════════════

    def _calc_damage(self, target_char, raw_dmg: float,
                     bypass_crit: bool = False) -> float:
        char = self.character
        if not bypass_crit and random.random() < char.cr:
            raw_dmg *= char.cd
        return max(0.0, raw_dmg)