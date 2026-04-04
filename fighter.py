from character import Character
import random
class Spekkio:
    def __init__(self):
        self.character = Character("Spekkio", "Mantis", 2929509, 72514, 2884, 1173, 1, 0, 1.25, 1, 1, 0.5, 0.15, 0.5, 0, 0, [], [], 4)
        self.immune = ["atk_reduce", "cr_reduce", "hi_chance_reduce", "stun"]
        self.position = 4

    def basic_atk(self, enemies, allies:list):
        """
        Passive skill #2 : Attaque de base
        Prend en paramètre un Character ennemis vivants.
        Prend en paramètre une liste d'objets Character allies vivants.
        """
        if not enemies:
            return 0
            
        # 1. Détermination de la cible selon la position de Spekkio
        if 1 <= self.position <= 3:
            target = max(enemies, key=lambda e: e.character.atk)
        else:
            target = min(enemies, key=lambda e: e.character.hp)

        base_damage = self.character.atk * 2.50

        is_crit = random.random() < self.character.cr
        
        if is_crit:
            self.on_crit()
            damage = base_damage * self.character.cd
            self.character.energy += 50
            
            # --- LOGIQUE DE DEBUFF À AJOUTER SELON TON MOTEUR DE JEU ---
            # target.armor -= target.armor * 0.25  (pendant 5 tours)
            # target.dmg_reduce -= 0.25            (pendant 5 tours)
        else:
            damage = base_damage
        self.passif1(enemies)
        for w in self.character.weapon:
            damage = w.modify_damage_dealt(self.character, target.character, damage)
            w.on_basic_attack(self.character, damage)
            
            
        return damage*self.character.attack_multiplier
    

    
    def ult(self, enemies, allies:list):
        """
        Active skill : Attaque spéciale
        Prend en paramètre la liste des ennemis et des alliés vivants.
        """
        if not enemies:
            return 0

        if 1 <= self.position <= 3:
            target = max(enemies, key=lambda e: e.character.atk)
        else:
            target = max(enemies, key=lambda e: e.character.hp)

        num_attacks = 3
        
        if all(ally.character.is_alive for ally in allies):
            num_attacks += 1
            print("[Wave Cutter] Tous les alliés sont en vie : +1 attaque.")
            
        if len(enemies) == 1:
            num_attacks += 1
            self.character.energy += 80
            print("[Wave Cutter] Dernier ennemi restant : +1 attaque et +80 Energy.")

        bonus_cr = 0
        if self.character.hp > (self.character.max_hp * 0.5):
            bonus_cr = 0.30
            print("[Wave Cutter] HP > 50% : Chances de crit augmentées de 30%.")
        else:
            heal_amount = self.character.max_hp * 0.75
            self.character.hp = min(self.character.max_hp, self.character.hp + heal_amount)
            print(f"[Wave Cutter] HP <= 50% : Spekkio se soigne de {heal_amount:.0f} HP.")

        total_damage = 0
        for i in range(num_attacks):
            attack_dmg = self.character.atk * 4.00 # 400% de dégâts
            
            # On vérifie le critique pour chaque frappe avec le bonus potentiel
            if random.random() < (self.character.cr + bonus_cr):
                self.on_crit()
                attack_dmg *= self.character.cd
                
            total_damage += attack_dmg

        for w in self.character.weapon:
            total_damage = w.modify_damage_dealt(self.character, target.character, total_damage)

        return total_damage*self.character.attack_multiplier
    
    def passif1(self, enemies):
        """
        Passive skill #3 (Shell Shockwave) : Effet de fin de round.
        À appeler dans la boucle principale de ton jeu à la fin de chaque round.
        """
        if self.character.energy >= 100:
            self.character.atk += 1.10 * self.character.base_atk
            for enemy in enemies:
                if enemy.character.is_alive and enemy.character.hp <= (enemy.character.max_hp * 0.50):
                    # --- LOGIQUE DE DEBUFF À AJOUTER SELON TON MOTEUR DE JEU ---
                    # enemy.character.armor -= 0.30  (pendant 5 tours)
                    # enemy.character.block -= 0.30  (pendant 5 tours)
                    # enemy.character.spd -= 100     (pendant 5 tours)
                    pass

    def on_crit(self):
        """
        À appeler à chaque fois que Spekkio fait un Critical Strike (dans basic_atk ou ult).
        """
        if random.random() < 0.25:
            self.character.cd += 0.25