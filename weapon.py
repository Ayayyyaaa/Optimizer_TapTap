class Weapon:
    def __init__(self, name):
        self.name = name
    def on_battle_start(self, fighter): pass
    def on_round_start(self, fighter): pass
    def on_basic_attack(self, fighter): pass
    def on_round_end(self, fighter, round_number): pass
    def modify_damage_dealt(self, fighter, target, current_damage): return current_damage

class Weapon_Khopesh:
    group = 4
    def __init__(self): self.name = "Khopesh"
    def on_battle_start(self, fighter): pass
    def on_round_start(self, fighter): pass
    def on_basic_attack(self, fighter): pass
    def on_round_end(self, fighter, round_number): pass
    def modify_damage_dealt(self, fighter, target, current_damage):
        return current_damage * 1.40
    
class Weapon_Katana:
    group = 2
    def __init__(self): self.name = "Katana"
    def on_battle_start(self, fighter): pass
    def on_round_start(self, fighter): pass
    def on_basic_attack(self, fighter): pass
    def on_round_end(self, fighter, round_number): pass
    def modify_damage_dealt(self, fighter, target, current_damage):
        return current_damage * 1.35
    
class Weapon_Sai:
    group = 1
    def __init__(self): self.name = "Sai"
    def on_battle_start(self, fighter): pass
    def on_round_start(self, fighter): pass
    def on_round_end(self, fighter, round_number): pass
    def modify_damage_dealt(self, fighter, target, current_damage): return current_damage
    def on_basic_attack(self, fighter):
        fighter.energy += 60

class Weapon_Kunai:
    group = 2
    def __init__(self): self.name = "Kunai"
    def on_battle_start(self, fighter): pass
    def on_round_start(self, fighter): pass
    def on_basic_attack(self, fighter): pass
    def on_round_end(self, fighter, round_number): pass
    def modify_damage_dealt(self, fighter, target, current_damage): return current_damage