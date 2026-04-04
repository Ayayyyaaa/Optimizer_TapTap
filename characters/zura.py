import random
from char import Hero

class Zura(Hero):
    def __init__(self):
        super().__init__(
            name="Zura",
            hp=3308267,
            attack=82503,
            armor=1920,
            speed=1307
        )

        # PASSIF 1 : ANCIENT AURA
        self.max_hp = int(self.max_hp * 1.35)
        self.hp = self.max_hp
        self.attack_multiplier += 0.45
        self.crit_chance += 45.0
        self.skill_damage_bonus += 0.20
        self.block_chance += 25.0

        if not hasattr(self, 'immunities'):
            self.immunities = []
        self.immunities += ["Stun", "Petrify", "Silence"]

        self._sphinx_triggered = False

        # FIX: les buffs ATK_Up sont gérés via un compteur propre,
        # pas dans _tick_buffs appelé à chaque take_turn.
        self._atk_up_rounds_left = 0

    # ---- ACTIVE SKILL : SHIFTING SANDS ----
    def use_active_skill(self, enemies, allies):
        total_damage = 0
        for enemy in enemies:
            dmg = (self.base_attack * self.attack_multiplier) * 2.0
            dmg *= (1.0 + self.skill_damage_bonus)
            total_damage += dmg

        if all(ally.hp > 0 for ally in allies):
            # FIX: +25% ATK pendant 3 rounds, géré proprement
            for ally in allies:
                ally.attack_multiplier += 0.25
            self._atk_up_rounds_left = 3
            # Stocke les alliés concernés pour pouvoir retirer le buff
            self._atk_up_targets = allies[:]
        else:
            heal_amount = (self.base_attack * self.attack_multiplier) * 10.0
            for ally in allies:
                ally.hp = min(ally.max_hp, ally.hp + heal_amount)

        return total_damage

    # ---- PASSIF 2 : HIEROGLYPH OF HEALING ----
    def use_basic_attack(self, enemies):
        target = min(enemies, key=lambda e: e.hp)
        dmg = (self.base_attack * self.attack_multiplier) * 2.0
        if "Torment" not in target.active_debuffs:
            target.active_debuffs.append("Torment")
        return dmg

    def _hieroglyph_heal(self, allies):
        if not allies:
            return
        weakest = min(allies, key=lambda a: a.hp)
        heal = (self.base_attack * self.attack_multiplier) * 5.0
        weakest.hp = min(weakest.max_hp, weakest.hp + heal)
        dots_and_debuffs = {"Bleed", "Burn", "Poison", "Torment", "Curse",
                            "Silence", "Sleep", "Stun", "Petrify"}
        weakest.active_debuffs = [
            d for d in weakest.active_debuffs if d not in dots_and_debuffs
        ]

    def take_turn(self, enemies, allies):
        """Surcharge pour injecter le soin passif après l'attaque basique."""
        if "Sleep" in self.active_debuffs:
            return 0

        can_use_skill = self.energy >= 100
        damage_dealt = 0

        if can_use_skill:
            damage_dealt = self.use_active_skill(enemies, allies)
            self.energy = 0
            self.on_after_skill()
        else:
            damage_dealt = self.use_basic_attack(enemies)
            self._hieroglyph_heal(allies)
            self.energy += 50
            for weapon in self.weapons:
                if hasattr(weapon, 'on_basic_attack'):
                    weapon.on_basic_attack(self)

        return damage_dealt

    # ---- PASSIF 3 : SHIELD OF THE SPHINX ----
    def on_round_end(self, enemies, allies):
        """
        FIX: _tick_buffs déplacé ici (fin de round) plutôt que dans take_turn
        pour un timing correct.
        """
        # Expire le buff ATK_Up de Shifting Sands
        if self._atk_up_rounds_left > 0:
            self._atk_up_rounds_left -= 1
            if self._atk_up_rounds_left == 0:
                for ally in getattr(self, '_atk_up_targets', []):
                    ally.attack_multiplier -= 0.25

        # Shield of the Sphinx : déclenché quand Zura passe sous 50% HP
        if not self._sphinx_triggered and self.hp < self.max_hp * 0.50:
            self._sphinx_triggered = True
            shield_value = self.max_hp * 0.35
            for ally in allies:
                ally.hp = min(ally.max_hp, ally.hp + shield_value)
                ally.active_buffs.append(("Zura_HealEffect_Up", 5))