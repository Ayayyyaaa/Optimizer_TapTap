from debuffs import apply_debuff
class Mutagen:
    def __init__(self, source_char, name = "E"):
        self.name = name
        self.names = {"D" : 0, "C" : 1, "B" : 2, "A" : 3, "S" : 4}
        self.atk_multi = [0.03,0.06,0.09,0.12,0.15]
        self.hp_multi = [0.045,0.09,0.135,0.18,0.225]
        self.armor_multi = [0.06,0.12,0.18,0.24,0.3]
        self.spd_multi = [15,30,45,60,75]
        self.source_char = source_char
        self.stacks = 0

    def apply(self):
        if self.name not in self.names:
            return
        i = self.names[self.name]
        self.source_char.character.atk += self.atk_multi[i] * self.source_char.character.base_atk
        self.source_char.character.max_hp *= (1 + self.hp_multi[i])
        self.source_char.character.max_defense += self.armor_multi[i] * self.source_char.character.base_defense
        self.source_char.character.spd += self.spd_multi[i]

    def perk1(self):
        if self.name in self.names.keys():
            self.source_char.character.atk += 0.03 * self.source_char.character.base_atk
            self.source_char.character.cr += 0.05

    def perk2(self):
        if self.name in ["B", "A", "S"]:
            self.source_char.character.atk += 0.03 * self.source_char.character.base_atk
            self.source_char.character.cd += 0.05

    def perk3(self, trigger):
        if trigger == "enemy" and self.name in ["A", "S"]:
            apply_debuff(self.source_char, "atk_muta_a", duration=3)
        elif self.name in ["A", "S"]:
            self.source_char.character.energy += 20

    def perk4(self):
        if self.name == "S":
            if self.stacks == 0:
                self.source_char.character.cr += 0.25
                self.stacks += 1
            elif self.stacks == 1:
                self.source_char.character.cd += 0.25
                self.stacks += 1
            elif self.stacks == 2:
                self.source_char.character.skill_dmg += 0.25
                self.stacks += 1