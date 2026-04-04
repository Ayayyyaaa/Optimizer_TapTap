from random import randint
class Dragon:
    """Classe de base pour tous les dragons. Hériter de cette classe pour créer un nouveau dragon."""
    def __init__(self, name):
        self.name = name

    def on_battle_start(self, fighter):           pass
    def on_round_start(self, fighter, allies):    pass
    def on_basic_attack(self, fighter, dmg):      pass
    def on_round_end(self, fighter, allies, round_number): pass
    def modify_damage_dealt(self, fighter, target, current_damage): return current_damage
    def on_ally_die(self, fighter, allies):        pass
    def on_ennemy_die(self, fighter, allies):      pass
    def on_block(self, fighter):                   pass


# ─────────────────────────────────────────────
#  DRAGONS DISPONIBLES
# ─────────────────────────────────────────────

class Zhulong(Dragon):
    """
    """
    def __init__(self, fighter):
        super().__init__("Zhulong")

    def on_battle_start(self, fighter):
        fighter.skill_dmg += 0.6
        fighter.hit_chance += 0.6
        fighter.control_precision += 0.5
    
    def on_round_end(self, fighter, allies, round_number):
        if randint(1, 2) == 1:  
            fighter.atk += 0.15 * fighter.base_atk

class Yinglong(Dragon):
    """
    """
    def __init__(self, fighter):
        super().__init__("Yinglong")

    def on_battle_start(self, fighter):
        fighter.atk += 0.2 * fighter.base_atk
        fighter.cr += 0.25
        fighter.cd += 0.5
        fighter.true_dmg += 0.3

class Tianlu(Dragon):
    """
    """
    def __init__(self, fighter):
        super().__init__("Tianlu")

    def on_battle_start(self, fighter):
        fighter.max_hp *= 0.25
        fighter.dmg_reduce += 0.25
        fighter.control_resist += 0.5
        fighter.true_dmg += 0.3

class Naga(Dragon):
    """
    """
    def __init__(self, fighter):
        super().__init__("Naga")

    def on_battle_start(self, fighter):
        fighter.atk += 0.25 * fighter.base_atk
        fighter.block += 0.5
        fighter.spd += 100
        fighter.true_dmg += 0.3

class Yamata(Dragon):
    """
    """
    def __init__(self, fighter):
        super().__init__("Yamata")

    def on_battle_start(self, fighter):
        fighter.atk += 0.25 * fighter.base_atk
        fighter.max_hp *= 0.25
        fighter.energy += 150
        fighter.true_dmg += 0.3

    def on_ally_die(self, fighter, allies):
        fighter.energy += 60


class Matsu(Dragon):
    """
    """
    def __init__(self, fighter):
        super().__init__("Matsu")

    def on_battle_start(self, fighter):
        fighter.atk += 0.22 * fighter.base_atk
        fighter.control_resist += 0.5

class Dabei(Dragon):
    """
    """
    def __init__(self, fighter):
        super().__init__("Dabei")

    def on_battle_start(self, fighter):
        fighter.atk += 0.18 * fighter.base_atk
        fighter.cr += 0.18

class Toronbo(Dragon):
    """
    """
    def __init__(self, fighter):
        super().__init__("Toronbo")

    def on_battle_start(self, fighter):
        fighter.energy += 50
        fighter.skill_dmg += 0.4

class Goujun(Dragon):
    """
    """
    def __init__(self, fighter):
        super().__init__("Goujun")

    def on_battle_start(self, fighter):
        fighter.atk += 0.18 * fighter.base_atk
        fighter.hp_max *= 0.18

class Mingshe(Dragon):
    """
    """
    def __init__(self, fighter):
        super().__init__("Mingshe")

    def on_battle_start(self, fighter):
        fighter.dmg_reduce += 0.25
        fighter.hp_max *= 0.20

class Apep(Dragon):
    """
    """
    def __init__(self, fighter):
        super().__init__("Apep")

    def on_battle_start(self, fighter):
        fighter.armor_break += 0.5
        fighter.hit_chance += 0.6

# ─── Template pour ajouter un nouveau dragon ─────────────────────────────────
#
# class MonDragon(Dragon):
#     def __init__(self, fighter):
#         super().__init__("MonDragon")
#
#     def on_battle_start(self, fighter):
#         pass  # ex: fighter.cr += 0.10
#
#     def on_round_end(self, fighter, allies, round_number):
#         pass  # ex: fighter.atk += 0.05 * fighter.base_atk
#
# ─────────────────────────────────────────────────────────────────────────────