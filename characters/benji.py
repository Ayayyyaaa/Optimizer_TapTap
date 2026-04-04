import random
from char import Hero

class Benji(Hero):
    def __init__(self):
        # Stats de base tirées de ton image (vraisemblablement niveau max)
        super().__init__(
            name="Benji", 
            hp=6104803, 
            attack=92261, 
            armor=3442, 
            speed=1418
        )
        
        # ------------------------------------------------
        # PASSIF 1 : PRIMAL FURY
        # Stats permanentes ajoutées dès l'initialisation
        # ------------------------------------------------
        self.attack_multiplier += 0.40
        self.crit_chance += 40.0
        self.skill_damage_bonus += 0.60 # +60% Skill Damage
        self.armor_break += 60.0
        
        # Gestionnaire de stacks pour le Passif 1 (+15% Crit Dmg sur Crit)
        # Comme l'algo ne gère pas encore les durées (3 rounds), 
        # on va tracker l'activation pour le tour en cours.
        self.current_turn_crit_dmg_bonus = 0.0
        
        # Flag pour le Passif 3 (HP < 60%, trigger une fois)
        self.instinct_triggered = False

    def _roll_crit(self):
        """Fonction utilitaire pour lancer le dé de coup critique."""
        return random.random() < (self.crit_chance / 100.0)

    # ------------------------------------------------
    # ACTIVE SKILL (Inventé car image manquante)
    # ------------------------------------------------
    def use_active_skill(self, enemies, allies):
        target = enemies[0] # Cible unique contre le Dummy
        
        # Multiplicateur d'Energy Overflow standard
        overflow = max(0, self.energy - 100)
        overflow_bonus = overflow * 0.005
        
        # Dégâts inventés : 800% monocible (Plausible pour un attaquant Feral)
        damage = (self.base_attack * self.attack_multiplier) * 8.0
        
        # On applique le bonus spécifique de Benji (Passif 1 : +60% Skill Damage)
        damage *= (1.0 + self.skill_damage_bonus + overflow_bonus)
        
        # Gestion du coup critique et déclenchement du Passif 1
        # (L'image dit "When landing a Critical Strike", cela s'applique aussi au Skill)
        if self._roll_crit():
            # Applique le Crit Dmg (de base + stacks du tour précédent si géré)
            damage *= (self.crit_dmg + self.current_turn_crit_dmg_bonus)
            # Gagne un stack de +15% Crit Dmg pour le prochain tour (simulé permanent ici)
            self.current_turn_crit_dmg_bonus += 0.15
            
        return damage

    # ------------------------------------------------
    # PASSIF 2 : WILD INSTINCT (Remplace l'attaque basique)
    # ------------------------------------------------
    def use_basic_attack(self, enemies):
        target = enemies[0]
        
        # Dégâts augmentés : 200% au lieu de 100%
        base_hit = (self.base_attack * self.attack_multiplier) * 2.0 
        
        is_crit = self._roll_crit()
        
        if is_crit:
            # Applique le Crit Dmg
            base_hit *= (self.crit_dmg + self.current_turn_crit_dmg_bonus)
            # Déclenche Passif 1 (+15% Crit Dmg)
            self.current_turn_crit_dmg_bonus += 0.15
            
            # --- EFFETS SPÉCIFIQUES WILD INSTINCT SUR CRIT ---
            # 1. Restore 40 Energy to self (En plus des 50 naturels = +90 !)
            self.energy += 40
            # 2. Reduce target's Armor by 30% for 3 rounds (Applique le tag)
            target.active_debuffs.append("Benji_Armor_Down_30")
            
        return base_hit

    # ------------------------------------------------
    # PASSIF 3 : SPIRIT OF THE WOLF
    # ------------------------------------------------
    def on_round_start(self):
        """Hook appelé au début de chaque round."""
        # Condition de PV < 60% (Inutile contre Dummy inoffensif, codé par principe)
        if (self.hp / self.max_hp) < 0.60 and not self.instinct_triggered:
            self.instinct_triggered = True
            # Buffs défensifs (inutiles ici)
            self.active_buffs.append("Benji_Dodge_CtrlResist_Up")

    def on_ally_skill_used(self, target, enemies, allies):
        """
        NOUVEAU HOOK : À appeler dans algo.py quand N'IMPORTE QUEL allié utilise un skill.
        C'est ici que réside la puissance de Benji en équipe.
        """
        # 50% de chance de lancer une poursuite
        if random.random() < 0.50:
            # Dégâts : 300% Attaque. Considéré comme une "Normal Attack".
            pursuit_damage = (self.base_attack * self.attack_multiplier) * 3.0
            
            # Puisque c'est une "Normal Attack", elle peut Crit et déclencher Passif 1 & 2 !
            if self._roll_crit():
                pursuit_damage *= (self.crit_dmg + self.current_turn_crit_dmg_bonus)
                self.current_turn_crit_dmg_bonus += 0.15 # Stack Crit Dmg
                
                # Effets Wild Instinct sur Crit (Poursuite)
                self.energy += 40 # Énergie bonus sur Poursuite Crit !
                target.active_debuffs.append("Benji_Armor_Down_30") # Armor shred
                
            return pursuit_damage
        
        return 0