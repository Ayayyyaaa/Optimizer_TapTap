import random
from char import Hero

class Zemus(Hero):
    def __init__(self):
        # Stats de base tirées de ton image
        super().__init__(
            name="Zemus", 
            hp=3121813, 
            attack=79070, 
            armor=1990, 
            speed=1392
        )
        
        # ------------------------------------------------
        # PASSIF 1 : DEATH MACHINE
        # ------------------------------------------------
        self.attack_multiplier += 0.30
        self.crit_chance += 30.0
        self.crit_dmg += 0.50 # +50% Crit Damage
        self.speed += 80
        self.armor_break += 50.0
        
        # Immunité au Curse
        if not hasattr(self, 'immunities'):
            self.immunities = []
        self.immunities.append("Curse")
        
        # Flag pour le Passif 3 (une fois par combat)
        self.reactive_dot_triggered = False

    def _roll_crit(self):
        return random.random() < (self.crit_chance / 100.0)

    # ------------------------------------------------
    # ACTIVE SKILL : NOXIOUS STRIKE
    # ------------------------------------------------
    def use_active_skill(self, enemies, allies):
        # Cible les 2 ennemis avec le moins de HP (Ici le Dummy)
        # Passif 3 : Si un seul ennemi, Zemus attaque deux fois
        targets = sorted(enemies, key=lambda e: e.hp)[:2]
        total_damage = 0
        
        attack_count = 2 if len(enemies) == 1 else 1
        
        for _ in range(attack_count):
            for target in targets:
                # 1. Dégâts : 1000%
                damage = (self.base_attack * self.attack_multiplier) * 10.0
                
                # Bonus Energy Overflow
                overflow = max(0, self.energy - 100)
                damage *= (1.0 + (overflow * 0.005))
                
                if self._roll_crit():
                    damage *= self.crit_dmg
                
                # 2. 75% chance de Curse (400% dmg)
                if random.random() < 0.75:
                    target.active_debuffs.append("Curse")
                
                # 3. Supprime les Heal Over Time (HoT)
                target.active_debuffs = [d for d in target.active_debuffs if d != "HoT"]
                
                total_damage += damage
                
                # Logique de Killing Blow (si la cible meurt)
                if target.hp <= damage:
                    self._on_killing_blow(enemies, allies)

        return total_damage

    # ------------------------------------------------
    # PASSIF 2 : DEFENSE DISINTEGRATION (Attaque Basique)
    # ------------------------------------------------
    def use_basic_attack(self, enemies):
        # Cible l'ennemi avec le plus de Max HP (Le Dummy)
        target = max(enemies, key=lambda e: e.max_hp)
        total_damage = 0
        
        # Passif 3 : Si un seul ennemi, attaque deux fois
        attack_count = 2 if len(enemies) == 1 else 1
        
        for _ in range(attack_count):
            # 1. Dégâts : 200%
            damage = (self.base_attack * self.attack_multiplier) * 2.0
            
            if self._roll_crit():
                damage *= self.crit_dmg
            
            # 2. Réduit Block Chance de 10% pour 5 rounds
            target.block_chance = max(0, getattr(target, 'block_chance', 0) - 10.0)
            
            # Simulation du Block (si l'ennemi bloque)
            enemy_blocks = random.random() < (getattr(target, 'block_chance', 0) / 100.0)
            if enemy_blocks:
                damage *= 0.70 # Réduction de dégâts due au blocage
                target.block_chance = max(0, target.block_chance - 25.0)
                self.hit_chance = getattr(self, 'hit_chance', 0) + 30.0
                
            total_damage += damage
                
        return total_damage

    def _on_killing_blow(self, enemies, allies):
        """Effet déclenché lors d'un coup fatal (Passif 2)"""
        self.purify() # Se purifie
        # Buff 3 alliés aléatoires
        targets = random.sample(allies, min(len(allies), 3))
        for ally in targets:
            ally.armor_break += 25.0
            ally.hit_chance = getattr(ally, 'hit_chance', 0) + 25.0

    # ------------------------------------------------
    # PASSIF 3 : REACTIVE ARMOR (Hooks de fin de round)
    # ------------------------------------------------
    def on_round_end(self, enemies, allies):
        """Logique de fin de round pour les DoT et buffs Cursed"""
        
        # 1. Si Zemus a Bleed/Burn/Poison, renvoie 200% (1 fois par combat)
        dots = ["Bleed", "Burn", "Poison"]
        has_dot = any(d in self.active_debuffs for d in dots)
        
        if has_dot and not self.reactive_dot_triggered:
            self.reactive_dot_triggered = True
            # On simule l'application du DoT à tous les ennemis (non implémenté ici car Dummy)
            pass
            
        # 2. Pour chaque ennemi "Cursed", buff Crit Damage des 2 plus forts alliés
        cursed_count = sum(1 for e in enemies if "Curse" in e.active_debuffs)
        
        if cursed_count > 0:
            # On trie les alliés par attaque
            top_allies = sorted(allies, key=lambda a: a.base_attack * a.attack_multiplier, reverse=True)[:2]
            for ally in top_allies:
                ally.crit_dmg += 0.50 # +50% Crit Damage pour 5 rounds