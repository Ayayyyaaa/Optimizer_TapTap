# ═══════════════════════════════════════════════════════════════
#  TEEPO.PY  —  Fighter : Teepo
# ═══════════════════════════════════════════════════════════════
#
#  SKILLS :
#
#  [ACTIVE] Rapid Venom :
#    - 650% dmg × 3 sur un ennemi.
#    - Chaque coup : 75% chance d'appliquer Poison (350% ATK dmg, 3 rounds).
#
#  [PASSIVE 1] Line Mastery :
#    - Front-line : HP +75%, Armor +75%.
#    - Back-line  : ATK +75%, Crit Chance +75%.
#    - Immune au Poison.
#
#  [PASSIVE 2] Toxic Retaliation :
#    - Si Teepo est attaqué par un ennemi Poisonné → contre-attaque 350% ATK.
#
#  [PASSIVE 3] Survival Instinct :
#    - Première fois que HP < 50% → DMG Reduce +75% pendant 3 rounds
#                                  + HoT 1250% ATK pendant 3 rounds.
#    - Se déclenche une seule fois par combat.
#
#  Stats de base (image) :
#    HP 5 026 119 | ATK 91 234 | DEF 3 360 | SPD 1 199
#    CR 90% | Skill DMG 0 | Hit Chance 0 | Block 0
#    Crit DMG 0 | Armor Break 0 | DMG Reduce 0
#    Control Resist 0 | Control Precision 0 | Stealth 0
# ═══════════════════════════════════════════════════════════════

import random
from character import Character
from debuffs import apply_debuff, has_debuff, apply_buff


class Teepo:
    """Fighter Teepo."""

    BASE_HP    = 5_026_119
    BASE_ATK   = 91_234
    BASE_DEF   = 3_360
    BASE_SPD   = 1_199
    BASE_CR    = 0.90
    BASE_CD    = 1.50   # valeur par défaut (non visible dans l'image)

    def __init__(self):
        self.character = Character(
            name               = "Teepo",
            faction            = "Howler",  # à ajuster selon le jeu
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

        # Immune au Poison (Line Mastery P1)
        self.character._immune = ["poisoned"]

        # Flags internes
        self._survival_triggered = False   # P3 : une seule fois par combat
        self._hot_stacks         = 0       # tours de HoT restants
        self._hot_value          = 0.0     # montant de soin par tour

    # ══════════════════════════════════════════════════════════
    #  BATTLE START — Line Mastery (P1)
    # ══════════════════════════════════════════════════════════

    def battle_start(self, allies: list, enemies: list):
        char = self.character
        pos  = getattr(char, "position", "front")

        if pos == "front":
            # HP +75%, Armor +75%
            char.max_hp  = int(char.max_hp * 1.75)
            char.hp      = char.max_hp
            char.defense += 0.75 * char.base_defense
        else:
            # ATK +75%, CR +75% (plafonné à 100% dans les rolls)
            char.atk += 0.75 * char.base_atk
            char.cr   = min(1.0, char.cr + 0.75)

    # ══════════════════════════════════════════════════════════
    #  ROUND START — tick HoT (Survival Instinct P3)
    # ══════════════════════════════════════════════════════════

    def on_round_start(self, allies: list):
        if self._hot_stacks > 0:
            char = self.character
            heal = self._hot_value * getattr(char, "heal_effect", 1.0)
            char.hp = min(char.max_hp, char.hp + heal)
            self._hot_stacks -= 1

    # ══════════════════════════════════════════════════════════
    #  ATTAQUE BASIQUE
    # ══════════════════════════════════════════════════════════

    def basic_atk(self, enemies: list, allies: list) -> float:
        char = self.character

        alive_enemies = [e for e in enemies
                         if getattr(getattr(e, "character", e), "is_alive", True)]
        if not alive_enemies:
            return 0.0

        target      = random.choice(alive_enemies)
        target_char = getattr(target, "character", target)

        raw = char.atk * char.attack_multiplier * 2.50
        dmg = self._calc_damage(char, raw)
        if target_char.hp <= 0:
            target_char.is_alive = False

        char.energy += 20

        for w in char.weapon:
            w.on_basic_attack(char, dmg)

        self._check_survival_instinct()
        return dmg

    # ══════════════════════════════════════════════════════════
    #  ULT — RAPID VENOM
    # ══════════════════════════════════════════════════════════

    def ult(self, enemies: list, allies: list) -> float:
        """
        3 coups de 650% sur une même cible.
        Chaque coup : 75% chance de Poison (350% ATK dmg, 3 rounds).
        Les dégâts de Poison passent par modify_dot_damage() des armes
        (compatibilité Weapon_Knife).
        """
        char = self.character

        alive_enemies = [e for e in enemies
                         if getattr(getattr(e, "character", e), "is_alive", True)]
        if not alive_enemies:
            return 0.0

        target      = random.choice(alive_enemies)
        target_char = getattr(target, "character", target)

        total_dmg = 0.0

        for _ in range(3):
            if not target_char.is_alive:
                break

            # 650% ATK amplifié par skill_dmg
            raw = char.atk * char.attack_multiplier * 6.50
            raw *= (1.0 + char.skill_dmg)
            dmg  = self._calc_damage(char, raw)

            total_dmg += dmg

            if target_char.hp <= 0:
                target_char.is_alive = False

            # 75% chance de Poison par coup
            if random.random() < 0.75:
                applied = apply_debuff(target_char, "poisoned", duration=3, source=self, dot_multiplier=3.50)
                if applied:
                    # Dégâts immédiats du Poison (350% ATK)
                    # passent par modify_dot_damage() pour Knife etc.
                    poison_dmg = char.atk * 3.50
                    poison_dmg = self._apply_dot_damage(poison_dmg)
                    total_dmg += poison_dmg
                    if target_char.hp <= 0 and target_char.is_alive:
                        target_char.is_alive = False

        self._check_survival_instinct()
        return total_dmg

    # ══════════════════════════════════════════════════════════
    #  PASSIVE 2 — Toxic Retaliation
    # ══════════════════════════════════════════════════════════

    def on_hit_received(self, attacker, damage: float, allies: list) -> float:
        """
        Appelé par le moteur quand Teepo reçoit un coup.
        Si l'attaquant est Poisonné → contre-attaque 350% ATK.
        """
        char = self.character

        # Applique les dégâts
        char.hp -= damage

        # Contre-attaque si l'attaquant est Poisonné
        attacker_char = getattr(attacker, "character", attacker)
        if has_debuff(attacker_char, "poisoned"):
            counter = char.atk * 3.50 * char.attack_multiplier
            attacker_char.hp -= counter
            if attacker_char.hp <= 0:
                attacker_char.is_alive = False

        self._check_survival_instinct()
        return damage

    # ══════════════════════════════════════════════════════════
    #  PASSIVE 3 — Survival Instinct (vérification continue)
    # ══════════════════════════════════════════════════════════

    def _check_survival_instinct(self):
        """
        Déclenche Survival Instinct la première fois que HP < 50%.
        - DMG Reduce +75% pendant 3 rounds.
        - HoT 1250% ATK par tour pendant 3 rounds.
        """
        if self._survival_triggered:
            return
        char = self.character
        if char.hp < char.max_hp * 0.50:
            self._survival_triggered = True

            # DMG Reduce +75% via buff (retiré automatiquement après 3 rounds)
            apply_buff(char, "survival_dmg_reduce", duration=3,
                       delta_override=0.75, source=self)
            char.dmg_reduce = min(0.90, char.dmg_reduce + 0.75)

            # HoT : stocker pour tick dans on_round_start
            self._hot_stacks = 3
            self._hot_value  = char.atk * 12.50   # 1250% ATK

    def on_round_end(self, allies: list, round_number: int):
        """Callbacks armes / dragons."""
        char = self.character
        for w in char.weapon:
            w.on_round_end(char, allies, round_number)
        for d in char.dragons:
            d.on_round_end(char, allies, round_number)

    def on_ally_die(self, allies: list):
        pass

    def on_self_death(self, allies: list):
        pass

    # ══════════════════════════════════════════════════════════
    #  HELPERS
    # ══════════════════════════════════════════════════════════

    def _calc_damage(self, char, raw_dmg: float) -> float:
        if random.random() < char.cr:
            raw_dmg *= char.cd
        return max(0.0, raw_dmg)

    def _apply_dot_damage(self, base_dmg: float) -> float:
        """Passe les dégâts DoT par modify_dot_damage() des armes (Knife × 3)."""
        dmg = base_dmg
        for w in self.character.weapon:
            if hasattr(w, "modify_dot_damage"):
                dmg = w.modify_dot_damage(self.character, dmg)
        return max(0.0, dmg)