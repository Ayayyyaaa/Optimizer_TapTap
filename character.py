class Character:
        def __init__(self, name, faction, hp,atk,defense,spd,skilld_mg, block, cr, cd, dmg_reduce, control_resist, hit_chance, armor_break, control_precision, stealth, weapon, dragons, pos):
                self.name = name
                self.faction = faction
                self.max_hp = hp 
                self.hp = hp  
                self.base_atk = atk
                self.atk = atk
                self.max_defense = defense
                self.defense = defense
                self.spd = spd
                self.skilld_mg = skilld_mg
                self.block = block
                self.cr = cr
                self.cd = cd
                self.dmg_reduce = dmg_reduce
                self.control_resist = control_resist
                self.hit_chance = hit_chance
                self.armor_break = armor_break
                self.control_precision = control_precision
                self.stealth = stealth
                self.weapon = weapon
                self.dragons = dragons
                self.buffs = []
                self.debuffs = []
                self.energy = 50
                self.position = pos
                self.is_alive = True
                self.is_stunned = False
                self.attack_multiplier = 1

        