from fighter import *
def launch_game():
    spekkio = Spekkio()
    enemies = [spekkio]
    allies = [spekkio] 
    dmg_tot = 0
    for tour in range(1,11):
        print(f"\n--- Tour {tour} ---")
        for fighter in allies:
            if fighter.character.is_alive and not fighter.character.is_stunned:
                if fighter.character.energy >= 100:
                    fighter.character.energy = 0
                    damage = fighter.ult(enemies, allies)
                    dmg_tot += damage
                    print(f"{fighter.character.name} utilise son Ult pour infliger {damage:.2f} dégâts.")
                else:
                    damage = fighter.basic_atk(enemies, allies)
                    dmg_tot += damage
                    print(f"{fighter.character.name} utilise basic_atk pour infliger {damage:.2f} dégâts.")
    print("\n===== Fin du combat =====")
    print(f"\nDégâts totaux infligés après 10 tours : {dmg_tot:.2f}")
                    
launch_game()