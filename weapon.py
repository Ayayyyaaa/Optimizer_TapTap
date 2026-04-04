class Weapon:
    def __init__(self, name):
        self.name = name
    def on_battle_start(self, fighter): pass
    def on_round_start(self, fighter): pass
    def on_basic_attack(self, fighter): pass
    def on_round_end(self, fighter, round_number): pass
    def modify_damage_dealt(self, fighter, target, current_damage): return current_damage


class Weapon_Katar:
    """
    FIX: Le buff ATK+SPD est permanent (appliqué une seule fois au début du combat),
    pas stacké à chaque round. Déplacé dans on_battle_start.
    """
    group = 4
    def __init__(self):
        self.name = "Katar"

    def on_battle_start(self, fighter):
        # Appliqué UNE SEULE FOIS au début du combat
        fighter.attack_multiplier += 0.40
        fighter.speed += 40

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


class Weapon_Shuriken:
    group = 2
    def __init__(self): self.name = "Shuriken"
    def on_battle_start(self, fighter): pass
    def on_round_start(self, fighter): pass
    def on_basic_attack(self, fighter): pass
    def on_round_end(self, fighter, round_number): pass
    def modify_damage_dealt(self, fighter, target, current_damage):
        if getattr(fighter, 'has_faction_advantage', False):
            return current_damage * 4.0
        return current_damage


class Weapon_Knife:
    group = 1
    def __init__(self): self.name = "Knife"
    def on_battle_start(self, fighter): pass
    def on_round_start(self, fighter): pass
    def on_basic_attack(self, fighter): pass
    def on_round_end(self, fighter, round_number): pass
    def modify_damage_dealt(self, fighter, target, current_damage): return current_damage
    def modify_dot_damage(self, current_dot_damage):
        return current_dot_damage * 3.0


class Weapon_Nunchucks:
    """
    FIX: on_round_start appliquait stacks*0.20 de façon cumulative à chaque round
    (au round 5 avec 5 stacks = +5.0 ATK multiplier sur un seul héros).
    Correction : on applique seulement le DELTA entre l'ancien et le nouveau stack.
    """
    group = 1
    def __init__(self):
        self.name = "Nunchucks"
        self.stacks = 0
        self._applied_bonus = 0.0  # Bonus déjà appliqué sur le fighter

    def on_battle_start(self, fighter):
        self.stacks = 0
        self._applied_bonus = 0.0

    def on_round_start(self, fighter):
        # Applique seulement le delta depuis la dernière application
        new_bonus = self.stacks * 0.20
        delta = new_bonus - self._applied_bonus
        fighter.attack_multiplier += delta
        self._applied_bonus = new_bonus

    def on_basic_attack(self, fighter): pass

    def on_round_end(self, fighter, round_number):
        if self.stacks < 5:
            self.stacks += 1

    def modify_damage_dealt(self, fighter, target, current_damage): return current_damage


class Weapon_Sai:
    group = 1
    def __init__(self): self.name = "Sai"
    def on_battle_start(self, fighter): pass
    def on_round_start(self, fighter): pass
    def on_round_end(self, fighter, round_number): pass
    def modify_damage_dealt(self, fighter, target, current_damage): return current_damage
    def on_basic_attack(self, fighter):
        fighter.energy += 60


class Weapon_Bow:
    group = 3
    def __init__(self): self.name = "Bow"
    def on_battle_start(self, fighter): pass
    def on_round_start(self, fighter): pass
    def on_basic_attack(self, fighter): pass
    def on_round_end(self, fighter, round_number): pass
    def modify_damage_dealt(self, fighter, target, current_damage): return current_damage


class Weapon_CobraStaff:
    group = 4
    def __init__(self): self.name = "Cobra Staff"
    def on_battle_start(self, fighter): pass
    def on_round_start(self, fighter): pass
    def on_basic_attack(self, fighter): pass
    def on_round_end(self, fighter, round_number): pass
    def modify_damage_dealt(self, fighter, target, current_damage): return current_damage


class Weapon_Kunai:
    group = 2
    def __init__(self): self.name = "Kunai"
    def on_battle_start(self, fighter): pass
    def on_round_start(self, fighter): pass
    def on_basic_attack(self, fighter): pass
    def on_round_end(self, fighter, round_number): pass
    def modify_damage_dealt(self, fighter, target, current_damage): return current_damage


class Weapon_Knuckles:
    group = 1
    def __init__(self): self.name = "Knuckles"
    def on_battle_start(self, fighter): pass
    def on_round_start(self, fighter): pass
    def on_basic_attack(self, fighter): pass
    def on_round_end(self, fighter, round_number): pass
    def modify_damage_dealt(self, fighter, target, current_damage): return current_damage


class Weapon_Bomb:
    group = 2
    def __init__(self): self.name = "Bomb"
    def on_battle_start(self, fighter): pass
    def on_round_start(self, fighter): pass
    def on_basic_attack(self, fighter): pass
    def on_round_end(self, fighter, round_number): pass
    def modify_damage_dealt(self, fighter, target, current_damage): return current_damage


class Weapon_Claw:
    group = 2
    def __init__(self): self.name = "Claw"
    def on_battle_start(self, fighter): pass
    def on_round_start(self, fighter): pass
    def on_basic_attack(self, fighter): pass
    def on_round_end(self, fighter, round_number): pass
    def modify_damage_dealt(self, fighter, target, current_damage): return current_damage


class Weapon_Haladie:
    group = 3
    def __init__(self): self.name = "Haladie"
    def on_battle_start(self, fighter): pass
    def on_round_start(self, fighter): pass
    def on_basic_attack(self, fighter): pass
    def on_round_end(self, fighter, round_number): pass
    def modify_damage_dealt(self, fighter, target, current_damage): return current_damage


class Weapon_Pipe:
    group = 1
    def __init__(self):
        self.name = "Pipe"
        self.stacks = 0

    def on_battle_start(self, fighter): pass
    def on_round_start(self, fighter): pass
    def on_basic_attack(self, fighter): pass
    def modify_damage_dealt(self, fighter, target, current_damage): return current_damage

    def on_round_end(self, fighter, round_number):
        if self.stacks < 5:
            self.stacks += 1
            fighter.armor_multiplier = getattr(fighter, 'armor_multiplier', 1.0) + 0.40


class Weapon_Kusarigama:
    group = 4
    def __init__(self): self.name = "Kusarigama"
    def on_battle_start(self, fighter): pass
    def on_round_start(self, fighter): pass
    def on_basic_attack(self, fighter): pass
    def on_round_end(self, fighter, round_number): pass
    def modify_damage_dealt(self, fighter, target, current_damage): return current_damage


class Weapon_Dart:
    group = 4
    def __init__(self): self.name = "Dart"
    def on_battle_start(self, fighter): pass
    def on_round_start(self, fighter): pass
    def on_basic_attack(self, fighter): pass
    def on_round_end(self, fighter, round_number): pass
    def modify_damage_dealt(self, fighter, target, current_damage): return current_damage


class Weapon_Spear:
    group = 3
    def __init__(self): self.name = "Spear"
    def on_battle_start(self, fighter): pass
    def on_round_start(self, fighter): pass
    def on_basic_attack(self, fighter): pass
    def on_round_end(self, fighter, round_number): pass
    def modify_damage_dealt(self, fighter, target, current_damage): return current_damage


class Weapon_Tomahawk:
    group = 3
    def __init__(self): self.name = "Tomahawk"

    def on_battle_start(self, fighter):
        fighter.control_resist += 0.35

    def on_round_start(self, fighter): pass
    def on_basic_attack(self, fighter): pass
    def modify_damage_dealt(self, fighter, target, current_damage): return current_damage

    def on_round_end(self, fighter, round_number):
        for cc in ["Freeze", "Petrify", "Stun", "Vine Root", "Sleep"]:
            if cc in fighter.active_debuffs:
                fighter.active_debuffs.remove(cc)


class Weapon_FanAxe:
    group = 3
    def __init__(self): self.name = "Fan Axe"

    def on_battle_start(self, fighter):
        fighter.control_precision += 0.75

    def on_round_start(self, fighter): pass
    def on_basic_attack(self, fighter): pass
    def on_round_end(self, fighter, round_number): pass
    def modify_damage_dealt(self, fighter, target, current_damage): return current_damage