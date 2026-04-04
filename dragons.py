class Dragon:
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

class Zhulong:
    def __init__(self, fighter):
        self.name = "Zhulong"
        self.fighter = fighter
        self.fighter.character.dragons.append(self)

    def on_battle_start(self, fighter):
        fighter.atk += 0.15 * fighter.base_atk
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