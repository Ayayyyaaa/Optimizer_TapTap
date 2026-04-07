# ═══════════════════════════════════════════════════════════════
#  CHANCER.PY  —  Fighter : Chancer
#  Faction : Crane
# ═══════════════════════════════════════════════════════════════
#
#  SKILLS :
#
#  [PASSIVE 1] Fortune's Favor
#    - ATK +30%, CR +40%, Skill DMG +30%, Armor Break +40%, CD +30%, Block +20%
#    - +5% Skill DMG & DMG Reduce per Crane ally
#    - +20% damage vs enemies at full HP
#    - Immune to Frostbite, Curse, Slow
#    - Whenever a Magic Shield is broken → heal 50% max HP
#
#  [PASSIVE 2] Odd or Even
#    - Dice Roll ODD  → attaques sur Chancer ont 20% de chance de rater
#    - Dice Roll EVEN → 25% chance de contre-attaque (200% dmg, vol 40 energy)
#    - Attaque basic cible les 2 ennemis avec le plus de SPD,
#      200% dmg, 20% chance de paralyze 2 rounds
#
#  [PASSIVE 3] Loaded Luck
#    - Début de combat : 100% chance d'appliquer Slow à l'ennemi en face pendant 2 rounds
#    - Dice Roll = 6 → Chancer + alliés de la même rangée gagnent +15% ATK
#    - À la mort : si Dice Roll = 6 → revit avec HP/Energy pleins
#                  sinon → cast Silence sur (Dice Roll) ennemis pendant 2 rounds
#    - Chaque effet de mort ne se déclenche qu'une fois par combat
#    - Si Ascended : 50% chance de commencer en Stealth 2 rounds, sinon commence avec Dice Roll = 6
#
#  [ACTIVE] Dice Storm
#    - Inflige 550% dmg à un nombre aléatoire d'ennemis basé sur le Dice Roll
#    - Si un seul ennemi reste, le Dice Roll = nombre d'attaques et de malédictions sur cette cible sur cette cible
#    - Dice Roll ODD  → 100% chance de Magic Shield 2 rounds + 350% Frostbite dmg 3 rounds
#    - Dice Roll EVEN → +100% dmg supplémentaire + 350% Curse dmg 3 rounds
#    - Dice Roll ≤ 3  → réduit Hit Chance front line de 30% pendant 2 rounds
#    - Dice Roll > 3  → réduit ATK back line de 30% pendant 2 rounds
#
#  NOTE KNIFE :
#    Les dégâts de Frostbite (ODD) et de Curse (EVEN) sont des dégâts
#    de type "debuff damage". Ils passent par _apply_debuff_damage() qui
#    appelle modify_dot_damage() sur chaque arme du porteur.
#    Weapon_Knife multiplie donc ces dégâts par ×3 automatiquement.
#
#  Dice Roll : valeur 1–6, re-tirée au début de chaque round et à la revival.
# ═══════════════════════════════════════════════════════════════

import random
from character import Character
from debuffs import apply_debuff, has_debuff, apply_buff


class Chancer:
    """Fighter Chancer — Faction Crane."""

    BASE_HP          = 2_747_196
    BASE_ATK         = 71_881
    BASE_DEF         = 1_920
    BASE_SPD         = 1_250
    BASE_CR          = 0.55
    BASE_CD          = 1.30
    BASE_SKILL_DMG   = 0.35
    BASE_BLOCK       = 0.20
    BASE_ARMOR_BREAK = 0.40
    BASE_DMG_REDUCE  = 0.05

    def __init__(self):
        self.character = Character(
            name               = "Chancer",
            faction            = "Crane",
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
            armor_break        = self.BASE_ARMOR_BREAK,
            control_precision  = 0.0,
            stealth            = False,
            weapon             = [],
            dragons            = [],
            pos                = "back",
        )

        self._dice_roll           = 1
        self._death_triggered     = False
        self._magic_shield_active = False
        self._magic_shield_duration = 0
        self._is_ascended         = False

        # Immunités (Fortune's Favor)
        self.character._immune = ["frostbite", "cursed", "spd_reduce"]

    # ══════════════════════════════════════════════════════════
    #  BATTLE START
    # ══════════════════════════════════════════════════════════

    def battle_start(self, allies: list, enemies: list):
        char = self.character

        self._roll_dice()

        # ── Fortune's Favor (P1) ──────────────────────────────
        char.atk         += 0.30 * char.base_atk
        char.cr          += 0.40
        char.skill_dmg   += 0.30
        char.armor_break += 0.40
        char.cd          += 0.30
        char.block       += 0.20

        crane_allies = [a for a in allies
                        if a is not self and a.character.faction == "Crane"]
        bonus = len(crane_allies) * 0.05
        char.skill_dmg  += bonus
        char.dmg_reduce += bonus

        # ── Loaded Luck (P3) — Slow sur l'ennemi en face ──────
        if enemies:
            apply_debuff(getattr(enemies[0], "character", enemies[0]),
                         "spd_reduce", duration=2, source=self)

        # ── Ascension ─────────────────────────────────────────
        if self._is_ascended:
            if random.random() < 0.50:
                char.stealth    = True
                self._stealth_rounds = 2
            else:
                self._dice_roll = 6

        # Dice Roll = 6 → +15% ATK Chancer + alliés même rangée
        if self._dice_roll == 6:
            self._apply_dice6_atk_bonus(allies)

    # ══════════════════════════════════════════════════════════
    #  ROUND START
    # ══════════════════════════════════════════════════════════

    def on_round_start(self, allies: list):
        char = self.character

        old_dice = self._dice_roll
        if old_dice == 6:
            self._remove_dice6_atk_bonus(allies)

        self._roll_dice()

        if self._dice_roll == 6:
            self._apply_dice6_atk_bonus(allies)

        if char.stealth and hasattr(self, "_stealth_rounds"):
            self._stealth_rounds -= 1
            if self._stealth_rounds <= 0:
                char.stealth = False

        # Décompte Magic Shield
        if self._magic_shield_active:
            self._magic_shield_duration -= 1
            if self._magic_shield_duration <= 0:
                self._magic_shield_active = False

    # ══════════════════════════════════════════════════════════
    #  ATTAQUE BASIQUE
    # ══════════════════════════════════════════════════════════

    def basic_atk(self, enemies: list, allies: list) -> float:
        """
        Odd or Even (P2) :
        Cible les 2 ennemis avec le plus de SPD, 200% ATK,
        20% chance de paralyze 2 rounds.
        """
        char = self.character

        alive_enemies = [e for e in enemies
                         if getattr(getattr(e, "character", e), "is_alive", True)]
        if not alive_enemies:
            return 0.0

        targets = sorted(alive_enemies,
                         key=lambda e: getattr(getattr(e, "character", e), "spd", 0),
                         reverse=True)[:2]

        total_dmg = 0.0
        for target in targets:
            target_char = getattr(target, "character", target)
            raw = char.atk * char.attack_multiplier * 2.0
            dmg = self._calc_damage(char, target_char, raw, is_skill=False)
            target_char.hp -= dmg
            if target_char.hp <= 0:
                target_char.is_alive = False
            total_dmg += dmg

            for w in char.weapon:
                dmg += w.modify_damage_dealt(char, target_char, dmg)
                w.on_basic_attack(char, dmg)

            if random.random() < 0.20:
                apply_debuff(target_char, "stun", duration=2, source=self)

        char.energy += 20
        return total_dmg

    # ══════════════════════════════════════════════════════════
    #  ULT — DICE STORM
    # ══════════════════════════════════════════════════════════

    def ult(self, enemies: list, allies: list) -> float:
        """
        Dice Storm.
        Les dégâts Frostbite et Curse passent par _apply_debuff_damage()
        afin que Weapon_Knife (et toute arme avec modify_dot_damage) les amplifie.
        """
        char = self.character
        alive_enemies = [e for e in enemies
                         if getattr(getattr(e, "character", e), "is_alive", True)]
        if not alive_enemies:
            return 0.0

        dice    = self._dice_roll
        is_odd  = (dice % 2 == 1)
        is_even = (dice % 2 == 0)

        # ── Sélection des cibles ──────────────────────────────
        if len(alive_enemies) == 1:
            targets = [alive_enemies[0]] * dice
        else:
            nb_targets = min(dice, len(alive_enemies))
            targets = random.sample(alive_enemies, nb_targets)

        # ── Dégâts principaux (550% ou 650% si even) ──────────
        base_mult = 5.50 + (1.00 if is_even else 0.0)

        total_dmg = 0.0
        for target in targets:
            target_char = getattr(target, "character", target)
            raw = char.atk * char.attack_multiplier * base_mult
            raw *= (1.0 + char.skill_dmg)
            dmg  = self._calc_damage(char, target_char, raw, is_skill=True)
            target_char.hp -= dmg
            if target_char.hp <= 0:
                target_char.is_alive = False
            for w in char.weapon:
                dmg = w.modify_damage_dealt(char, target_char, dmg)
            total_dmg += dmg

        # ── Effets selon parité ───────────────────────────────
        if is_odd:
            # Magic Shield 2 rounds
            self._magic_shield_active   = True
            self._magic_shield_duration = 2

            # Frostbite 350% ATK — passe par _apply_debuff_damage
            base_frostbite = char.atk * 3.50
            for target in targets: # <--- CORRIGÉ : On itère sur le nombre de coups !
                target_char = getattr(target, "character", target)
                apply_debuff(target_char, "frostbite", duration=3, source=self,dot_multiplier=3.50)
                dmg = self._apply_debuff_damage(base_frostbite, target_char)
                target_char.hp -= dmg
                if target_char.hp <= 0:
                    target_char.is_alive = False
                total_dmg += dmg

        if is_even:
            # Curse 350% ATK — passe par _apply_debuff_damage
            base_curse = char.atk * 3.50
            for target in targets: # <--- CORRIGÉ : On itère sur le nombre de coups !
                target_char = getattr(target, "character", target)
                apply_debuff(target_char, "cursed", duration=3, source=self,dot_multiplier=3.50)
                dmg = self._apply_debuff_damage(base_curse, target_char)
                target_char.hp -= dmg
                if target_char.hp <= 0:
                    target_char.is_alive = False
                total_dmg += dmg

        # ── Effets selon valeur du dé ─────────────────────────
        if dice <= 3:
            front_enemies = [e for e in alive_enemies
                             if getattr(getattr(e, "character", e), "position", "front") == "front"]
            for e in front_enemies:
                apply_debuff(getattr(e, "character", e), "taunted", duration=2, source=self)
        else:
            back_enemies = [e for e in alive_enemies
                            if getattr(getattr(e, "character", e), "position", "back") == "back"]
            for e in back_enemies:
                apply_debuff(getattr(e, "character", e), "atk_reduce", duration=2, source=self)

        return total_dmg

    # ══════════════════════════════════════════════════════════
    #  RÉCEPTION DE DÉGÂTS / MORT
    # ══════════════════════════════════════════════════════════

    def on_hit_received(self, attacker, damage: float, allies: list) -> float:
        """
        Appelé par le moteur quand Chancer reçoit un coup.
        - Dice ODD  → 20% chance de miss total
        - Magic Shield → absorbe, soigne 50% max HP (Fortune's Favor)
        - Dice EVEN → 25% contre-attaque 200% + vol 40 energy
        """
        char = self.character

        # ODD : 20% miss
        if self._dice_roll % 2 == 1:
            if random.random() < 0.20:
                return 0.0

        # Magic Shield
        if self._magic_shield_active:
            self._magic_shield_active   = False
            self._magic_shield_duration = 0
            char.hp = min(char.max_hp, char.hp + char.max_hp * 0.50)
            return 0.0

        # Dégâts réels
        char.hp -= damage

        # EVEN : 25% contre-attaque
        if self._dice_roll % 2 == 0 and random.random() < 0.25:
            attacker_char = getattr(attacker, "character", attacker)
            attacker_char.hp -= char.atk * 2.0
            stolen = min(40, getattr(attacker_char, "energy", 0))
            attacker_char.energy = getattr(attacker_char, "energy", 0) - stolen
            char.energy += stolen

        if char.hp <= 0:
            self._on_death(allies)

        return damage

    def _on_death(self, allies: list):
        """Loaded Luck — effet à la mort (une seule fois)."""
        if self._death_triggered:
            return
        self._death_triggered = True
        char = self.character

        if self._dice_roll == 6:
            char.hp       = char.max_hp
            char.energy   = 100
            char.is_alive = True
            self._roll_dice()
        # Sinon : Silence sur (dice) ennemis — nécessite accès aux ennemis,
        # à implémenter côté moteur si besoin.

    def on_self_death(self, allies: list):
        """Hook moteur — délègue à _on_death."""
        self._on_death(allies)

    def on_ally_die(self, allies: list):
        pass

    # ══════════════════════════════════════════════════════════
    #  HELPERS PRIVÉS
    # ══════════════════════════════════════════════════════════

    def _apply_debuff_damage(self, base_dmg: float, target_char) -> float:
        """
        Applique les dégâts de type "debuff" (Frostbite, Curse, etc.)
        en passant par modify_dot_damage() de chaque arme du porteur.

        C'est ce qui permet à Weapon_Knife de tripler ces dégâts.
        D'autres armes futures peuvent aussi implémenter modify_dot_damage.
        """
        dmg = base_dmg
        for w in self.character.weapon:
            if hasattr(w, "modify_dot_damage"):
                dmg = w.modify_dot_damage(self.character, dmg)
        return max(0.0, dmg)

    def _roll_dice(self):
        self._dice_roll = random.randint(1, 6)

    def _calc_damage(self, char, target_char, raw_dmg: float, is_skill: bool) -> float:
        """Calcul dégâts avec crit et bonus vs ennemi à pleine vie."""
        if random.random() < char.cr:
            raw_dmg *= char.cd
        # Fortune's Favor : +20% vs ennemi à pleine vie
        if target_char.hp >= target_char.max_hp:
            raw_dmg *= 1.20
        return max(0.0, raw_dmg)

    def _apply_dice6_atk_bonus(self, allies: list):
        char = self.character
        char.atk += 0.15 * char.base_atk
        self._dice6_bonus_allies = []
        my_pos = getattr(char, "position", "front")
        for ally in allies:
            if ally is not self and getattr(ally.character, "position", None) == my_pos:
                ally.character.atk += 0.15 * ally.character.base_atk
                self._dice6_bonus_allies.append(ally)

    def _remove_dice6_atk_bonus(self, allies: list):
        char = self.character
        char.atk -= 0.15 * char.base_atk
        for ally in getattr(self, "_dice6_bonus_allies", []):
            if ally.character.is_alive:
                ally.character.atk -= 0.15 * ally.character.base_atk
        self._dice6_bonus_allies = []