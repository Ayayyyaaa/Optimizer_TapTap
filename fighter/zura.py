# ═══════════════════════════════════════════════════════════════
#  ZURA.PY  —  Fighter : Zura
# ═══════════════════════════════════════════════════════════════
#
#  SKILLS :
#
#  [ACTIVE] Rally Cry :
#    - 200% dmg à TOUS les ennemis.
#    - Si tous les alliés sont vivants → ATK +25% à toute l'équipe 3 rounds.
#    - Sinon → soin 1000% ATK réparti sur toute l'équipe.
#
#  [PASSIVE 1] War Body :
#    - HP +35%, ATK +45%, CR +45%, Skill DMG +20%, Block +25%.
#    - Immune à Stun, Petrify, Silence.
#
#  [PASSIVE 2] Judgment Strike :
#    - Basic attack : 200% dmg sur l'ennemi avec le moins de HP.
#    - Applique Torment 5 rounds sur la cible.
#      (Torment : les bonus dégâts des factions adverses sont doublés,
#       et les bonus dégâts de Zura vs factions adverses sont supprimés.)
#    - Soigne l'allié avec le moins de HP pour 500% ATK.
#    - Purifie cet allié de tous ses DoT et debuffs.
#
#  [PASSIVE 3] Last Bastion :
#    - Première fois que HP < 50% :
#      → Heal Effect +50% à toute l'équipe pendant 5 rounds.
#      → Bouclier 35% Max HP de Zura sur toute l'équipe pendant 3 rounds.
#    - Se déclenche une seule fois par combat.
#
#  Stats de base (image) :
#    HP 3 308 267 | ATK 82 503 | DEF 1 920 | SPD 1 307
#    Hit Chance 40 | CR 50% | Armor Break 30%
#    Skill DMG 0 | Block 0 | Crit DMG 0
#    DMG Reduce 0 | Control Resist 0 | Control Precision 0 | Stealth 0
# ═══════════════════════════════════════════════════════════════

import random
from character import Character
from debuffs import apply_debuff, apply_buff, has_debuff, tick_debuffs


# Torment est un debuff custom — on l'enregistre dans DEBUFF_DEFS au chargement
def _register_torment():
    from debuffs import DEBUFF_DEFS
    if "torment" not in DEBUFF_DEFS:
        # Pas d'effet stat direct : l'effet est géré dans _apply_incoming_damage
        # via un check has_debuff(defender, "torment") dans boss.py / combat_engine.
        # On l'enregistre quand même pour que apply_debuff / tick_debuffs le gèrent.
        DEBUFF_DEFS["torment"] = {"stat": None, "delta": 0, "mode": "flat"}

_register_torment()


class Zura:
    """Fighter Zura."""

    BASE_HP          = 3_308_267
    BASE_ATK         = 82_503
    BASE_DEF         = 1_920
    BASE_SPD         = 1_307
    BASE_CR          = 0.50
    BASE_CD          = 1.50   # non visible dans l'image, valeur par défaut
    BASE_HIT_CHANCE  = 0.40   # miss chance 40%  (interprétation : 40% de rater)
    BASE_ARMOR_BREAK = 0.30
    BASE_SKILL_DMG   = 0.0
    BASE_BLOCK       = 0.0

    def __init__(self):
        self.character = Character(
            name               = "Zura",
            faction            = "Howler",   # à ajuster
            hp                 = self.BASE_HP,
            atk                = self.BASE_ATK,
            defense            = self.BASE_DEF,
            spd                = self.BASE_SPD,
            skill_dmg          = self.BASE_SKILL_DMG,
            block              = self.BASE_BLOCK,
            cr                 = self.BASE_CR,
            cd                 = self.BASE_CD,
            dmg_reduce         = 0.0,
            control_resist     = 0.0,
            hit_chance         = self.BASE_HIT_CHANCE,
            armor_break        = self.BASE_ARMOR_BREAK,
            control_precision  = 0.0,
            stealth            = False,
            weapon             = [],
            dragons            = [],
            pos                = "front",
        )

        # Immunités (War Body P1)
        self.character._immune = ["stun", "petrified", "silence"]

        # Flag Passive 3
        self._last_bastion_triggered = False

        # Boucliers actifs : dict {id(fighter): hp_restant}
        self._shields: dict[int, float] = {}

    # ══════════════════════════════════════════════════════════
    #  BATTLE START — War Body (P1)
    # ══════════════════════════════════════════════════════════

    def battle_start(self, allies: list, enemies: list):
        char = self.character

        char.max_hp    = int(char.max_hp * 1.35)
        char.hp        = char.max_hp
        char.atk      += 0.45 * char.base_atk
        char.cr        = min(1.0, char.cr + 0.45)
        char.skill_dmg += 0.20
        char.block     += 0.25

    # ══════════════════════════════════════════════════════════
    #  ROUND START — tick boucliers Last Bastion
    # ══════════════════════════════════════════════════════════

    def on_round_start(self, allies: list):
        pass   # les boucliers sont gérés dans on_hit_received

    # ══════════════════════════════════════════════════════════
    #  ATTAQUE BASIQUE — Judgment Strike (P2)
    # ══════════════════════════════════════════════════════════

    def basic_atk(self, enemies: list, allies: list) -> float:
        """
        Judgment Strike :
        - Cible l'ennemi avec le moins de HP.
        - 200% ATK dmg.
        - Applique Torment 5 rounds.
        - Soigne l'allié avec le moins de HP pour 500% ATK.
        - Purifie cet allié de tous ses DoT et debuffs.
        """
        char = self.character

        alive_enemies = [e for e in enemies
                         if getattr(getattr(e, "character", e), "is_alive", True)]
        if not alive_enemies:
            return 0.0

        # Cible = ennemi avec le moins de HP
        target      = min(alive_enemies,
                          key=lambda e: getattr(getattr(e, "character", e), "hp", 0))
        target_char = getattr(target, "character", target)

        raw = char.atk * char.attack_multiplier * 2.0
        dmg = self._calc_damage(char, raw)

        target_char.hp -= dmg
        if target_char.hp <= 0:
            target_char.is_alive = False

        # Torment 5 rounds
        apply_debuff(target_char, "torment", duration=5, source=self)

        char.energy += 20

        for w in char.weapon:
            w.on_basic_attack(char, dmg)

        # ── Soin + purification de l'allié le plus bas ────────
        alive_allies = [a for a in allies if a.character.is_alive]
        if alive_allies:
            weakest = min(alive_allies, key=lambda a: a.character.hp)
            wc = weakest.character
            heal = char.atk * 5.0 * getattr(wc, "heal_effect", 1.0)
            wc.hp = min(wc.max_hp, wc.hp + heal)
            # Purification : supprime tous les debuffs (DoT inclus)
            self._purify(wc)

        self._check_last_bastion(allies)
        return dmg

    # ══════════════════════════════════════════════════════════
    #  ULT — RALLY CRY
    # ══════════════════════════════════════════════════════════

    def ult(self, enemies: list, allies: list) -> float:
        """
        Rally Cry :
        - 200% ATK à tous les ennemis vivants.
        - Si toute l'équipe est vivante → ATK +25% 3 rounds.
        - Sinon → soin 1000% ATK réparti sur toute l'équipe.
        """
        char = self.character

        alive_enemies = [e for e in enemies
                         if getattr(getattr(e, "character", e), "is_alive", True)]
        alive_allies  = [a for a in allies if a.character.is_alive]

        total_dmg = 0.0
        for target in alive_enemies:
            target_char = getattr(target, "character", target)
            raw = char.atk * char.attack_multiplier * 2.0
            raw *= (1.0 + char.skill_dmg)
            dmg  = self._calc_damage(char, raw)
            target_char.hp -= dmg
            if target_char.hp <= 0:
                target_char.is_alive = False
            total_dmg += dmg

        # ── Effet conditionnel ────────────────────────────────
        all_alive = all(a.character.is_alive for a in allies)

        if all_alive:
            # ATK +25% à toute l'équipe pendant 3 rounds
            for ally in allies:
                ac = ally.character
                bonus = 0.25 * ac.base_atk
                apply_buff(ac, "rally_atk_zura", duration=3,
                           delta_override=bonus, source=self)
                ac.atk += bonus
        else:
            # Soin 1000% ATK réparti équitablement
            if alive_allies:
                heal_total = char.atk * 10.0
                heal_each  = heal_total / len(alive_allies)
                for ally in alive_allies:
                    ac   = ally.character
                    heal = heal_each * getattr(ac, "heal_effect", 1.0)
                    ac.hp = min(ac.max_hp, ac.hp + heal)

        self._check_last_bastion(allies)
        return total_dmg

    # ══════════════════════════════════════════════════════════
    #  RÉCEPTION DE DÉGÂTS — bouclier Last Bastion
    # ══════════════════════════════════════════════════════════

    def on_hit_received(self, attacker, damage: float, allies: list) -> float:
        """
        Absorbe les dégâts avec le bouclier Last Bastion si actif,
        puis applique les dégâts restants sur les HP.
        """
        char = self.character
        key  = id(self)

        if key in self._shields and self._shields[key] > 0:
            if damage <= self._shields[key]:
                self._shields[key] -= damage
                return 0.0
            else:
                damage -= self._shields[key]
                self._shields[key] = 0

        char.hp -= damage
        self._check_last_bastion(allies)
        return damage

    # ══════════════════════════════════════════════════════════
    #  PASSIVE 3 — Last Bastion
    # ══════════════════════════════════════════════════════════

    def _check_last_bastion(self, allies: list):
        """
        Première fois que HP < 50% :
        - Heal Effect +50% à toute l'équipe 5 rounds.
        - Bouclier 35% Max HP de Zura sur toute l'équipe 3 rounds.
        """
        if self._last_bastion_triggered:
            return
        char = self.character
        if char.hp >= char.max_hp * 0.50:
            return

        self._last_bastion_triggered = True
        shield_value = char.max_hp * 0.35

        for ally in allies:
            ac = ally.character
            if not ac.is_alive:
                continue

            # Heal Effect +50%
            apply_buff(ac, "last_bastion_heal_zura", duration=5,
                       delta_override=0.50, source=self)
            ac.heal_effect = getattr(ac, "heal_effect", 1.0) + 0.50

            # Bouclier : stocké dans _shields (clé = id du fighter)
            # Le moteur doit appeler on_hit_received pour que le bouclier absorbe.
            # Pour les fighters qui n'ont pas ce hook, on applique le bouclier
            # directement comme HP temporaire.
            fid = id(ally)
            self._shields[fid] = shield_value

    # ══════════════════════════════════════════════════════════
    #  HELPERS
    # ══════════════════════════════════════════════════════════

    def _calc_damage(self, char, raw_dmg: float) -> float:
        if random.random() < char.cr:
            raw_dmg *= char.cd
        return max(0.0, raw_dmg)

    def _purify(self, char):
        """Retire tous les debuffs d'un Character et annule leurs effets stat."""
        from debuffs import remove_debuff
        debuff_types = [d["type"] for d in list(char.debuffs)]
        for dtype in debuff_types:
            remove_debuff(char, dtype)
        char.is_stunned = False

    def on_round_end(self, allies: list, round_number: int):
        char = self.character
        for w in char.weapon:
            w.on_round_end(char, allies, round_number)
        for d in char.dragons:
            d.on_round_end(char, allies, round_number)

    def on_ally_die(self, allies: list):
        pass

    def on_self_death(self, allies: list):
        pass