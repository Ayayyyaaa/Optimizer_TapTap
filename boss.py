# Fichier: boss.py
from char import Fighter

class Boss(Fighter):
    """
    Classe représentant un Boss (actuellement configuré comme un Sac à PV inoffensif).
    """
    def __init__(self, name="Mech Boss (Dummy)", hp=999999999, armor=1000, speed=0):
        # On appelle le Fighter avec toutes les stats requises.
        # Comme c'est un sac à PV inoffensif, on lui donne 0 en attaque.
        super().__init__(name=name, hp=hp, attack=0, armor=armor, speed=speed)
        
        # --- Tags Spécifiques ---
        self.is_boss = True
        self.is_mech = True # Indispensable pour la règle du Damage Cap à 9000%
        
        # --- Immunités ---
        self.immunities = ["Stun", "Freeze", "Sleep", "Silence", "Petrify", "Vine Root"]

    def apply_debuff(self, debuff_name):
        """Tente d'appliquer un debuff au Boss."""
        if debuff_name in self.immunities:
            return False
            
        if debuff_name not in self.active_debuffs:
            self.active_debuffs.append(debuff_name)
            return True
            
        return False

    def take_turn(self, targets=None):
        """Le boss n'attaque pas, il retourne 0 dégât."""
        return 0