# ═══════════════════════════════════════════════════════════════
#  LEENE.PY  —  Fighter : Leene
#  Faction : Kodiak
# ═══════════════════════════════════════════════════════════════
#
#  SKILLS :
#
#  [ACTIVE] Shadow Raid :
#    - 200% dmg ignorant l'armure à TOUS les ennemis.
#    - 25% chance par cible : vole 25% de l'Armor de la cible
#      et l'ajoute à Leene pendant 2 rounds.
#    - Accorde Cloak à Leene pendant 3 rounds.
#    - Armor Break +45% à tous les alliés de même rangée pendant 5 rounds.
#    - Pour chaque Killing Blow : soigne l'allié avec le moins de HP
#      pour 75% de son Max HP.
#
#  [PASSIVE 1] Shadow Body :
#    - HP +35%, ATK +30%, Control Resist +40%, SPD +100, Stealth +90%.
#    - Immune à Stun.
#
#  [PASSIVE 2] Cloak Tactics :
#    - Sous Cloak : attaque basique → ennemi aléatoire, 200% dmg,
#      vole 80 Energy à la cible.
#    - Si Leene reçoit des dégâts sous Cloak : contre-attaque 250% dmg,
#      25% chance de Stun 2 rounds.
#    - Cloak est perdu si tous les alliés sont morts.
#
#  [PASSIVE 3] Energize :
#    - Fin de round : soigne chaque allié à 100 Energy pour 25% Max HP
#      + Skill DMG +25% pendant 2 rounds.
#    - À la mort de Leene : donne 100 Energy à tous les alliés.
#
#  Stats de base :
#    HP 3 708 715 | ATK 66 747 | DEF 1 920 | SPD 1 316
#    CR 15% | Control Resist 40% | Stealth 90%
# ═══════════════════════════════════════════════════════════════

import random
from character import Character
from debuffs import apply_debuff, apply_buff, remove_buff, has_buff
from muta import Mutagen


class Leene:
    """Fighter Leene — Faction Kodiak."""

    BASE_HP           = 3_708_715
    BASE_ATK          = 66_747
    BASE_DEF          = 1_920
    BASE_SPD          = 1_316
    BASE_CR           = 0.15
    BASE_CD           = 1.50
    BASE_CONTROL_RESIST = 0.40

    def __init__(self):
        self.character = Character(
            name               = "Leene",
            faction            = "Kodiak",
            hp                 = self.BASE_HP,
            atk                = self.BASE_ATK,
            defense            = self.BASE_DEF,
            spd                = self.BASE_SPD,
            skill_dmg          = 0.0,
            block              = 0.0,
            cr                 = self.BASE_CR,
            cd                 = self.BASE_CD,
            dmg_reduce         = 0.0,
            control_resist     = self.BASE_CONTROL_RESIST,
            hit_chance         = 0.0,
            armor_break        = 0.0,
            control_precision  = 0.0,
            stealth            = True,   # Stealth 90 → on représente par True
            weapon             = [],
            dragons            = [],
            pos                = "back",
            mutagen            = Mutagen(self, "E"),  
        )
        self.character.mutagen.apply()
        self.character.mutagen.perk1()
        self.character.mutagen.perk2()


        # Immunités (Shadow Body P1)
        self.character._immune = ["stun"]

        # Cloak state
        self._cloaked         = False
        self._cloak_rounds    = 0

        # Armor steal tracking (pour retirer le buff à expiration)
        self._armor_stolen    = 0.0

        # Death flag (P3 : une seule fois)
        self._death_triggered = False

    # ══════════════════════════════════════════════════════════
    #  BATTLE START — Shadow Body (P1)
    # ══════════════════════════════════════════════════════════

    def battle_start(self, allies: list, enemies: list):
        char = self.character

        char.max_hp          = int(char.max_hp * 1.35)
        char.hp              = char.max_hp
        char.atk             += 0.30 * char.base_atk
        char.control_resist  += 0.40
        char.spd             += 100
        # Stealth +90 est représenté par char.stealth = True (déjà posé)

    # ══════════════════════════════════════════════════════════
    #  ROUND START — tick Cloak
    # ══════════════════════════════════════════════════════════

    def on_round_start(self, allies: list):
        # Cloak se perd si aucun allié vivant (hors Leene)
        if self._cloaked:
            other_alive = any(
                a is not self and a.character.is_alive for a in allies
            )
            if not other_alive:
                self._cloaked     = False
                self._cloak_rounds = 0

    # ══════════════════════════════════════════════════════════
    #  ATTAQUE BASIQUE — Cloak Tactics (P2)
    # ══════════════════════════════════════════════════════════

    def basic_atk(self, enemies: list, allies: list) -> float:
        """
        Sous Cloak : ennemi aléatoire, 200% dmg, vole 80 Energy.
        Hors Cloak : attaque standard 200% dmg sur l'ennemi le moins HP.
        """
        char = self.character

        alive_enemies = [e for e in enemies
                         if getattr(getattr(e, "character", e), "is_alive", True)]
        if not alive_enemies:
            return 0.0

        if self._cloaked:
            target = random.choice(alive_enemies)
        else:
            target = min(alive_enemies,
                         key=lambda e: getattr(getattr(e, "character", e), "hp", float("inf")))

        target_char = getattr(target, "character", target)

        raw = char.atk * char.attack_multiplier * 2.00
        dmg = self._calc_damage(char, raw)
        if target_char.hp <= 0:
            target_char.hp       = 0
            target_char.is_alive = False

        # Vol d'Energy sous Cloak
        if self._cloaked:
            stolen_energy = min(80, getattr(target_char, "energy", 0))
            target_char.energy = getattr(target_char, "energy", 0) - stolen_energy
            char.energy        = min(100, char.energy + stolen_energy)

        char.energy += 20
        for w in char.weapon:
            w.on_basic_attack(char, dmg)

        return dmg

    # ══════════════════════════════════════════════════════════
    #  ULT — SHADOW RAID
    # ══════════════════════════════════════════════════════════

    def ult(self, enemies: list, allies: list) -> float:
        """
        Shadow Raid :
        200% dmg ignorant l'armure à tous les ennemis.
        25% chance par cible : vole 25% Armor pendant 2 rounds.
        Cloak 3 rounds sur Leene.
        Armor Break +45% à tous les alliés de même rangée pendant 5 rounds.
        Killing Blow : soigne l'allié le moins HP pour 75% Max HP.
        """
        char = self.character

        alive_enemies = [e for e in enemies
                         if getattr(getattr(e, "character", e), "is_alive", True)]
        if not alive_enemies:
            return 0.0

        total_dmg    = 0.0
        total_stolen = 0.0

        for target in alive_enemies:
            target_char = getattr(target, "character", target)
            if not target_char.is_alive:
                continue

            # 200% ATK, ignore l'armure (bypass_armor=True via _calc_damage_raw)
            raw = char.atk * char.attack_multiplier * 2.00
            raw *= (1.0 + char.skill_dmg)
            dmg = self._calc_damage(char, raw)

            # Dégâts directs sur HP (ignorant armure → pas de boss.take_damage armor)
            # Le moteur appelle boss.take_damage sur la valeur retournée par ult().
            # Pour vraiment ignorer l'armure il faudrait un flag côté boss,
            # mais on retourne les dégâts bruts ici — à gérer si boss a armor logic.
            total_dmg += dmg

            was_killing_blow = target_char.hp <= 0
            if was_killing_blow:
                target_char.hp       = 0
                target_char.is_alive = False
                self._on_ult_killing_blow(allies)

            # 25% chance : vole 25% de l'Armor de la cible
            if target_char.is_alive and random.random() < 0.25:
                stolen = getattr(target_char, "defense", 0) * 0.25
                target_char.defense = max(0.0, target_char.defense - stolen)
                total_stolen += stolen

        # Applique l'armor volée à Leene (buff 2 rounds, repose si déjà actif)
        if total_stolen > 0:
            if any(b["type"] == "leene_armor_steal" for b in char.buffs):
                remove_buff(char, "leene_armor_steal")
            apply_buff(char, "leene_armor_steal", duration=2,
                       delta_override=total_stolen, source=self)

        # Cloak 3 rounds
        self._cloaked      = True
        self._cloak_rounds = 3

        # Armor Break +45% à tous les alliés de même rangée (5 rounds)
        my_pos = getattr(char, "pos", "back")
        for ally in allies:
            a_char = ally.character
            if not a_char.is_alive:
                continue
            if getattr(a_char, "pos", "back") == my_pos:
                if any(b["type"] == "leene_armorbreak_up" for b in a_char.buffs):
                    remove_buff(a_char, "leene_armorbreak_up")
                apply_buff(a_char, "leene_armorbreak_up", duration=5,
                           delta_override=0.45, source=self)

        return total_dmg

    # ══════════════════════════════════════════════════════════
    #  RÉCEPTION DE DÉGÂTS — Cloak Tactics (P2)
    # ══════════════════════════════════════════════════════════

    def on_hit_received(self, attacker, damage: float, allies: list) -> float:
        """
        Sous Cloak : contre-attaque 250% ATK, 25% chance Stun 2 rounds.
        """
        char = self.character
        char.hp -= damage

        if self._cloaked:
            attacker_char = getattr(attacker, "character", attacker)
            counter = char.atk * 2.50 * char.attack_multiplier
            attacker_char.hp -= counter
            if attacker_char.hp <= 0:
                attacker_char.hp       = 0
                attacker_char.is_alive = False
            if random.random() < 0.25:
                apply_debuff(attacker_char, "stun", duration=2, source=self)

        if char.hp <= 0:
            char.hp = 0

        return damage

    # ══════════════════════════════════════════════════════════
    #  ROUND END — Energize (P3)
    # ══════════════════════════════════════════════════════════

    def on_round_end(self, allies: list, round_number: int):
        char = self.character

        # Tick Cloak
        if self._cloaked:
            self._cloak_rounds -= 1
            if self._cloak_rounds <= 0:
                self._cloaked = False

        # Energize (P3) : soigne les alliés à 100 Energy
        for ally in allies:
            a_char = ally.character
            if not a_char.is_alive:
                continue
            if getattr(a_char, "energy", 0) >= 100:
                heal = a_char.max_hp * 0.25 * getattr(a_char, "heal_effect", 1.0)
                a_char.hp = min(a_char.max_hp, a_char.hp + heal)
                # Skill DMG +25% pendant 2 rounds
                if any(b["type"] == "leene_skill_dmg_up" for b in a_char.buffs):
                    remove_buff(a_char, "leene_skill_dmg_up")
                print(f"Lenne apply skill_dmg a {a_char.name}, cd = {a_char.skill_dmg}")
                apply_buff(a_char, "leene_skill_dmg_up", duration=2,
                           delta_override=0.25, source=self)

        # Callbacks armes / dragons
        for w in char.weapon:
            w.on_round_end(char, allies, round_number)
        for d in char.dragons:
            d.on_round_end(char, allies, round_number)

    # ══════════════════════════════════════════════════════════
    #  MORT — Energize (P3)
    # ══════════════════════════════════════════════════════════

    def on_self_death(self, allies: list) -> bool:
        """À la mort : donne 100 Energy à tous les alliés (une seule fois)."""
        if not self._death_triggered:
            self._death_triggered = True
            for ally in allies:
                if ally is not self and ally.character.is_alive:
                    ally.character.energy = 100
        return False   # pas de revival

    def on_ally_die(self, allies: list):
        # Cloak perdu si plus aucun allié vivant
        if self._cloaked:
            other_alive = any(
                a is not self and a.character.is_alive for a in allies
            )
            if not other_alive:
                self._cloaked      = False
                self._cloak_rounds = 0

    # ══════════════════════════════════════════════════════════
    #  HELPERS
    # ══════════════════════════════════════════════════════════

    def _on_ult_killing_blow(self, allies: list):
        """Soigne l'allié le moins HP pour 75% de son Max HP."""
        char = self.character
        alive_allies = [a for a in allies if a.character.is_alive]
        if not alive_allies:
            return
        weakest = min(alive_allies, key=lambda a: a.character.hp)
        wc   = weakest.character
        heal = wc.max_hp * 0.75 * getattr(wc, "heal_effect", 1.0)
        wc.hp = min(wc.max_hp, wc.hp + heal)

    def _calc_damage(self, char, raw_dmg: float) -> float:
        if random.random() < char.cr:
            raw_dmg *= char.cd
        return max(0.0, raw_dmg)