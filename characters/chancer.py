import random
from char import Hero

class Chancer(Hero):
    def __init__(self):
        # Stats de base tirées de ton image
        super().__init__(
            name="Chancer", 
            hp=2747196, 
            attack=71881, 
            armor=1920, 
            speed=1250
        )
        
        # ------------------------------------------------
        # PASSIF 1 : FORTUNE'S FAVOR
        # ------------------------------------------------
        self.attack_multiplier += 0.30
        self.crit_chance += 40.0
        self.skill_damage_bonus += 0.30
        self.armor_break += 40.0
        self.crit_dmg += 0.30
        self.block_chance += 20.0
        
        # Immunités aux DoT et contrôles spécifiques
        if not hasattr(self, 'immunities'):
            self.immunities = []
        self.immunities.extend(["Frostbite", "Curse", "Slow"])
        
        # Variables spécifiques à Chancer
        self.dice_roll = 1
        self.is_ascended = True # On assume qu'il est maxé pour l'optimiseur

    def roll_dice(self):
        """Lance le dé de Chancer (1 à 6)"""
        self.dice_roll = random.randint(1, 6)

    def _roll_crit(self):
        return random.random() < (self.crit_chance / 100.0)

    # ------------------------------------------------
    # HOOKS DE DÉBUT DE COMBAT ET DE ROUND
    # ------------------------------------------------
    def on_battle_start(self, enemies, allies):
        """À appeler tout au début du combat dans algo.py"""
        # Passif 3 : Loaded Luck (Ascended)
        if self.is_ascended and random.random() < 0.50:
            self.dice_roll = 6
        else:
            self.roll_dice()
            self.active_buffs.append("Stealth")
            
        # Applique Slow à l'ennemi en face (le Dummy)
        if enemies:
            enemies[0].active_debuffs.append("Slow")
            
        self._check_dice_6(allies)

    def on_round_start(self, enemies=None, allies=None):
        """Relance le dé au début de chaque tour"""
        self.roll_dice()
        self._check_dice_6(allies)

    def _check_dice_6(self, allies):
        """Passif 3 : Si le dé fait 6, buff d'attaque permanent"""
        if self.dice_roll == 6:
            self.attack_multiplier += 0.15
            # Dans un vrai combat de grille, ça bufferait la ligne, ici on se buff soi-même.

    # ------------------------------------------------
    # ACTIVE SKILL : DICE STORM
    # ------------------------------------------------
    def use_active_skill(self, enemies, allies):
        target = enemies[0] 
        self.roll_dice()
        
        # Le nombre de coups est égal au dé puisqu'il n'y a qu'une seule cible (le boss)
        hits = self.dice_roll 
        total_damage = 0
        
        overflow = max(0, self.energy - 100)
        overflow_bonus = overflow * 0.005
        
        # Dégâts de base : 550% (Pair : +100% = 650%)
        base_multiplier = 5.50
        if self.dice_roll % 2 == 0:
            base_multiplier += 1.00
            
        # Passif 1 : +20% dégâts si la cible est full HP
        full_hp_multiplier = 1.20 if target.hp >= target.max_hp else 1.0

        for _ in range(hits):
            hit_dmg = (self.base_attack * self.attack_multiplier) * base_multiplier
            hit_dmg *= (1.0 + self.skill_damage_bonus + overflow_bonus)
            hit_dmg *= full_hp_multiplier
            
            if self._roll_crit():
                hit_dmg *= self.crit_dmg
                
            total_damage += hit_dmg

        # --- EFFETS SECONDAIRES DU SKILL ---
        if self.dice_roll % 2 != 0: # IMPAIR
            self.active_buffs.append("Magic Shield")
            target.active_debuffs.append("Frostbite") # Infligera 350% Frostbite
        else: # PAIR
            target.active_debuffs.append("Curse") # Infligera 350% Curse
            
        if self.dice_roll <= 3:
            target.active_debuffs.append("Chancer_Hit_Chance_Down_30")
        else:
            target.active_debuffs.append("Chancer_Attack_Down_30")

        return total_damage

    # ------------------------------------------------
    # PASSIF 2 : ODD OR EVEN (Attaque Basique)
    # ------------------------------------------------
    def use_basic_attack(self, enemies):
        target = enemies[0]
        self.roll_dice()
        
        # L'attaque basique de Chancer cible 2 ennemis et fait 200%. 
        # Contre notre boss, il fait un hit de 200%.
        base_hit = (self.base_attack * self.attack_multiplier) * 2.0
        
        # Passif 1 : Full HP bonus
        if target.hp >= target.max_hp:
            base_hit *= 1.20
            
        if self._roll_crit():
            base_hit *= self.crit_dmg
            
        # 20% de chance d'appliquer une paralysie aléatoire
        if random.random() < 0.20:
            target.active_debuffs.append("Paralyzed_By_Chancer")
            
        return base_hit

    # ------------------------------------------------
    # PASSIF 1 : MAGIC SHIELD HEAL (Hook utilitaire)
    # ------------------------------------------------
    def on_shield_broken(self):
        """À appeler par le moteur si Chancer se fait taper et perd son Magic Shield"""
        heal_amount = self.max_hp * 0.50
        self.hp = min(self.max_hp, self.hp + heal_amount)