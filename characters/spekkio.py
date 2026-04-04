import random
from char import Hero

class Spekkio(Hero):
    def __init__(self, is_front_line=True):
        # Stats de base tirées de ton image
        super().__init__(
            name="Spekkio", 
            hp=2929509, 
            attack=72514, 
            armor=2884, 
            speed=1173
        )
        
        self.is_front_line = is_front_line
        
        # ------------------------------------------------
        # PASSIF 1 : LOBSTER LOCKDOWN
        # ------------------------------------------------
        self.attack_multiplier += 0.35
        self.armor_multiplier += 0.40
        self.crit_dmg += 0.25 # Attention: Le jeu de base est souvent à 1.5 (150%), ici il passe à 1.75
        self.hit_chance = 50.0 
        self.armor_break += 50.0
        
        # Immunités
        self.immune_stat_reductions = True
        if not hasattr(self, 'immunities'):
            self.immunities = []
        self.immunities.append("Stun")

    def _roll_crit(self, bonus_crit_chance=0.0):
        """Fonction utilitaire pour lancer le dé de coup critique."""
        total_crit_chance = self.crit_chance + bonus_crit_chance
        return random.random() < (total_crit_chance / 100.0)

    def _on_critical_strike(self):
        """Gère le déclenchement de la moitié du Passif 3 (Shell Shockwave)."""
        # 25% de chance d'augmenter les dégâts critiques de 25% de façon permanente
        if random.random() < 0.25:
            self.crit_dmg += 0.25

    # ------------------------------------------------
    # ACTIVE SKILL : WAVE CUTTER
    # ------------------------------------------------
    def use_active_skill(self, enemies, allies):
        target = enemies[0] # Contre le Dummy, c'est la seule cible
        
        # Calcul du nombre de coups
        hits = 3
        # Si tous les alliés sont en vie (+1 hit)
        if all(ally.hp > 0 for ally in allies):
            hits += 1
        # Si l'ennemi est le dernier en vie (+1 hit & +80 Energie)
        if len(enemies) == 1:
            hits += 1
            self.energy += 80
            
        # Condition de PV
        bonus_crit = 0.0
        if (self.hp / self.max_hp) > 0.50:
            bonus_crit = 30.0
        else:
            self.hp = min(self.max_hp, self.hp + (self.max_hp * 0.75))

        total_damage = 0
        overflow = max(0, self.energy - 100)
        overflow_bonus = overflow * 0.005

        # On simule chaque coup indépendamment (car chacun peut crit)
        for _ in range(hits):
            hit_dmg = (self.base_attack * self.attack_multiplier) * 4.0 # 400% par coup
            hit_dmg *= (1.0 + overflow_bonus)
            
            if self._roll_crit(bonus_crit):
                hit_dmg *= self.crit_dmg
                self._on_critical_strike() # Check du passif
                
            total_damage += hit_dmg

        return total_damage

    # ------------------------------------------------
    # PASSIF 2 : CLAW STRIKE (Remplacement de l'attaque basique)
    # ------------------------------------------------
    def use_basic_attack(self, enemies):
        target = enemies[0]
        
        # Dégâts de base à 250% au lieu de 100%
        base_hit = (self.base_attack * self.attack_multiplier) * 2.5 
        
        if self._roll_crit():
            base_hit *= self.crit_dmg
            self._on_critical_strike() # Check du passif
            
            # Bonus spécifique de Claw Strike sur un Crit
            self.energy += 50
            # Simule le debuff appliqué à la cible
            target.active_debuffs.append("Spekkio_Armor_DR_Down") 
            
        return base_hit

    # ------------------------------------------------
    # PASSIF 3 : SHELL SHOCKWAVE (Fin de tour & Kill)
    # ------------------------------------------------
    def on_kill(self, enemies):
        """Hook à appeler si une cible meurt"""
        for enemy in enemies:
            if (enemy.hp / enemy.max_hp) < 0.25:
                enemy.apply_debuff("Stun") # Stun pour 2 rounds

    def on_round_end(self, enemies):
        """Hook à appeler à la fin de chaque round dans algo.py"""
        if self.energy >= 100:
            self.attack_multiplier += 0.10 # +10% Attaque permanent !
            
            for enemy in enemies:
                if (enemy.hp / enemy.max_hp) <= 0.50:
                    # Simule les violents debuffs
                    enemy.active_debuffs.append("Spekkio_Speed_Armor_Block_Down")