# ═══════════════════════════════════════════════════════════════
#  OKAMI.PY  —  Fighter : Okami
# ═══════════════════════════════════════════════════════════════

import random
from character import Character
from debuffs import apply_debuff, apply_buff, remove_buff, has_buff, tick_buffs
from muta import Mutagen


class Okami:
    def __init__(self):
        # ── Stats de base SANS les passifs ───────────────────
        # BUG FIX : Les bonus de "Lust for Blood" (HP×1.55, CR+0.40, SPD+80)
        # étaient appliqués à l'__init__, ce qui gonflait les stats de base
        # utilisées par les dragons (base_atk, etc.) et s'accumulait si
        # l'instance était réutilisée. Ils sont maintenant dans battle_start().
        self.character = Character(
            name              = "Okami",
            faction           = "Crane",
            hp                = 4_258_154,
            atk               = 52_924,
            defense           = 1_920,
            spd               = 1_296,
            skill_dmg         = 0,
            block             = 0,
            cr                = 0.55,
            cd                = 1.8,
            dmg_reduce        = 0,
            control_resist    = 0,
            hit_chance        = 0,
            armor_break       = 0,
            control_precision = 0,
            stealth           = 0,
            weapon            = [],
            dragons           = [],
            pos               = "back",
            mutagen            = Mutagen(self, "E"),
        )
        self.character.mutagen.apply()
        self.character.mutagen.perk1()
        self.character.mutagen.perk2()
        self.immune   = []
        self.character._immune = self.immune
        self.position = 1

        self._allies_dead = 0

    # ═══════════════════════════════════════════════════════════
    #  BATTLE START — Lust for Blood (P1)
    # ═══════════════════════════════════════════════════════════
    def battle_start(self, allies: list, enemies: list):
        """
        BUG FIX : les bonus de Lust for Blood sont appliqués ici,
        APRÈS que les dragons ont boosté base_atk (ordre correct dans fight.py).
        Ainsi base_atk est déjà gonflé par les dragons quand on applique ×1.55 HP,
        et les bonus ne s'accumulent pas entre simulations.
        """
        char = self.character
        char.max_hp  = int(char.max_hp * 1.55)
        char.hp      = char.max_hp
        char.cr     += 0.40
        char.spd    += 80

    # ═══════════════════════════════════════════════════════════
    #  ATTAQUE DE BASE
    # ═══════════════════════════════════════════════════════════
    def basic_atk(self, enemies: list, allies: list) -> float:
        if not enemies:
            return 0.0

        target      = self._pick_target(enemies)
        target_char = target.character if hasattr(target, "character") else target

        base_damage = self.character.atk * 2.50
        is_crit     = random.random() < min(1.0, self.character.cr)

        if is_crit:
            self.on_crit()
            damage = base_damage * self.character.cd

            # Fresh Meat (P2) : heal 600% ATK on crit basic
            heal = self.character.atk * 6.0
            self.character.hp = min(self.character.max_hp, self.character.hp + heal)

            self.character.energy += 20
        else:
            damage = base_damage

        for w in self.character.weapon:
            damage = w.modify_damage_dealt(self.character, target_char, damage)
            w.on_basic_attack(self.character, damage)

        return damage * self.character.attack_multiplier

    # ═══════════════════════════════════════════════════════════
    #  ULT : Werewolf Form
    # ═══════════════════════════════════════════════════════════
    def ult(self, enemies: list, allies: list) -> float:
        if not enemies:
            return 0.0

        alive_enemies = [e for e in enemies
                         if getattr(e.character if hasattr(e, "character") else e, "is_alive", True)]
        if not alive_enemies:
            return 0.0

        target      = random.choice(alive_enemies)
        target_char = target.character if hasattr(target, "character") else target

        damage = self.character.atk * 15.0
        damage *= (1.0 + self.character.skill_dmg)

        for w in self.character.weapon:
            damage = w.modify_damage_dealt(self.character, target_char, damage)

        # Vol d'ATK : 80% de l'ATK de la cible pendant 4 tours
        stolen_atk = getattr(target_char, "atk", 0) * 0.80
        self._steal_atk(target_char, stolen_atk, duration=4)

        return damage * self.character.attack_multiplier

    # ═══════════════════════════════════════════════════════════
    #  PASSIVE #3 : Last One Standing
    # ═══════════════════════════════════════════════════════════
    def on_ally_die(self, allies: list):
        """
        BUG FIX : ce hook était bien déclaré mais fight.py ne le déclenchait
        jamais car le dummy ne mourrait jamais. Avec combat_engine.py (boss réel),
        le boss attaque et peut tuer des alliés → le hook s'active correctement.
        Aucune correction de code ici, le bug était côté moteur (voir fight.py fix).
        """
        self._allies_dead += 1
        self.character.atk += 0.40 * self.character.base_atk
        self.character.cr  = min(1.0, self.character.cr + 0.40)

    # ═══════════════════════════════════════════════════════════
    #  HELPERS
    # ═══════════════════════════════════════════════════════════
    def on_crit(self):
        pass

    def _pick_target(self, enemies):
        alive = [e for e in enemies
                 if getattr(e.character if hasattr(e, "character") else e, "is_alive", True)]
        if not alive:
            return enemies[0]
        if 1 <= self.position <= 3:
            return max(alive, key=lambda e: getattr(
                e.character if hasattr(e, "character") else e, "atk", 0))
        return min(alive, key=lambda e: getattr(
            e.character if hasattr(e, "character") else e, "hp", 0))

    def _steal_atk(self, target_char, amount: float, duration: int):
        target_char.atk = max(0, target_char.atk - amount)

        buff_key = f"werewolf_steal_{id(self)}_{len(self.character.buffs)}"

        from debuffs import BUFF_DEFS
        BUFF_DEFS[buff_key] = {"stat": "atk", "delta": amount, "mode": "flat"}

        self.character.buffs.append({
            "type":     buff_key,
            "duration": duration,
            "delta":    amount,
            "source":   self,
        })
        self.character.atk += amount