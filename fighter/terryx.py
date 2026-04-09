# ═══════════════════════════════════════════════════════════════
#  TERRYX.PY  —  Fighter : Terryx
#  Faction : Finisher (Dino)
# ═══════════════════════════════════════════════════════════════
#
#  SKILLS :
#
#  [ACTIVE] Tri-Strike :
#    - Attaque 1 : 450% dmg à 3 ennemis aléatoires.
#      15% chance d'appliquer Molten Fury (3 rounds) par cible.
#    - Attaque 2 : 500% dmg à 2 ennemis aléatoires.
#      50% chance de Stun chaque cible (2 rounds).
#    - Attaque 3 : 600% dmg à l'ennemi avec le moins de HP.
#      50% chance de réduire Armor et Damage Reduction de 30% (3 rounds).
#    - Après toutes les attaques : +15% ATK par cible touchée (2 rounds).
#
#  [PASSIVE 1] Apex Predator :
#    - HP +40%, ATK +50%, CR +40%, Armor Break +50%, SPD +80.
#    - Immunité à tous les effets DoT.
#    - Immunité à Molten Fury.
#    - +25% ATK par allié Finisher au début du combat (permanent).
#
#  [PASSIVE 2] Dino Strike :
#    - Attaque basique : cible l'ennemi avec le moins de HP, 200% dmg.
#      50% chance d'appliquer Molten Fury (3 rounds).
#    - Si 1 Dino Orb actif : frappe aussi l'ennemi derrière pour 150% dmg.
#    - Si 2 Dino Orbs actifs : 400% dmg total sur la cible principale.
#
#  [PASSIVE 3] Dino Orbs :
#    - Round 1 : Invoque 1 Dino Orb (pas d'attaque).
#    - Round 2+ : Chaque Dino Orb attaque un ennemi aléatoire pour 300% dmg
#      (DoT, ne peut pas crit, ignore les boucliers).
#    - Max 2 orbes. Invocation d'un orbe → soin self de 15% Max HP.
#    - 2 orbes actifs → tous les alliés Finisher gagnent +25% ATK (permanent).
#    - À la mort : revit en Techno Spike avec 100% HP et stats améliorées.
#
#  CORRECTIONS :
#    - Bug 1 : tristrike_atk_up — retire l'ancien buff avant d'en poser un nouveau
#              pour que le 2ème cast soit bien pris en compte.
#    - Bug 2 : Molten Fury n'est plus appliqué sur les cibles déjà mortes.
#    - Bug 3 : on_orb_attack et on_self_death sont appelés par combat_engine
#              (corrections côté moteur).
# ═══════════════════════════════════════════════════════════════

import random
from character import Character
from debuffs import apply_debuff, has_debuff, apply_buff, remove_buff
from muta import Mutagen

class Terryx:
    """Fighter Terryx — Faction Finisher."""

    BASE_HP          = 3_046_890
    BASE_ATK         = 87_364
    BASE_DEF         = 1_920
    BASE_SPD         = 1_355
    BASE_CR          = 0.45
    BASE_CD          = 1.50
    BASE_ARMOR_BREAK = 0.50

    # Stats Techno Spike (revival)
    TECHNO_ATK_BONUS = 0.30
    TECHNO_CD_BONUS  = 0.30

    def __init__(self):
        self.character = Character(
            name              = "Terryx",
            faction           = "Finisher",
            hp                = self.BASE_HP,
            atk               = self.BASE_ATK,
            defense           = self.BASE_DEF,
            spd               = self.BASE_SPD,
            skill_dmg         = 0.0,
            block             = 0.0,
            cr                = self.BASE_CR,
            cd                = self.BASE_CD,
            dmg_reduce        = 0.0,
            control_resist    = 0.0,
            hit_chance        = 0.0,
            armor_break       = self.BASE_ARMOR_BREAK,
            control_precision = 0.0,
            stealth           = False,
            weapon            = [],
            dragons           = [],
            pos               = "front",
            mutagen            = Mutagen(self, "E"),
        )
        self.character.mutagen.apply()
        self.character.mutagen.perk1()
        self.character.mutagen.perk2()
        # Immunités Apex Predator (P1) — tous les DoT + Molten Fury
        self.character._immune = [
            "bleeding", "poisoned", "burning", "burn",
            "frostbite", "cursed", "molten_fury",
        ]

        # Dino Orbs
        self._dino_orbs        = 0
        self._orb_buff_applied = False
        self._round_counter    = 0

        # Revival Techno Spike (une seule fois)
        self._has_revive      = True
        self._is_techno_spike = False

        # Référence ennemis pour les Orbs
        self._last_enemies_ref = []

    # ══════════════════════════════════════════════════════════
    #  BATTLE START — Apex Predator (P1)
    # ══════════════════════════════════════════════════════════

    def battle_start(self, allies: list, enemies: list):
        char = self.character
        self._last_enemies_ref = enemies

        char.max_hp      = int(char.max_hp * 1.40)
        char.hp          = char.max_hp
        char.atk         += 0.50 * char.base_atk
        char.cr          += 0.40
        char.armor_break += 0.50
        char.spd         += 80

        # +25% ATK par allié Finisher (hors Terryx)
        finisher_count = sum(
            1 for a in allies
            if a is not self
            and getattr(getattr(a, "character", a), "faction", "") == "Finisher"
        )
        if finisher_count > 0:
            char.atk += 0.25 * finisher_count * char.base_atk

    # ══════════════════════════════════════════════════════════
    #  ROUND START — Dino Orbs (P3)
    # ══════════════════════════════════════════════════════════

    def on_round_start(self, allies: list):
        self._round_counter += 1

        if self._dino_orbs < 2:
            self._summon_orb(allies)

    # ══════════════════════════════════════════════════════════
    #  DINO ORB ATTACK — appelé par combat_engine (round >= 2)
    # ══════════════════════════════════════════════════════════

    def on_orb_attack(self, enemies: list) -> float:
        """
        Chaque Dino Orb attaque un ennemi aléatoire pour 300% ATK dmg.
        DoT : pas de crit, ignore les boucliers.
        Appelé par combat_engine en début de round si round >= 2.
        """
        if self._round_counter < 2 or self._dino_orbs == 0:
            return 0.0

        char = self.character
        total_dmg = 0.0

        for _ in range(self._dino_orbs):
            alive_enemies = [e for e in enemies
                             if getattr(getattr(e, "character", e), "is_alive", True)]
            if not alive_enemies:
                break
            target = random.choice(alive_enemies)
            t_char = getattr(target, "character", target)

            # DoT, pas de crit, ignore bouclier → appliqué directement sur HP
            raw = char.atk * 3.00
            t_char.hp -= raw
            total_dmg += raw
            if t_char.hp <= 0:
                t_char.hp       = 0
                t_char.is_alive = False

        return total_dmg

    # ══════════════════════════════════════════════════════════
    #  ATTAQUE BASIQUE — Dino Strike (P2)
    # ══════════════════════════════════════════════════════════

    def basic_atk(self, enemies: list, allies: list) -> float:
        char = self.character
        self._last_enemies_ref = enemies

        alive_enemies = [e for e in enemies
                         if getattr(getattr(e, "character", e), "is_alive", True)]
        if not alive_enemies:
            return 0.0

        primary      = min(alive_enemies,
                           key=lambda e: getattr(getattr(e, "character", e), "hp", float("inf")))
        primary_char = getattr(primary, "character", primary)

        total_dmg = 0.0

        mult = 4.00 if self._dino_orbs >= 2 else 2.00
        raw  = char.atk * char.attack_multiplier * mult
        dmg  = self._calc_damage(primary_char, raw)
        primary_char.hp -= dmg
        total_dmg += dmg
        if primary_char.hp <= 0:
            primary_char.hp       = 0
            primary_char.is_alive = False

        # 50% chance Molten Fury — seulement si la cible est encore vivante
        if primary_char.is_alive and random.random() < 0.50:
            apply_debuff(primary_char, "molten_fury", duration=3, source=self)

        # Si exactement 1 orbe : frappe l'ennemi derrière
        if self._dino_orbs == 1:
            behind = self._get_enemy_behind(primary, alive_enemies)
            if behind:
                b_char = getattr(behind, "character", behind)
                raw2   = char.atk * char.attack_multiplier * 1.50
                dmg2   = self._calc_damage(b_char, raw2)
                b_char.hp -= dmg2
                total_dmg += dmg2
                if b_char.hp <= 0:
                    b_char.hp       = 0
                    b_char.is_alive = False

        char.energy = min(100, getattr(char, "energy", 0) + 20)
        for w in char.weapon:
            w.on_basic_attack(char, total_dmg)

        return total_dmg

    # ══════════════════════════════════════════════════════════
    #  ULT — TRI-STRIKE
    # ══════════════════════════════════════════════════════════

    def ult(self, enemies: list, allies: list) -> float:
        char = self.character
        self._last_enemies_ref = enemies
        total_dmg   = 0.0
        targets_hit = set()

        alive_enemies = [e for e in enemies
                         if getattr(getattr(e, "character", e), "is_alive", True)]
        if not alive_enemies:
            return 0.0

        # ── Attaque 1 : 450% × 3 ennemis aléatoires ──────────
        nb1      = min(3, len(alive_enemies))
        targets1 = random.sample(alive_enemies, nb1)
        for t in targets1:
            t_char = getattr(t, "character", t)
            if not t_char.is_alive:
                continue
            raw = char.atk * char.attack_multiplier * 4.50
            raw *= (1.0 + char.skill_dmg)
            dmg = self._calc_damage(t_char, raw)
            t_char.hp -= dmg
            total_dmg += dmg
            targets_hit.add(id(t))
            if t_char.hp <= 0:
                t_char.hp       = 0
                t_char.is_alive = False
            # BUG FIX : Molten Fury uniquement si la cible est vivante
            if t_char.is_alive and random.random() < 0.15:
                apply_debuff(t_char, "molten_fury", duration=3, source=self)

        # ── Attaque 2 : 500% × 2 ennemis aléatoires ──────────
        alive_enemies = [e for e in enemies
                         if getattr(getattr(e, "character", e), "is_alive", True)]
        nb2      = min(2, len(alive_enemies))
        targets2 = random.sample(alive_enemies, nb2) if alive_enemies else []
        for t in targets2:
            t_char = getattr(t, "character", t)
            if not t_char.is_alive:
                continue
            raw = char.atk * char.attack_multiplier * 5.00
            raw *= (1.0 + char.skill_dmg)
            dmg = self._calc_damage(t_char, raw)
            t_char.hp -= dmg
            total_dmg += dmg
            targets_hit.add(id(t))
            if t_char.hp <= 0:
                t_char.hp       = 0
                t_char.is_alive = False
            # Stun uniquement si la cible est vivante
            if t_char.is_alive and random.random() < 0.50:
                apply_debuff(t_char, "stun", duration=2, source=self)

        # ── Attaque 3 : 600% sur l'ennemi avec le moins de HP ─
        alive_enemies = [e for e in enemies
                         if getattr(getattr(e, "character", e), "is_alive", True)]
        if alive_enemies:
            target3 = min(alive_enemies,
                          key=lambda e: getattr(getattr(e, "character", e), "hp", float("inf")))
            t3_char = getattr(target3, "character", target3)
            raw = char.atk * char.attack_multiplier * 6.00
            raw *= (1.0 + char.skill_dmg)
            dmg = self._calc_damage(t3_char, raw)
            t3_char.hp -= dmg
            total_dmg += dmg
            targets_hit.add(id(target3))
            if t3_char.hp <= 0:
                t3_char.hp       = 0
                t3_char.is_alive = False
            # Armor/DR shred uniquement si la cible est vivante
            if t3_char.is_alive and random.random() < 0.50:
                apply_debuff(t3_char, "armor_reduction",  duration=3, source=self)
                apply_debuff(t3_char, "dmg_reduce_shred", duration=3, source=self)

        # ── BUG FIX : +15% ATK par cible touchée (2 rounds) ──
        # Si un buff tristrike_atk_up existe déjà (2ème cast),
        # on retire l'ancien d'abord pour appliquer le nouveau correctement.
        nb_hit = len(targets_hit)
        if nb_hit > 0:
            bonus_delta = 0.15 * nb_hit * char.base_atk
            if any(b["type"] == "tristrike_atk_up" for b in char.buffs):
                remove_buff(char, "tristrike_atk_up")
            apply_buff(char, "tristrike_atk_up", duration=2,
                       delta_override=bonus_delta, source=self)

        return total_dmg

    # ══════════════════════════════════════════════════════════
    #  ON SELF DEATH — Techno Spike (P3)
    # ══════════════════════════════════════════════════════════

    def on_self_death(self, allies: list) -> bool:
        """
        Retourne True si revival déclenché (combat_engine ne tue pas le fighter).
        Retourne False si mort définitive.
        """
        if not self._has_revive:
            return False

        self._has_revive      = False
        self._is_techno_spike = True
        char                  = self.character

        char.hp       = char.max_hp
        char.is_alive = True

        char.debuffs = []
        if hasattr(char, "is_stunned"):
            char.is_stunned = False

        char.atk += self.TECHNO_ATK_BONUS * char.base_atk
        char.cd  += self.TECHNO_CD_BONUS

        return True

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

    # ══════════════════════════════════════════════════════════
    #  HELPERS PRIVÉS
    # ══════════════════════════════════════════════════════════

    def _calc_damage(self, target_char, raw_dmg: float,
                     bypass_crit: bool = False) -> float:
        char = self.character
        if not bypass_crit and random.random() < char.cr:
            raw_dmg *= char.cd
        if has_debuff(target_char, "molten_fury"):
            raw_dmg *= 1.20
        return max(0.0, raw_dmg)

    def _summon_orb(self, allies: list):
        """Invoque 1 Dino Orb (max 2). Soin self + buff alliés si 2 orbes."""
        if self._dino_orbs >= 2:
            return

        self._dino_orbs += 1
        char = self.character

        char.hp = min(char.max_hp, char.hp + char.max_hp * 0.15)

        if self._dino_orbs == 2 and not self._orb_buff_applied:
            self._orb_buff_applied = True
            for ally in allies:
                a_char = getattr(ally, "character", ally)
                if getattr(a_char, "faction", "") == "Finisher" and a_char.is_alive:
                    a_char.atk += 0.25 * getattr(a_char, "base_atk", a_char.atk)

    def _get_enemy_behind(self, primary, alive_enemies: list):
        primary_char = getattr(primary, "character", primary)
        primary_pos  = getattr(primary_char, "position", "front")
        behind_pos   = "back" if primary_pos == "front" else "front"
        candidates   = [e for e in alive_enemies
                        if e is not primary
                        and getattr(getattr(e, "character", e), "position", "front") == behind_pos]
        return random.choice(candidates) if candidates else None