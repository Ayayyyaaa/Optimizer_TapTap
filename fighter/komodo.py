# ═══════════════════════════════════════════════════════════════
#  KOMODO.PY  —  Fighter : Komodo
#  Faction : Mantis
# ═══════════════════════════════════════════════════════════════
#
#  SKILLS :
#
#  [ACTIVE] Venom Sweep :
#    - 750% dmg aux 3 ennemis avec le plus d'ATK.
#    - Réduit leur Hit Chance et Crit Chance de 60% pendant 3 rounds.
#
#  [PASSIVE 1] Apex Scales :
#    - ATK +60%, HP +50%, CR +50%, SPD +50.
#
#  [PASSIVE 2] Crushing Bite :
#    - Attaque basique : cible l'ennemi avec le moins de HP, 200% dmg.
#    - Réduit ATK et Armor de la cible de 50% pendant 3 rounds.
#
#  [PASSIVE 3] Reactive Scales :
#    - Si Komodo reçoit des dégâts d'une attaque basique :
#      60% chance de contre-attaque + Stun 2 rounds.
#
#  Stats de base :
#    HP 3 558 867 | ATK 85 942 | DEF 1 920 | SPD 1 283
#    CR 65%
# ═══════════════════════════════════════════════════════════════

import random
from character import Character
from debuffs import apply_debuff


class Komodo:
    """Fighter Komodo — Faction Mantis."""

    BASE_HP  = 3_558_867
    BASE_ATK = 85_942
    BASE_DEF = 1_920
    BASE_SPD = 1_283
    BASE_CR  = 0.65
    BASE_CD  = 1.50

    def __init__(self):
        self.character = Character(
            name               = "Komodo",
            faction            = "Mantis",
            hp                 = self.BASE_HP,
            atk                = self.BASE_ATK,
            defense            = self.BASE_DEF,
            spd                = self.BASE_SPD,
            skill_dmg          = 0.0,
            block              = 0.0,
            cr                 = self.BASE_CR,
            cd                 = self.BASE_CD,
            dmg_reduce         = 0.0,
            control_resist     = 0.0,
            hit_chance         = 0.0,
            armor_break        = 0.0,
            control_precision  = 0.0,
            stealth            = False,
            weapon             = [],
            dragons            = [],
            pos                = "front",
        )

        self.character._immune = []

    # ══════════════════════════════════════════════════════════
    #  BATTLE START — Apex Scales (P1)
    # ══════════════════════════════════════════════════════════

    def battle_start(self, allies: list, enemies: list):
        char = self.character

        char.atk    += 0.60 * char.base_atk
        char.max_hp  = int(char.max_hp * 1.50)
        char.hp      = char.max_hp
        char.cr      = min(1.0, char.cr + 0.50)
        char.spd    += 50

    # ══════════════════════════════════════════════════════════
    #  ROUND START
    # ══════════════════════════════════════════════════════════

    def on_round_start(self, allies: list):
        pass

    # ══════════════════════════════════════════════════════════
    #  ATTAQUE BASIQUE — Crushing Bite (P2)
    # ══════════════════════════════════════════════════════════

    def basic_atk(self, enemies: list, allies: list) -> float:
        """
        Crushing Bite :
        Cible l'ennemi avec le moins de HP, 200% dmg.
        Applique atk_reduce (-50%) et armor_reduction (-50%) pendant 3 rounds.
        """
        char = self.character

        alive_enemies = [e for e in enemies
                         if getattr(getattr(e, "character", e), "is_alive", True)]
        if not alive_enemies:
            return 0.0

        target      = min(alive_enemies,
                          key=lambda e: getattr(getattr(e, "character", e), "hp", float("inf")))
        target_char = getattr(target, "character", target)

        raw = char.atk * char.attack_multiplier * 2.00
        dmg = self._calc_damage(char, raw, is_basic=True)
        if target_char.hp <= 0:
            target_char.hp       = 0
            target_char.is_alive = False

        # ATK -50% et Armor -50% pendant 3 rounds
        # On utilise atk_reduce (×0.50 ici, plus fort que la valeur par défaut 0.15)
        # et armor_reduction (×0.50, plus fort que la valeur par défaut 0.40).
        # On applique directement sur les stats car les DEBUFF_DEFS ont des deltas fixes.
        if target_char.is_alive:
            self._apply_crushing_bite(target_char)

        char.energy += 20
        for w in char.weapon:
            w.on_basic_attack(char, dmg)

        return dmg

    # ══════════════════════════════════════════════════════════
    #  ULT — VENOM SWEEP
    # ══════════════════════════════════════════════════════════

    def ult(self, enemies: list, allies: list) -> float:
        """
        Venom Sweep :
        750% dmg aux 3 ennemis avec le plus d'ATK.
        Hit Chance -60% et CR -60% pendant 3 rounds.
        """
        char = self.character

        alive_enemies = [e for e in enemies
                         if getattr(getattr(e, "character", e), "is_alive", True)]
        if not alive_enemies:
            return 0.0

        # 3 ennemis avec le plus d'ATK
        targets = sorted(alive_enemies,
                         key=lambda e: getattr(getattr(e, "character", e), "atk", 0),
                         reverse=True)[:3]

        total_dmg = 0.0
        for target in targets:
            target_char = getattr(target, "character", target)
            if not target_char.is_alive:
                continue

            raw = char.atk * char.attack_multiplier * 7.50
            raw *= (1.0 + char.skill_dmg)
            dmg  = self._calc_damage(char, raw, is_basic=False)
            total_dmg += dmg

            if target_char.hp <= 0:
                target_char.hp       = 0
                target_char.is_alive = False

            # Hit Chance -60% (taunted = -15% → on applique 4× ou directement)
            # et CR -60% pendant 3 rounds — valeurs custom, appliquées directement.
            if target_char.is_alive:
                self._apply_venom_debuffs(target_char)

        return total_dmg

    # ══════════════════════════════════════════════════════════
    #  RÉCEPTION DE DÉGÂTS — Reactive Scales (P3)
    # ══════════════════════════════════════════════════════════

    def on_hit_received(self, attacker, damage: float, allies: list,
                        is_basic: bool = True) -> float:
        """
        Reactive Scales :
        Si dégâts viennent d'une attaque basique → 60% chance contre-attaque + Stun.
        """
        char = self.character
        char.hp -= damage

        if is_basic and random.random() < 0.60:
            attacker_char = getattr(attacker, "character", attacker)
            counter = char.atk * char.attack_multiplier * 1.00   # counter non spécifié → 100% ATK
            attacker_char.hp -= counter
            if attacker_char.hp <= 0:
                attacker_char.hp       = 0
                attacker_char.is_alive = False
            apply_debuff(attacker_char, "stun", duration=2, source=self)

        if char.hp <= 0:
            char.hp = 0

        return damage

    # ══════════════════════════════════════════════════════════
    #  ROUND END
    # ══════════════════════════════════════════════════════════

    def on_round_end(self, allies: list, round_number: int):
        char = self.character
        for w in char.weapon:
            w.on_round_end(char, allies, round_number)
        for d in char.dragons:
            d.on_round_end(char, allies, round_number)

    def on_ally_die(self, allies: list):
        pass

    def on_self_death(self, allies: list) -> bool:
        return False

    # ══════════════════════════════════════════════════════════
    #  HELPERS
    # ══════════════════════════════════════════════════════════

    def _calc_damage(self, char, raw_dmg: float, is_basic: bool = False) -> float:
        if random.random() < char.cr:
            raw_dmg *= char.cd
        return max(0.0, raw_dmg)

    def _apply_crushing_bite(self, target_char):
        """
        ATK -50% et Armor -50% pendant 3 rounds.
        Les DEBUFF_DEFS ont des deltas fixes (atk_reduce -15%, armor_reduction -40%).
        On pose les debuffs standards les plus proches et on complète par application directe.
        Utilise atk_reduce (delta -15% base) et armor_reduction (delta -40% base) existants,
        mais avec les vrais 50% appliqués directement pour refléter le skill.
        """
        # On applique les debuffs custom via modification directe + durée trackée manuellement
        # car DEBUFF_DEFS ne supporte pas des deltas variables par fighter.
        # On stocke le malus dans des attributs dédiés pour pouvoir les retirer après 3 rounds.
        if not hasattr(target_char, "_komodo_bite_rounds"):
            target_char._komodo_bite_rounds = 0
            target_char._komodo_atk_stolen  = 0.0
            target_char._komodo_def_stolen  = 0.0

        # Retire l'ancien malus s'il est encore actif
        if target_char._komodo_bite_rounds > 0:
            target_char.atk     += target_char._komodo_atk_stolen
            target_char.defense += target_char._komodo_def_stolen

        atk_malus = getattr(target_char, "base_atk", target_char.atk) * 0.50
        def_malus = getattr(target_char, "base_defense", target_char.defense) * 0.50

        target_char.atk     = max(0.0, target_char.atk - atk_malus)
        target_char.defense = max(0.0, target_char.defense - def_malus)

        target_char._komodo_bite_rounds = 3
        target_char._komodo_atk_stolen  = atk_malus
        target_char._komodo_def_stolen  = def_malus

    def _apply_venom_debuffs(self, target_char):
        """
        Hit Chance -60% et CR -60% pendant 3 rounds.
        Même approche que _apply_crushing_bite : application directe trackée.
        """
        if not hasattr(target_char, "_komodo_venom_rounds"):
            target_char._komodo_venom_rounds  = 0
            target_char._komodo_hit_stolen    = 0.0
            target_char._komodo_cr_stolen     = 0.0

        if target_char._komodo_venom_rounds > 0:
            target_char.hit_chance += target_char._komodo_hit_stolen
            target_char.cr         += target_char._komodo_cr_stolen

        hit_malus = 0.60
        cr_malus  = 0.60

        target_char.hit_chance = max(0.0, getattr(target_char, "hit_chance", 0) + hit_malus)
        target_char.cr         = max(0.0, getattr(target_char, "cr", 0) - cr_malus)

        target_char._komodo_venom_rounds = 3
        target_char._komodo_hit_stolen   = hit_malus
        target_char._komodo_cr_stolen    = cr_malus