# ═══════════════════════════════════════════════════════════════
#  CHARACTER.PY
# ═══════════════════════════════════════════════════════════════

class Character:
    def __init__(self, name, faction, hp, atk, defense, spd, skill_dmg,
                 block, cr, cd, dmg_reduce, control_resist, hit_chance,
                 armor_break, control_precision, stealth, weapon, dragons, pos):

        self.name       = name
        self.faction    = faction

        self.max_hp     = hp
        self.hp         = hp
        self.base_atk   = atk
        self.atk        = atk
        self.max_defense   = defense
        self.base_defense  = defense
        self.defense    = defense
        self.spd        = spd
        self.skill_dmg  = skill_dmg
        self.block      = block
        self.cr         = cr
        self.cd         = cd
        self.dmg_reduce = dmg_reduce
        self.control_resist     = control_resist
        self.hit_chance         = hit_chance      # miss chance (0.15 = 15% de rater)
        self.armor_break        = armor_break
        self.control_precision  = control_precision
        self.stealth    = stealth
        self.weapon     = weapon
        self.dragons    = dragons

        self.buffs      = []
        self.debuffs    = []
        self.energy     = 50
        self.position   = pos
        self.is_alive   = True
        self.is_stunned = False
        self.attack_multiplier = 1.0
        self.true_dmg   = 0.0       # fraction des dégâts qui bypass armor+dmg_reduce

        # Modificateurs de dégâts reçus (activés par debuffs)
        self.basic_dmg_taken = 0.0  # +X% dégâts basic reçus (frozen)
        self.skill_dmg_taken = 0.0  # +X% dégâts skill reçus (petrified)
        self.heal_effect     = 1.0  # multiplicateur de soins reçus (cursed → 0.5)

        # Liste d'immunités (remplie par le fighter)
        self._immune    = []