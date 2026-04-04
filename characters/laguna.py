import random
from char import Hero

class Laguna(Hero):
    def __init__(self, is_front_line=False):
        # Stats de base tirées de ton image
        super().__init__(
            name="Laguna", 
            hp=3846074, 
            attack=65720, 
            armor=2784, 
            speed=1290
        )
        
        self.is_front_line = is_front_line
        
        # ------------------------------------------------
        # PASSIF 1 : STRENGTH OF THE SEA
        # ------------------------------------------------
        self.max_hp *= 1.40  # HP +40%
        self.hp = self.max_hp
        self.attack_multiplier += 0.30  # Attack +30%
        self.armor_multiplier += 0.45  # Armor +45%
        self.speed += 100  # Speed +100
        
        # Immunité aux effets de paralysie
        if not hasattr(self, 'immunities'):
            self.immunities = []
        self.immunities.extend(["Freeze", "Petrify", "Stun", "Vine Root", "Sleep"])

    # ------------------------------------------------
    # HOOKS DE DÉBUT DE COMBAT
    # ------------------------------------------------
    def on_battle_start(self, enemies, allies):
        """Passif 3 : Buff de ligne permanent au début du combat"""
        my_row = [a for a in allies if getattr(a, 'is_front_line', False) == self.is_front_line]
        
        for ally in my_row:
            ally.attack_multiplier += 0.25  # Attack +25%
            # On simule le Heal Effect par un multiplicateur si nécessaire
            ally.heal_effect_multiplier = getattr(ally, 'heal_effect_multiplier', 1.0) + 0.35 

    # ------------------------------------------------
    # ACTIVE SKILL : BON VOYAGE!
    # ------------------------------------------------
    def use_active_skill(self, enemies, allies):
        # Cible les ennemis de la ligne arrière (Back-line)
        # Contre le Dummy unique, il est la cible par défaut.
        target = enemies[0]
        
        # 1. Dégâts : 350%
        damage = (self.base_attack * self.attack_multiplier) * 3.5
        
        # 2. Debuff : Réduit Skill Damage de 35% pour 4 rounds
        target.active_debuffs.append("Laguna_Skill_Damage_Down")
        
        # 3. Soin de ligne : 500% de son ATK
        my_row = [a for a in allies if getattr(a, 'is_front_line', False) == self.is_front_line]
        heal_amount = (self.base_attack * self.attack_multiplier) * 5.0
        for ally in my_row:
            ally.hp = min(ally.max_hp, ally.hp + heal_amount)

        # 4. Buff de ligne selon sa position
        if self.is_front_line:
            # Front-line : +30% Damage Reduction pour 4 rounds
            for ally in my_row:
                ally.damage_reduce = getattr(ally, 'damage_reduce', 0.0) + 0.30
        else:
            # Back-line : +50% Skill Damage pour 4 rounds
            for ally in my_row:
                ally.skill_damage_bonus += 0.50

        # 5. Passif 3 : 45% de chance de paralyser chaque cible
        if random.random() < 0.45:
            target.active_debuffs.append(random.choice(["Freeze", "Stun", "Sleep"]))

        return damage

    # ------------------------------------------------
    # PASSIF 2 : OCTO AID
    # ------------------------------------------------
    def on_ally_death(self, dead_ally, allies):
        """Se déclenche à la mort d'un allié"""
        lowest_hp_ally = min(allies, key=lambda a: a.hp)
        
        # Soin : 1200% ATK
        heal_amount = (self.base_attack * self.attack_multiplier) * 12.0
        lowest_hp_ally.hp = min(lowest_hp_ally.max_hp, lowest_hp_ally.hp + heal_amount)
        
        # +25% DR pour 3 rounds
        lowest_hp_ally.damage_reduce = getattr(lowest_hp_ally, 'damage_reduce', 0.0) + 0.25

    def on_death(self, allies):
        """Se déclenche si Laguna meurt"""
        lowest_hp_ally = min(allies, key=lambda a: a.hp)
        lowest_hp_ally.active_buffs.append("Bubble_Mark")