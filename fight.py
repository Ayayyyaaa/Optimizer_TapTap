import itertools
from fighter import Spekkio
from weapon import *

def simulate_combat(weapon_combo):
    """Simule un combat de 10 tours et renvoie les dégâts totaux."""
    spekkio = Spekkio()
    spekkio.character.weapon = [weapon_combo[0](), weapon_combo[1](), weapon_combo[2]()]
    
    # Création d'un ennemi factice (Dummy) avec énormément de PV 
    # pour éviter que Spekkio ne s'attaque lui-même et fausse la simulation
    dummy = Spekkio()
    dummy.character.hp = 9999999999
    
    enemies = [dummy]
    allies = [spekkio] 
    dmg_tot = 0
    for a in allies:
        for w in a.character.weapon:
            w.on_battle_start(a.character)
            w.on_ennemy_die(a.character, allies)
    for tour in range(1, 11):
        for w in a.character.weapon:
            w.on_round_start(a.character, allies)
        if spekkio.character.is_alive and not spekkio.character.is_stunned:
            if spekkio.character.energy >= 100:
                spekkio.character.energy = 0
                damage = spekkio.ult(enemies, allies)
                dmg_tot += damage
            else:
                damage = spekkio.basic_atk(enemies, allies)
                dmg_tot += damage
        for a in allies:
            for w in a.character.weapon:
                w.on_round_end(a.character, allies, tour)
    return dmg_tot

def launch_optimizer():
    # Liste des classes d'armes disponibles (attention aux doublons, Kunai y était 2 fois)
    available_weapons = [
        Weapon_Kusarigama, Weapon_Pipe, Weapon_Haladie, Weapon_Claw, Weapon_Knuckles, 
        Weapon_Cobra, Weapon_Bow, Weapon_Nunchucks, Weapon_Shuriken, 
        Weapon_Khopesh, Weapon_Katana, Weapon_Sai, Weapon_Kunai, 
        Weapon_Katar, Weapon_Knife,Weapon_Dart,Weapon_Spear
    ]

    # Génère toutes les combinaisons de 3 armes possibles
    all_combinations = list(itertools.combinations(available_weapons, 3))
    
    results = []
    nb_simulations = 20 
    
    print(f"Lancement de l'optimiseur ({nb_simulations} simulations par combinaison)...\n")
    
    for combo in all_combinations:
        groups = [combo[0].group, combo[1].group, combo[2].group]
        
        if groups.count(1) > 1 or groups.count(2) > 1 or groups.count(3) > 1:
            continue
            
        total_dmg_across_sims = 0
        
        for _ in range(nb_simulations):
            total_dmg_across_sims += simulate_combat(combo)
            
        avg_damage = total_dmg_across_sims / nb_simulations
        combo_name = f"{combo[0]().name} & {combo[1]().name} & {combo[2]().name}"
        
        results.append({
            "combo_name": combo_name,
            "avg_damage": avg_damage
        })
        
    results.sort(key=lambda x: x["avg_damage"], reverse=True)
    
    print("===== CLASSEMENT DES MEILLEURES COMBINAISONS =====")
    for i, res in enumerate(results[:10]): 
        print(f"#{i+1} : {res['combo_name']} -> {res['avg_damage']:,.0f} dégâts en moyenne")

launch_optimizer()