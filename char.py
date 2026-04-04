# Fichier: char.py

class Fighter:
    def __init__(self, name, hp, attack, armor, speed):
        self.name = name
        
        # --- Stats de base ---
        self.max_hp = hp
        self.hp = hp
        self.base_attack = attack
        self.base_armor = armor
        self.speed = speed
        
        # --- Stats Avancées (Par défaut à 0) ---
        self.crit_chance = 0.0
        self.crit_dmg = 1.5 
        self.skill_damage_bonus = 0.0
        self.block_chance = 0.0
        self.armor_break = 0.0
        self.stealth = 0.0
        self.damage_reduce = 0.0
        self.control_resist = 0.0
        self.control_precision = 0.0
        
        # --- Modificateurs en combat ---
        self.attack_multiplier = 1.0
        self.armor_multiplier = 1.0  # <--- VOICI LA LIGNE MANQUANTE À AJOUTER
        self.energy = 50
        self.active_buffs = []
        self.active_debuffs = []
        self.weapons = []

    def purify(self):
        """Retire tous les debuffs (Mécanique très courante)"""
        self.active_debuffs.clear()

class Hero(Fighter):
    def __init__(self, name, hp, attack, armor, speed):
        super().__init__(name, hp, attack, armor, speed)
        
    def take_turn(self, enemies, allies):
        """
        Gère le choix entre Attaque Basique et Compétence.
        Passe la liste des alliés et ennemis pour les ciblages complexes.
        """
        if "Stun" in self.active_debuffs or "Sleep" in self.active_debuffs:
            return 0
            
        can_use_skill = self.energy >= 100 and "Silence" not in self.active_debuffs
        damage_dealt = 0

        if can_use_skill:
            # On appelle la fonction spécifique du héros !
            damage_dealt = self.use_active_skill(enemies, allies)
            self.energy = 0
            
            # --- HOOK : Après avoir lancé un skill ---
            self.on_after_skill()
            
        else:
            damage_dealt = self.use_basic_attack(enemies)
            self.energy += 50
            for weapon in self.weapons:
                if hasattr(weapon, 'on_basic_attack'):
                    weapon.on_basic_attack(self)

        return damage_dealt

    # --- Méthodes à surcharger par chaque personnage ---
    def use_active_skill(self, enemies, allies):
        return 0 # Défini dans la classe du perso

    def use_basic_attack(self, enemies):
        return self.base_attack * self.attack_multiplier # Basique par défaut

    def on_after_skill(self):
        pass # Déclenché juste après le skill


