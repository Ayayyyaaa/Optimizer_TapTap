from data import factions
class Weapon:
    def __init__(self, name):
        self.name = name
    def on_battle_start(self, fighter): pass
    def on_round_start(self, fighter, allies): pass
    def on_basic_attack(self, fighter, dmg): pass
    def on_round_end(self, fighter, allies, round_number): pass
    def modify_damage_dealt(self, fighter, target, current_damage): return current_damage
    def on_ally_die(self, fighter, allies):
        pass
    def on_ennemy_die(self, fighter, allies):
        pass
    def on_block(self, fighter):
        pass

class Weapon_Khopesh:
    group = 4
    def __init__(self): self.name = "Khopesh"
    def on_battle_start(self, fighter): pass
    def on_round_start(self, fighter, allies): pass
    def on_basic_attack(self, fighter, dmg): pass
    def on_round_end(self, fighter, allies, round_number): pass
    def modify_damage_dealt(self, fighter, target, current_damage):
        return current_damage * 1.40
    def on_ally_die(self, fighter, allies):
        pass
    def on_ennemy_die(self, fighter, allies):
        pass
    def on_block(self, fighter):
        pass
    
class Weapon_Katana:
    group = 2
    def __init__(self): self.name = "Katana"
    def on_battle_start(self, fighter): pass
    def on_round_start(self, fighter, allies): pass
    def on_basic_attack(self, fighter, dmg): pass
    def on_round_end(self, fighter, allies, round_number): pass
    def modify_damage_dealt(self, fighter, target, current_damage):
        return current_damage * 1.35
    def on_ally_die(self, fighter, allies):
        pass
    def on_ennemy_die(self, fighter, allies):
        pass
    def on_block(self, fighter):
        pass
    
class Weapon_Sai:
    group = 1
    def __init__(self): self.name = "Sai"
    def on_battle_start(self, fighter): pass
    def on_round_start(self, fighter, allies): pass
    def on_round_end(self, fighter, allies, round_number): pass
    def modify_damage_dealt(self, fighter, target, current_damage): return current_damage
    def on_basic_attack(self, fighter, dmg):
        fighter.energy += 60
    def on_ally_die(self, fighter, allies):
        pass
    def on_ennemy_die(self, fighter, allies):
        pass
    def on_block(self, fighter):
        pass

class Weapon_Kunai:
    group = 2
    def __init__(self): self.name = "Kunai"
    def on_battle_start(self, fighter): pass
    def on_round_start(self, fighter, allies): pass
    def on_basic_attack(self, fighter, dmg): pass
    def on_round_end(self, fighter, allies, round_number): pass
    def modify_damage_dealt(self, fighter, target, current_damage): return current_damage
    def on_ally_die(self, fighter, allies):
        pass
    def on_ennemy_die(self, fighter, allies):
        pass
    def on_block(self, fighter):
        pass

class Weapon_Knife:
    group = 1
    def __init__(self): self.name = "Knife"
    def on_battle_start(self, fighter): pass
    def on_round_start(self, fighter, allies): pass
    def on_basic_attack(self, fighter, dmg): pass
    def on_round_end(self, fighter, allies, round_number): pass
    def modify_damage_dealt(self, fighter, target, current_damage): return current_damage
    def modify_dot_damage(self, current_dot_damage):
        return current_dot_damage * 3.0
    def on_ally_die(self, fighter, allies):
        pass
    def on_ennemy_die(self, fighter, allies):
        pass
    def on_block(self, fighter):
        pass
    
class Weapon_Katar:
    group = 4
    def __init__(self):
        self.name = "Katar"

    def on_battle_start(self, fighter):pass
    def on_round_start(self, fighter, allies):
        if all(ally.character.is_alive for ally in allies):
            fighter.attack_multiplier += 0.40
            fighter.spd += 40
    def on_basic_attack(self, fighter, dmg): pass
    def on_round_end(self, fighter, allies, round_number):
        fighter.attack_multiplier -= 0.40
        fighter.spd -= 40
    def modify_damage_dealt(self, fighter, target, current_damage): return current_damage
    def on_ally_die(self, fighter, allies):
        pass
    def on_ennemy_die(self, fighter, allies):
        pass
    def on_block(self, fighter):
        pass


class Weapon_Shuriken:
    group = 2
    def __init__(self):
        self.name = "Shuriken"
    def on_battle_start(self, fighter):pass
    def on_round_start(self, fighter, allies): pass
    def on_basic_attack(self, fighter, dmg): pass
    def on_round_end(self, fighter, allies, round_number): pass
    def modify_damage_dealt(self, fighter, target, current_damage): 
        if target.faction == factions.get(fighter.faction):
            return current_damage * 3
        return current_damage
    def on_ally_die(self, fighter, allies):
        pass
    def on_ennemy_die(self, fighter, allies):
        pass
    def on_block(self, fighter):
        pass
    
class Weapon_Nunchucks:
    group = 1
    def __init__(self):
        self.name = "Nunchucks"
        self.stacks = 0
    def on_battle_start(self, fighter):
        self.stacks = 0
    def on_round_start(self, fighter, allies):
        pass
    def on_basic_attack(self, fighter, dmg): pass
    def on_round_end(self, fighter, allies, round_number): 
        if self.stacks < 5:
            fighter.atk += 0.20 * fighter.base_atk
            self.stacks += 1
    def modify_damage_dealt(self, fighter, target, current_damage): 
        return current_damage
    def on_ally_die(self, fighter, allies):
        pass
    def on_ennemy_die(self, fighter, allies):
        pass
    def on_block(self, fighter):
        pass
    
class Weapon_Bow:
    group = 3
    def __init__(self):
        self.name = "Bow"
        self.stacks = 0
    def on_battle_start(self, fighter):
        self.stacks = 0
    def on_round_start(self, fighter, allies):
        pass
    def on_basic_attack(self, fighter, dmg): pass
    def on_round_end(self, fighter, allies, round_number): 
        if self.stacks > 1:
            self.stacks -= 1
        elif self.stacks == 1:
            fighter.cr -= 60
            self.stacks = 0
    def modify_damage_dealt(self, fighter, target, current_damage): 
        return current_damage
    def on_ally_die(self, fighter, allies):
        pass
    def on_ennemy_die(self, fighter, allies):
        self.stacks = 3 
        fighter.cr += 60
    def on_block(self, fighter):
        pass

class Weapon_Cobra:
    group = 4
    def __init__(self):
        self.name = "Cobra Staff"
    def on_battle_start(self, fighter):pass
    def on_round_start(self, fighter, allies):
        if fighter.hp < fighter.max_hp * 0.5:
            fighter.energy += 50
        if fighter.hp < fighter.max_hp * 0.25:
            fighter.energy += 70
    def on_basic_attack(self, fighter, dmg): pass
    def on_round_end(self, fighter, allies, round_number): pass
    def modify_damage_dealt(self, fighter, target, current_damage): 
        return current_damage
    def on_ally_die(self, fighter, allies):
        pass
    def on_ennemy_die(self, fighter, allies):
        pass
    def on_block(self, fighter):
        pass

class Weapon_Kunai:
    group = 2
    def __init__(self):
        self.name = "Cobra Staff"
    def on_battle_start(self, fighter):pass
    def on_round_start(self, fighter, allies):
        if fighter.hp < fighter.max_hp * 0.5:
            fighter.energy += 50
        if fighter.hp < fighter.max_hp * 0.25:
            fighter.energy += 70
    def on_basic_attack(self, fighter, dmg): pass
    def on_round_end(self, fighter, allies, round_number): pass
    def modify_damage_dealt(self, fighter, target, current_damage): 
        return current_damage
    def on_ally_die(self, fighter, allies):
        pass
    def on_ennemy_die(self, fighter, allies):
        pass
    def on_block(self, fighter):
        fighter.energy += 80

class Weapon_Knuckles:
    group = 1
    def __init__(self):
        self.name = "Knuckles"
    def on_battle_start(self, fighter):pass
    def on_round_start(self, fighter, allies): pass
    def on_basic_attack(self, fighter, dmg):
        fighter.hp += dmg * 2
    def on_round_end(self, fighter, allies, round_number): pass
    def modify_damage_dealt(self, fighter, target, current_damage): 
        return current_damage
    def on_ally_die(self, fighter, allies):
        pass
    def on_ennemy_die(self, fighter, allies):
        pass
    def on_block(self, fighter):
        pass

class Weapon_Claw:
    group = 2
    def __init__(self):
        self.name = "Claw"
    def on_battle_start(self, fighter):pass
    def on_round_start(self, fighter, allies): pass
    def on_basic_attack(self, fighter, dmg):pass
    def on_round_end(self, fighter, allies, round_number): pass
    def modify_damage_dealt(self, fighter, target, current_damage): 
        return current_damage
    def on_ally_die(self, fighter, allies):
        pass
    def on_ennemy_die(self, fighter, allies):
        fighter.hp += fighter.atk * 12
    def on_block(self, fighter):
        pass

class Weapon_Haladie:
    group = 3
    def __init__(self):
        self.name = "Haladie"
    def on_battle_start(self, fighter):pass
    def on_round_start(self, fighter, allies): pass
    def on_basic_attack(self, fighter, dmg):pass
    def on_round_end(self, fighter, allies, round_number):
        fighter.hp += fighter.max_hp * 0.25
    def modify_damage_dealt(self, fighter, target, current_damage): 
        return current_damage
    def on_ally_die(self, fighter, allies):
        pass
    def on_ennemy_die(self, fighter, allies):
        pass
    def on_block(self, fighter):
        pass

class Weapon_Pipe:
    group = 1
    def __init__(self):
        self.name = "Pipe"
        self.stacks = 0
    def on_battle_start(self, fighter):pass
    def on_round_start(self, fighter, allies): pass
    def on_basic_attack(self, fighter, dmg):pass
    def on_round_end(self, fighter, allies, round_number):
        if self.stacks < 5:
            fighter.defense += 0.40 * fighter.max_defense
            self.stacks += 1
    def modify_damage_dealt(self, fighter, target, current_damage): 
        return current_damage
    def on_ally_die(self, fighter, allies):
        pass
    def on_ennemy_die(self, fighter, allies):
        pass
    def on_block(self, fighter):
        pass

class Weapon_Kusarigama:
    group = 4
    def __init__(self):
        self.name = "Kusarigama"
        self.stacks = 0
    def on_battle_start(self, fighter):
        fighter.block += 0.25
    def on_round_start(self, fighter, allies): pass
    def on_basic_attack(self, fighter, dmg):pass
    def on_round_end(self, fighter, allies, round_number): pass
    def modify_damage_dealt(self, fighter, target, current_damage): 
        return current_damage
    def on_ally_die(self, fighter, allies):
        cpt = 0
        for ally in allies:
            if ally.character.is_alive:
                cpt += 1
        if cpt == 1 and self.stacks == 0:
            self.stacks = 1
            fighter.dmg_reduce += 0.6
    def on_ennemy_die(self, fighter, allies):
        pass
    def on_block(self, fighter):
        pass

class Weapon_Dart:
    group = 3
    def __init__(self):
        self.name = "Dart"
        self.stacks = 0
        self.effective = False
    def on_battle_start(self, fighter):pass
    def on_round_start(self, fighter, allies): 
        if self.stacks > 0:
            self.stacks -= 1
            if self.stacks == 0 and self.effective:
                fighter.spd -= 80
                fighter.block -= 0.8
        elif fighter.hp < fighter.max_hp * 0.5 and not self.effective:
            self.effective = True
            self.stacks = 5
            fighter.spd += 80
            fighter.block += 0.8
    def on_basic_attack(self, fighter, dmg):pass
    def on_round_end(self, fighter, allies, round_number): pass
    def modify_damage_dealt(self, fighter, target, current_damage): 
        return current_damage
    def on_ally_die(self, fighter, allies):pass
    def on_ennemy_die(self, fighter, allies):
        pass
    def on_block(self, fighter):
        pass