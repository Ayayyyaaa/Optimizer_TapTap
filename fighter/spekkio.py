# ═══════════════════════════════════════════════════════════════
#  FIGHTER.PY  —  Spekkio
# ═══════════════════════════════════════════════════════════════
#
#  IMPORTANT : basic_atk() et ult() retournent désormais le
#  RAW DAMAGE (avant armor/block/dmg_reduce).
#  C'est combat_engine.py / boss.take_damage() qui applique
#  la formule de dégâts finale.
# ═══════════════════════════════════════════════════════════════

from character import Character
from debuffs import apply_debuff
import random


class Spekkio:
    def __init__(self):
        self.character = Character(
            "Spekkio", "Kodiak",
            2929509,   # hp
            72514,     # atk
            2884,      # defense
            1173,      # spd
            0,         # skill_dmg
            0,         # block
            0.25,      # cr  (125% → plafonné à 100% dans les rolls)
            1.25,         # cd
            1,         # dmg_reduce
            0.5,       # control_resist
            0.15,      # hit_chance  (miss chance)
            0.5,       # armor_break
            0,         # control_precision
            0,         # stealth
            [], [],    # weapon, dragons
            4          # position
        )
        self.immune   = ["atk_reduce", "cr_reduce", "hi_chance_reduce", "stun"]
        self.character._immune = self.immune
        self.position = 4

    # ── Attaque de base ───────────────────────────────────────
    def basic_atk(self, enemies, allies: list) -> float:
        if not enemies:
            return 0.0

        target = self._pick_target(enemies, prefer="lowest_hp")
        target_char = target.character if hasattr(target, "character") else target

        base_damage = self.character.atk * 2.50
        is_crit     = random.random() < min(1.0, self.character.cr)

        if is_crit:
            self.on_crit()
            damage = base_damage * self.character.cd
            self.character.energy += 50

            # Debuffs on crit (armor_break sur la cible)
            apply_debuff(target_char, "armor_break", duration=5, source=self.character)

        else:
            damage = base_damage

        # Passive Shell Shockwave
        self._passif1(enemies)

        # Modificateurs d'armes (raw)
        for w in self.character.weapon:
            damage = w.modify_damage_dealt(self.character, target_char, damage)
            w.on_basic_attack(self.character, damage)

        return damage * self.character.attack_multiplier

    # ── Ultime ───────────────────────────────────────────────
    def ult(self, enemies, allies: list) -> float:
        if not enemies:
            return 0.0

        target      = self._pick_target(enemies, prefer="highest_hp")
        target_char = target.character if hasattr(target, "character") else target

        num_attacks = 3

        if all(a.character.is_alive for a in allies):
            num_attacks += 1

        if len(enemies) == 1:
            num_attacks += 1
            self.character.energy += 80

        bonus_cr = 0.0
        if self.character.hp > self.character.max_hp * 0.5:
            bonus_cr = 0.30
        else:
            heal = self.character.max_hp * 0.75
            self.character.hp = min(self.character.max_hp, self.character.hp + heal)

        total_damage = 0.0
        for _ in range(num_attacks):
            hit_dmg = self.character.atk * 4.00
            hit_dmg *= (1.0 + self.character.skill_dmg)   # BUG FIX : skill_dmg ignoré
            if random.random() < min(1.0, self.character.cr + bonus_cr):
                self.on_crit()
                hit_dmg *= self.character.cd
            total_damage += hit_dmg

        for w in self.character.weapon:
            total_damage = w.modify_damage_dealt(self.character, target_char, total_damage)

        return total_damage * self.character.attack_multiplier

    # ── Passive Shell Shockwave ───────────────────────────────
    def _passif1(self, enemies):
        if self.character.energy >= 100:
            self.character.atk += 0.10 * self.character.base_atk
            for enemy in enemies:
                target_char = enemy.character if hasattr(enemy, "character") else enemy
                if getattr(target_char, "is_alive", True):
                    hp     = getattr(target_char, "hp", 1)
                    max_hp = getattr(target_char, "max_hp", 1)
                    if hp <= max_hp * 0.50:
                        apply_debuff(target_char, "armor_break", duration=5, source=self.character)
                        apply_debuff(target_char, "bleeding",    duration=5, source=self.character)
                        apply_debuff(target_char, "spd_reduce",  duration=5, source=self.character)

    # ── On crit ───────────────────────────────────────────────
    def on_crit(self):
        if random.random() < 0.25:
            self.character.cd += 0.25

    # ── Sélection de cible ───────────────────────────────────
    def _pick_target(self, enemies, prefer="lowest_hp"):
        alive = [e for e in enemies if getattr(
            e.character if hasattr(e, "character") else e, "is_alive", True)]
        if not alive:
            return enemies[0]

        def get_stat(e, stat):
            return getattr(e.character if hasattr(e, "character") else e, stat, 0)

        if 1 <= self.position <= 3:
            return max(alive, key=lambda e: get_stat(e, "atk"))
        elif prefer == "lowest_hp":
            return min(alive, key=lambda e: get_stat(e, "hp"))
        else:
            return max(alive, key=lambda e: get_stat(e, "hp"))