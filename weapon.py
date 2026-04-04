from data import factions
class Weapon:
    def __init__(self, name):
        self.name = name
    def on_battle_start(self, fighter): pass
    def on_round_start(self, fighter, allies): pass
    def on_basic_attack(self, fighter): pass
    def on_round_end(self, fighter, allies, round_number): pass
    def modify_damage_dealt(self, fighter, target, current_damage): return current_damage

class Weapon_Khopesh:
    group = 4
    def __init__(self): self.name = "Khopesh"
    def on_battle_start(self, fighter): pass
    def on_round_start(self, fighter, allies): pass
    def on_basic_attack(self, fighter): pass
    def on_round_end(self, fighter, allies, round_number): pass
    def modify_damage_dealt(self, fighter, target, current_damage):
        return current_damage * 1.40
    
class Weapon_Katana:
    group = 2
    def __init__(self): self.name = "Katana"
    def on_battle_start(self, fighter): pass
    def on_round_start(self, fighter, allies): pass
    def on_basic_attack(self, fighter): pass
    def on_round_end(self, fighter, allies, round_number): pass
    def modify_damage_dealt(self, fighter, target, current_damage):
        return current_damage * 1.35
    
class Weapon_Sai:
    group = 1
    def __init__(self): self.name = "Sai"
    def on_battle_start(self, fighter): pass
    def on_round_start(self, fighter, allies): pass
    def on_round_end(self, fighter, allies, round_number): pass
    def modify_damage_dealt(self, fighter, target, current_damage): return current_damage
    def on_basic_attack(self, fighter):
        fighter.energy += 60

class Weapon_Kunai:
    group = 2
    def __init__(self): self.name = "Kunai"
    def on_battle_start(self, fighter): pass
    def on_round_start(self, fighter, allies): pass
    def on_basic_attack(self, fighter): pass
    def on_round_end(self, fighter, allies, round_number): pass
    def modify_damage_dealt(self, fighter, target, current_damage): return current_damage

class Weapon_Knife:
    group = 1
    def __init__(self): self.name = "Knife"
    def on_battle_start(self, fighter): pass
    def on_round_start(self, fighter, allies): pass
    def on_basic_attack(self, fighter): pass
    def on_round_end(self, fighter, allies, round_number): pass
    def modify_damage_dealt(self, fighter, target, current_damage): return current_damage
    def modify_dot_damage(self, current_dot_damage):
        return current_dot_damage * 3.0
    
class Weapon_Katar:
    group = 4
    def __init__(self):
        self.name = "Katar"

    def on_battle_start(self, fighter):pass
    def on_round_start(self, fighter, allies):
        if all(ally.character.is_alive for ally in allies):
            fighter.attack_multiplier += 0.40
            fighter.spd += 40
    def on_basic_attack(self, fighter): pass
    def on_round_end(self, fighter, allies, round_number):
        fighter.attack_multiplier -= 0.40
        fighter.spd -= 40
    def modify_damage_dealt(self, fighter, target, current_damage): return current_damage

class Weapon_Shuriken:
    group = 2
    def __init__(self):
        self.name = "Shuriken"
    def on_battle_start(self, fighter):pass
    def on_round_start(self, fighter, allies): pass
    def on_basic_attack(self, fighter): pass
    def on_round_end(self, fighter, allies, round_number): pass
    def modify_damage_dealt(self, fighter, target, current_damage): 
        if target.faction == factions.get(fighter.faction):
            return current_damage * 3
        return current_damage
    
class Weapon_Nunchucks:
    group = 1
    def __init__(self):
        self.name = "Nunchucks"
        self.stacks = 0
    def on_battle_start(self, fighter):
        self.stacks = 0
    def on_round_start(self, fighter, allies):
        if self.stacks <= 5:
            fighter.atk += 0.20 * fighter.base_atk
            self.stacks += 1
    def on_basic_attack(self, fighter): pass
    def on_round_end(self, fighter, allies, round_number): pass
    def modify_damage_dealt(self, fighter, target, current_damage): 
        return current_damage