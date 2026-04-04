# ═══════════════════════════════════════════════════════════════
#  LAGUNA.PY  —  Fighter : Laguna
# ═══════════════════════════════════════════════════════════════
#
#  HOOKS UTILISÉS PAR LE MOTEUR (fight.py corrigé) :
#    - battle_start(allies, enemies)   → appelé après armes/dragons
#    - on_round_start(allies)          → appelé après armes/dragons
#    - on_round_end(allies, round_num) → appelé après armes/dragons
#    - on_ally_die(allies)             → appelé quand un allié meurt
#    - on_self_death(allies)           → appelé quand Laguna meurt
#    - basic_atk(enemies, allies)      → attaque basique
#    - ult(enemies, allies)            → compétence active
#
#  POSITION :
#    fight.py assigne automatiquement character.position = "front"
#    pour les slots 0-2 et "back" pour les slots 3-5.
#    Laguna filtre ses buffs de rangée sur cette valeur.
#
#  SKILLS :
#    [P1] Strength of the Sea : HP +40%, ATK +30%, DEF +45%, SPD +100
#                               Immune à tous les effets Paralyze
#    [P2] Octo Aid : sur mort d'allié → soin 1200% ATK sur allié à + bas HP
#                                        + 25% DMG Reduce 3 tours
#                    sur mort de Laguna → Bubble Mark sur allié à + bas HP
#    [P3] Paralyzing Odds : skill → 45% chance paralyze 2 tours par cible
#                           battle start → alliés même rangée +25% ATK, +35% Heal Effect
#    [A]  Bon Voyage! : 350% dmg tous ennemis back-line + Skill Dmg -35% 4 tours
#                       Si front : +30% DMG Reduce alliés front 4 tours
#                       Si back  : +50% Skill Damage alliés back 4 tours
#                       Soins alliés même rangée 500% ATK
# ═══════════════════════════════════════════════════════════════

import random
from character import Character
from debuffs import apply_debuff, apply_buff, has_buff, tick_buffs


PARALYZE_TYPES = ["stun", "frozen"]   # types de paralyze disponibles dans debuffs.py


class Laguna:
    """Fighter Laguna."""

    BASE_HP    = 3_846_074
    BASE_ATK   = 65_720
    BASE_DEF   = 2_784
    BASE_SPD   = 1_290
    BASE_CR    = 0.15
    BASE_CD    = 1.50

    def __init__(self):
        self.character = Character(
            name               = "Laguna",
            faction            = "Crane",
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
            pos                = "back",   # ecrase par fight.py selon le slot
        )

        # Immunites Paralyze (Strength of the Sea)
        self.character._immune = ["stun", "frozen", "paralyze"]

        # Etat interne
        self._death_triggered = False
        self._bubble_marks: dict = {}   # id(fighter) -> {fighter, active, duration}

    # ══════════════════════════════════════════════════════════
    #  BATTLE START — appele par fight.py apres armes/dragons
    # ══════════════════════════════════════════════════════════

    def battle_start(self, allies: list, enemies: list):
        char = self.character

        # ── Strength of the Sea (P1) ──────────────────────────
        char.max_hp   = int(char.max_hp * 1.40)
        char.hp       = char.max_hp
        char.atk     += 0.30 * char.base_atk
        char.defense += 0.45 * char.base_defense
        char.spd     += 100

        # ── Paralyzing Odds (P3) — buffs de rangee ────────────
        # position est assignee par fight.py avant cet appel
        my_pos = getattr(char, "position", "front")
        same_row = [
            a for a in allies
            if a is not self
            and getattr(a.character, "position", "front") == my_pos
        ]
        for ally in same_row:
            ally.character.atk += 0.25 * ally.character.base_atk
            ally.character.heal_effect = getattr(ally.character, "heal_effect", 1.0) + 0.35

    # ══════════════════════════════════════════════════════════
    #  ROUND START
    # ══════════════════════════════════════════════════════════

    def on_round_start(self, allies: list):
        self._tick_bubble_marks(allies)

    # ══════════════════════════════════════════════════════════
    #  ATTAQUE BASIQUE
    # ══════════════════════════════════════════════════════════

    def basic_atk(self, enemies: list, allies: list) -> float:
        char  = self.character
        alive = [e for e in enemies if getattr(getattr(e, "character", e), "is_alive", True)]
        if not alive:
            return 0.0

        target      = random.choice(alive)
        target_char = getattr(target, "character", target)

        raw = char.atk * char.attack_multiplier
        dmg = self._calc_damage(char, raw, is_skill=False)

        target_char.hp -= dmg
        if target_char.hp <= 0:
            target_char.is_alive = False

        char.energy += 20

        for w in char.weapon:
            w.on_basic_attack(char, dmg)

        return dmg

    # ══════════════════════════════════════════════════════════
    #  ULT — BON VOYAGE!
    # ══════════════════════════════════════════════════════════

    def ult(self, enemies: list, allies: list) -> float:
        char   = self.character
        my_pos = getattr(char, "position", "front")

        # ── Cibles : ennemis en back-line ─────────────────────
        # Si le moteur ne distingue pas les positions ennemies (boss unique),
        # on cible tous les ennemis vivants.
        alive_enemies = [e for e in enemies
                         if getattr(getattr(e, "character", e), "is_alive", True)]
        back_enemies  = [e for e in alive_enemies
                         if getattr(getattr(e, "character", e), "position", "back") == "back"]
        targets = back_enemies if back_enemies else alive_enemies

        total_dmg = 0.0
        for target in targets:
            target_char = getattr(target, "character", target)

            raw = char.atk * char.attack_multiplier * 3.50   # 350%
            raw *= (1.0 + char.skill_dmg)
            dmg  = self._calc_damage(char, raw, is_skill=True)

            target_char.hp -= dmg
            if target_char.hp <= 0:
                target_char.is_alive = False
            total_dmg += dmg

            # Skill Damage -35% sur la cible 4 tours (proxy atk_reduce)
            apply_debuff(target_char, "atk_reduce", duration=4, source=self)

            # Paralyzing Odds (P3) : 45% chance paralyze 2 tours
            if random.random() < 0.45:
                apply_debuff(target_char, random.choice(PARALYZE_TYPES),
                             duration=2, source=self)

        # ── Effet selon position de Laguna ────────────────────
        alive_allies    = [a for a in allies if a is not self and a.character.is_alive]
        same_row_allies = [a for a in alive_allies
                           if getattr(a.character, "position", "front") == my_pos]

        if my_pos == "front":
            for ally in same_row_allies:
                ac = ally.character
                if not has_buff(ac, "dmg_reduce_laguna"):
                    apply_buff(ac, "dmg_reduce_laguna", duration=4,
                               delta_override=0.30, source=self)
                    ac.dmg_reduce += 0.30
        else:
            for ally in same_row_allies:
                ac = ally.character
                if not has_buff(ac, "skill_dmg_laguna"):
                    apply_buff(ac, "skill_dmg_laguna", duration=4,
                               delta_override=0.50, source=self)
                    ac.skill_dmg += 0.50

        # ── Soins alliés meme rangee (500% ATK) ───────────────
        healable = [a for a in allies
                    if a.character.is_alive
                    and getattr(a.character, "position", "front") == my_pos]
        heal_base = char.atk * 5.00
        for ally in healable:
            ac   = ally.character
            heal = heal_base * getattr(ac, "heal_effect", 1.0)
            ac.hp = min(ac.max_hp, ac.hp + heal)

        return total_dmg

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
    #  CALLBACKS MORTS
    # ══════════════════════════════════════════════════════════

    def on_ally_die(self, allies: list):
        """Octo Aid (P2) : soigne l'allié avec le moins de HP."""
        char = self.character
        alive_allies = [a for a in allies if a is not self and a.character.is_alive]
        if not alive_allies:
            return

        target = min(alive_allies, key=lambda a: a.character.hp)
        tc     = target.character

        heal = char.atk * 12.00 * getattr(tc, "heal_effect", 1.0)
        tc.hp = min(tc.max_hp, tc.hp + heal)

        if not has_buff(tc, "dmg_reduce_octo"):
            apply_buff(tc, "dmg_reduce_octo", duration=3,
                       delta_override=0.25, source=self)
            tc.dmg_reduce += 0.25

    def on_self_death(self, allies: list):
        """Octo Aid (P2) : Bubble Mark sur l'allié avec le moins de HP (une fois)."""
        if self._death_triggered:
            return
        self._death_triggered = True

        alive_allies = [a for a in allies if a is not self and a.character.is_alive]
        if not alive_allies:
            return

        target = min(alive_allies, key=lambda a: a.character.hp)
        self._bubble_marks[id(target)] = {
            "fighter":  target,
            "active":   False,
            "duration": 0,
        }
        target._has_bubble_mark    = True
        target._bubble_mark_source = self

    def trigger_bubble_mark(self, fighter, allies: list):
        """
        Appelé par le moteur quand le fighter balisé allait subir des dégâts fataux.
        Le fighter reste à 1 HP, immune 1 round, puis soins 50% max HP.
        """
        mark = self._bubble_marks.get(id(fighter))
        if mark is None or mark["active"]:
            return
        mark["active"]   = True
        mark["duration"] = 1
        fighter.character.hp = 1
        fighter._bubble_active = True

    def _tick_bubble_marks(self, allies: list):
        """Decrémente les bubbles et soigne a l'expiration."""
        to_remove = []
        for key, mark in self._bubble_marks.items():
            if not mark["active"]:
                continue
            mark["duration"] -= 1
            if mark["duration"] <= 0:
                f  = mark["fighter"]
                f._bubble_active = False
                heal = f.character.max_hp * 0.50 * getattr(f.character, "heal_effect", 1.0)
                f.character.hp = min(f.character.max_hp, f.character.hp + heal)
                to_remove.append(key)
        for key in to_remove:
            del self._bubble_marks[key]

    # ══════════════════════════════════════════════════════════
    #  HELPER
    # ══════════════════════════════════════════════════════════

    def _calc_damage(self, char, raw_dmg: float, is_skill: bool) -> float:
        if random.random() < char.cr:
            raw_dmg *= char.cd
        return max(0.0, raw_dmg)