from char import Hero

class Masamune(Hero):
    def __init__(self):
        super().__init__(
            name="Masamune",
            hp=2996941,
            attack=79622,
            armor=1990,
            speed=1266
        )

        # PASSIF 1 : SAMURAI'S BLADE
        self.attack_multiplier += 0.40
        self.crit_chance += 50.0
        self.speed += 50
        self.armor_break += 65.0
        self.stealth += 65.0

        self.shadowy_revenge_triggered = False

        # FIX: Suivi des buffs temporaires de on_after_skill
        self._meditation_rounds_left = 0

    # ---- ACTIVE SKILL : LAST STAND ----
    def use_active_skill(self, enemies, allies):
        target = enemies[0]
        overflow = max(0, self.energy - 100)
        overflow_bonus = overflow * 0.005

        damage = (self.base_attack * self.attack_multiplier) * 15.0
        damage *= (1.0 + overflow_bonus)

        target.active_debuffs.append("Mark of Death")

        hp_percent = self.hp / self.max_hp
        if hp_percent < 0.50:
            heal_amount = (self.base_attack * self.attack_multiplier) * 15.0
            self.hp = min(self.max_hp, self.hp + heal_amount)
            self.active_buffs.append("Cloak")
        else:
            lowest_hp_ally = min(allies, key=lambda a: a.hp)
            lowest_hp_ally.active_buffs.append("Cloak")
            lowest_hp_ally.armor_multiplier += 0.60

        return damage

    # ---- PASSIF 2 : MOMENT OF MEDITATION ----
    def on_after_skill(self):
        """
        FIX: Les buffs durent 4 rounds, pas en permanence.
        On utilise un compteur pour les appliquer et les retirer proprement.
        """
        # Si un buff précédent est encore actif, on le retire d'abord pour éviter les doublons
        if self._meditation_rounds_left > 0:
            self.attack_multiplier -= 0.40
            self.crit_chance -= 40.0

        # Applique les nouveaux buffs pour 4 rounds
        self.attack_multiplier += 0.40
        self.crit_chance += 40.0
        self._meditation_rounds_left = 4

        self.purify()

        if (self.hp / self.max_hp) > 0.50:
            self.energy += 60

    def on_round_end(self, enemies):
        """FIX: Décrémente le compteur de buff et l'expire si nécessaire."""
        if self._meditation_rounds_left > 0:
            self._meditation_rounds_left -= 1
            if self._meditation_rounds_left == 0:
                self.attack_multiplier -= 0.40
                self.crit_chance -= 40.0

    # ---- PASSIF 3 : SHADOWY REVENGE ----
    def on_ally_death(self, enemies, allies):
        if "Cloak" in self.active_buffs and not self.shadowy_revenge_triggered:
            self.shadowy_revenge_triggered = True
            revenge_damage = (self.base_attack * self.attack_multiplier) * 10.0
            heal_amount = self.max_hp * 0.50
            for ally in allies:
                ally.hp = min(ally.max_hp, ally.hp + heal_amount)
            return revenge_damage * 2
        return 0