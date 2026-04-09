# ═══════════════════════════════════════════════════════════════
#  SCYTHE.PY  —  Fighter : Scythe
# ═══════════════════════════════════════════════════════════════
#
#  SKILLS :
#
#  [ACTIVE] Reaping Strike :
#    - 2 attaques sur ennemis aléatoires, chacune à 450% dmg.
#    - Si une attaque est un Crit → 2 attaques supplémentaires.
#    - Si une attaque est un Killing Blow → 2 attaques supplémentaires.
#    - Killing Blow : soin self de 40% Max HP + CD et Armor Break +30% (3 rounds).
#    - HP > 50% : Control Resist +50% (3 rounds).
#    - HP < 50% : ATK et Skill Damage +25% (3 rounds).
#    - HP < 25% : ATK et Skill Damage +30% supplémentaires (même durée).
#
#  [PASSIVE 1] Harvester :
#    - ATK +40%, Hit Chance +40%, Crit Damage +35%, SPD +100, Armor Break +50%.
#    - Convertit les dégâts Poison et Curse en soins à 250%.
#    - Immunité aux réductions d'ATK et de SPD.
#
#  [PASSIVE 2] Skullbound Harvest :
#    - Attaque basique → 150% dmg à TOUS les ennemis à 50% HP ou moins
#      + Heal Effect -35% sur la cible pendant 5 rounds.
#    - Si la cible a un Skullbound Seal → ignore l'armure + 200% dmg bonus.
#    - Si AUCUN ennemi n'est à 50% HP ou moins :
#        • Soin self de 60% Max HP
#        • +100 Énergie
#        • Skill Damage +35% (3 rounds)
#        • 25% chance d'appliquer Skullbound Seal à chaque ennemi.
#
#  [PASSIVE 3] Soul Reaper :
#    - Chaque fois que Scythe reçoit des dégâts de Skill : 65% chance d'appliquer
#      Skullbound Seal à l'attaquant.
#    - Lors de son prochain Skill Attack : inflige 400% Curse dmg (5 rounds)
#      à toutes les cibles avec Skullbound Seal + retire le Seal.
#    - À sa mort : 750% dmg à tous les ennemis avec Skullbound Seal.
#    - Si un ennemi avec Skullbound Seal meurt :
#        • Soin self de 50% Max HP
#        • +100 Énergie
#        • Crit Chance +35%, Crit Damage +30% (4 rounds)
# ═══════════════════════════════════════════════════════════════

import random
from character import Character
from debuffs import apply_debuff, has_debuff, apply_buff

class Scythe:
    """Fighter Scythe."""

    BASE_HP    = 2_802_140
    BASE_ATK   = 77_410
    BASE_DEF   = 1_920
    BASE_SPD   = 1_350
    # Stats visibles sur l'image (avant passifs)
    BASE_CR    = 0.15   # Crit Chance : 15
    BASE_CD    = 1.35   # Crit Damage : base 100% + 35% (image)
    BASE_SKILL_DMG   = 0.0
    BASE_HIT_CHANCE  = 0.0   # Hit Chance affichée = 0 avant passif
    BASE_ARMOR_BREAK = 0.50  # Armor Break : 50 (image)

    def __init__(self):
        self.character = Character(
            name              = "Scythe",
            faction           = "Unknown",
            hp                = self.BASE_HP,
            atk               = self.BASE_ATK,
            defense           = self.BASE_DEF,
            spd               = self.BASE_SPD,
            skill_dmg         = self.BASE_SKILL_DMG,
            block             = 0.0,
            cr                = self.BASE_CR,
            cd                = self.BASE_CD,
            dmg_reduce        = 0.0,
            control_resist    = 0.0,
            hit_chance        = self.BASE_HIT_CHANCE,
            armor_break       = self.BASE_ARMOR_BREAK,
            control_precision = 0.0,
            stealth           = False,
            weapon            = [],
            dragons           = [],
            pos               = "front",
        )

        # Immunités Harvester (P1)
        self.character._immune = ["atk_reduce", "spd_reduce"]

        # Suivi Skullbound Seal : set des références ennemis portant le Seal
        self._skullbound_enemies = set()

        # Flag : Scythe a des Seals en attente d'être déclenchés au prochain Skill
        self._soul_reaper_curse_pending = False

        # Référence aux ennemis pour la mort (P3)
        self._last_enemies_ref = []

    # ══════════════════════════════════════════════════════════
    #  BATTLE START — Harvester (P1)
    # ══════════════════════════════════════════════════════════

    def battle_start(self, allies: list, enemies: list):
        char = self.character
        self._last_enemies_ref = enemies

        # Harvester (P1) — bonus de stats permanents
        char.atk         += 0.40 * char.base_atk
        char.hit_chance  += 0.40
        char.cd          += 0.35
        char.spd         += 100
        char.armor_break += 0.50

    # ══════════════════════════════════════════════════════════
    #  ROUND START
    # ══════════════════════════════════════════════════════════

    def on_round_start(self, allies: list):
        pass

    # ══════════════════════════════════════════════════════════
    #  ATTAQUE BASIQUE — Skullbound Harvest (P2)
    # ══════════════════════════════════════════════════════════

    def basic_atk(self, enemies: list, allies: list) -> float:
        char = self.character
        self._last_enemies_ref = enemies

        alive_enemies = [e for e in enemies
                         if getattr(getattr(e, "character", e), "is_alive", True)]
        if not alive_enemies:
            return 0.0

        # Vérifie si au moins un ennemi est à ≤ 50% HP
        low_hp_enemies = [
            e for e in alive_enemies
            if getattr(getattr(e, "character", e), "hp", 1) <=
               getattr(getattr(e, "character", e), "max_hp", 1) * 0.50
        ]

        total_dmg = 0.0

        if low_hp_enemies:
            # 150% dmg à TOUS les ennemis à ≤ 50% HP
            for e in low_hp_enemies:
                e_char = getattr(e, "character", e)
                if not e_char.is_alive:
                    continue

                raw = char.atk * char.attack_multiplier * 1.50
                has_seal = e in self._skullbound_enemies

                # Skullbound Seal → ignore armure + 200% dmg bonus
                if has_seal:
                    raw += char.atk * char.attack_multiplier * 2.00
                    dmg = self._calc_damage(e_char, raw, ignore_armor=True)
                else:
                    dmg = self._calc_damage(e_char, raw)

                e_char.hp -= dmg
                total_dmg += dmg

                # Heal Effect -35% pendant 5 rounds
                apply_debuff(e_char, "heal_reduce", duration=5, source=self)

                if e_char.hp <= 0:
                    e_char.hp       = 0
                    e_char.is_alive = False
                    if e in self._skullbound_enemies:
                        self._on_seal_kill()
                        self._skullbound_enemies.discard(e)
        else:
            # Aucun ennemi à ≤ 50% HP → mode soin/buff
            # Soin self de 60% Max HP
            heal = char.max_hp * 0.60
            char.hp = min(char.max_hp, char.hp + heal)

            # +100 Énergie
            char.energy = min(100, getattr(char, "energy", 0) + 100)

            # Skill Damage +35% (3 rounds)
            apply_buff(char, "skill_dmg_up", duration=3, delta_override=0.35, source=self)

            # 25% chance d'appliquer Skullbound Seal à chaque ennemi
            for e in alive_enemies:
                if random.random() < 0.25:
                    self._apply_skullbound_seal(e)

        char.energy = min(100, getattr(char, "energy", 0) + 20)
        for w in char.weapon:
            w.on_basic_attack(char, total_dmg)

        return total_dmg

    # ══════════════════════════════════════════════════════════
    #  ULT — REAPING STRIKE
    # ══════════════════════════════════════════════════════════

    def ult(self, enemies: list, allies: list) -> float:
        char = self.character
        self._last_enemies_ref = enemies

        alive_enemies = [e for e in enemies
                         if getattr(getattr(e, "character", e), "is_alive", True)]
        if not alive_enemies:
            return 0.0

        # ── Soul Reaper (P3) : déclencher Curse sur les Skullbound Seals ──
        if self._soul_reaper_curse_pending and self._skullbound_enemies:
            self._trigger_soul_reaper_curse(enemies)
            self._soul_reaper_curse_pending = False

        # ── Buffs conditionnels selon HP avant les attaques ──
        hp_ratio = char.hp / char.max_hp
        if hp_ratio > 0.50:
            apply_buff(char, "control_resist_up", duration=3, delta_override=0.50, source=self)
        else:
            apply_buff(char, "atk_up",       duration=3, delta_override=0.25, source=self)
            apply_buff(char, "skill_dmg_up", duration=3, delta_override=0.25, source=self)
            if hp_ratio < 0.25:
                apply_buff(char, "atk_up",       duration=3, delta_override=0.30, source=self)
                apply_buff(char, "skill_dmg_up", duration=3, delta_override=0.30, source=self)

        # ── Attaques principales : 2 de base ──
        total_dmg      = 0.0
        extra_crit     = False   # déjà accordé ce tour ?
        extra_kill     = False   # déjà accordé ce tour ?
        nb_attacks     = 2

        i = 0
        while i < nb_attacks:
            alive_enemies = [e for e in enemies
                             if getattr(getattr(e, "character", e), "is_alive", True)]
            if not alive_enemies:
                break

            target      = random.choice(alive_enemies)
            target_char = getattr(target, "character", target)

            raw      = char.atk * char.attack_multiplier * 4.50
            raw     *= (1.0 + char.skill_dmg)
            is_crit  = random.random() < char.cr
            if is_crit:
                raw *= char.cd

            dmg = self._calc_damage(target_char, raw, bypass_crit=True)
            total_dmg      += dmg

            was_kill = target_char.hp <= 0
            if was_kill:
                target_char.hp       = 0
                target_char.is_alive = False
                if target in self._skullbound_enemies:
                    self._on_seal_kill()
                    self._skullbound_enemies.discard(target)
                # Soin 40% Max HP + CD/Armor Break +30% (3 rounds) au premier KB
                self._on_killing_blow()

            # Extra attaques (une seule série par condition)
            if is_crit and not extra_crit:
                nb_attacks  += 2
                extra_crit   = True

            if was_kill and not extra_kill:
                nb_attacks  += 2
                extra_kill   = True

            i += 1

        return total_dmg

    # ══════════════════════════════════════════════════════════
    #  ON HIT RECEIVED — Soul Reaper (P3)
    # ══════════════════════════════════════════════════════════

    def on_skill_hit_received(self, attacker) -> None:
        """Appelé par le moteur quand Scythe reçoit des dégâts de Skill."""
        if random.random() < 0.65:
            self._apply_skullbound_seal(attacker)
            self._soul_reaper_curse_pending = True

    # ══════════════════════════════════════════════════════════
    #  ON SELF DEATH — Soul Reaper (P3)
    # ══════════════════════════════════════════════════════════

    def on_self_death(self, allies: list):
        """À sa mort : 750% dmg à tous les ennemis avec Skullbound Seal."""
        char = self.character
        for e in list(self._skullbound_enemies):
            e_char = getattr(e, "character", e)
            if not getattr(e_char, "is_alive", False):
                continue
            raw = char.atk * 7.50
            e_char.hp -= raw
            if e_char.hp <= 0:
                e_char.hp       = 0
                e_char.is_alive = False
        self._skullbound_enemies.clear()

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
    #  HELPERS PRIVÉS
    # ══════════════════════════════════════════════════════════

    def _calc_damage(self, target_char, raw_dmg: float,
                     bypass_crit: bool = False,
                     ignore_armor: bool = False) -> float:
        """Calcul dégâts standard."""
        if not bypass_crit and random.random() < self.character.cr:
            raw_dmg *= self.character.cd

        if not ignore_armor:
            defense = getattr(target_char, "defense", 0)
            armor_break_mult = 1.0 - max(
                0.0,
                defense * (1.0 - getattr(self.character, "armor_break", 0.0))
            ) / max(1.0, defense + 1000)
            raw_dmg *= armor_break_mult

        return max(0.0, raw_dmg)

    def _apply_skullbound_seal(self, enemy) -> None:
        """Applique le Skullbound Seal à un ennemi."""
        e_char = getattr(enemy, "character", enemy)
        if getattr(e_char, "is_alive", True):
            apply_debuff(e_char, "skullbound_seal", duration=999, source=self)
            self._skullbound_enemies.add(enemy)

    def _trigger_soul_reaper_curse(self, all_enemies: list) -> None:
        """P3 : 400% Curse dmg (5 rounds) à toutes les cibles avec Skullbound Seal."""
        char = self.character
        curse_base = char.atk * 4.00
        for e in list(self._skullbound_enemies):
            e_char = getattr(e, "character", e)
            if not getattr(e_char, "is_alive", False):
                self._skullbound_enemies.discard(e)
                continue
            apply_debuff(e_char, "cursed", duration=5, source=self, dot_multiplier=4)
            e_char.hp -= curse_base
            if e_char.hp <= 0:
                e_char.hp       = 0
                e_char.is_alive = False
                self._on_seal_kill()
            self._skullbound_enemies.discard(e)

    def _on_killing_blow(self) -> None:
        """Active : soin 40% Max HP + CD et Armor Break +30% (3 rounds)."""
        char = self.character
        heal = char.max_hp * 0.40
        char.hp = min(char.max_hp, char.hp + heal)
        apply_buff(char, "cd_up",          duration=3, delta_override=0.30, source=self)
        apply_buff(char, "armor_break_up", duration=3, delta_override=0.30, source=self)

    def _on_seal_kill(self) -> None:
        """P3 : Un ennemi avec Skullbound Seal meurt → soin + énergie + buffs."""
        char = self.character
        # Soin 50% Max HP
        heal = char.max_hp * 0.50
        char.hp = min(char.max_hp, char.hp + heal)
        # +100 Énergie
        char.energy = min(100, getattr(char, "energy", 0) + 100)
        # Crit Chance +35%, Crit Damage +30% (4 rounds)
        apply_buff(char, "cr_up", duration=4, delta_override=0.35, source=self)
        apply_buff(char, "cd_up", duration=4, delta_override=0.30, source=self)

    # ══════════════════════════════════════════════════════════
    #  HARVESTER (P1) — Conversion Poison/Curse en soin
    # ══════════════════════════════════════════════════════════

    def on_dot_received(self, dot_type: str, dot_dmg: float) -> float:
        """
        Appelé par le moteur lors d'un tick de DoT.
        Si c'est Poison ou Curse → convertit en soin 250%.
        Retourne les dégâts réels (0 si convertis).
        """
        if dot_type in ("poisoned", "cursed"):
            heal = dot_dmg * 2.50
            self.character.hp = min(self.character.max_hp, self.character.hp + heal)
            return 0.0   # Dégâts annulés
        return dot_dmg