import itertools
from fighter import Spekkio
from weapon import *

def simulate_combat(weapon_combo):
    """Simule un combat de 10 tours et renvoie les dégâts totaux."""
    spekkio = Spekkio()
    # On équipe les deux armes instanciées
    spekkio.character.weapon = [weapon_combo[0](), weapon_combo[1]()]
    
    # Création d'un ennemi factice (Dummy) avec énormément de PV 
    # pour éviter que Spekkio ne s'attaque lui-même et fausse la simulation
    dummy = Spekkio()
    dummy.character.hp = 9999999999
    
    enemies = [dummy]
    allies = [spekkio] 
    dmg_tot = 0
    
    for tour in range(1, 11):
        for a in allies:
            a.character.weapon[0].on_round_start(a.character, allies)
            a.character.weapon[1].on_round_start(a.character, allies)
        if spekkio.character.is_alive and not spekkio.character.is_stunned:
            if spekkio.character.energy >= 100:
                spekkio.character.energy = 0
                damage = spekkio.ult(enemies, allies)
                dmg_tot += damage
            else:
                damage = spekkio.basic_atk(enemies, allies)
                dmg_tot += damage
        for a in allies:
            a.character.weapon[0].on_round_end(a.character, allies, tour)
            a.character.weapon[1].on_round_end(a.character, allies, tour)
    return dmg_tot

def launch_optimizer():
    # Liste des classes d'armes disponibles
    available_weapons = [Weapon_Nunchucks, Weapon_Shuriken, Weapon_Khopesh, Weapon_Katana, Weapon_Sai, Weapon_Kunai,Weapon_Katar, Weapon_Knife]
    
    # Génère toutes les paires d'armes possibles
    all_combinations = list(itertools.combinations(available_weapons, 2))
    
    results = []
    nb_simulations = 1000 # Nombre de simulations par combinaison pour lisser le RNG
    
    print(f"Lancement de l'optimiseur ({nb_simulations} simulations par combinaison)...\n")
    
    for combo in all_combinations:
        # On empêche l'équipement de deux armes du même groupe (si c'est la règle du jeu)
        if combo[0].group == combo[1].group:
            continue
            
        total_dmg_across_sims = 0
        
        for _ in range(nb_simulations):
            total_dmg_across_sims += simulate_combat(combo)
            
        avg_damage = total_dmg_across_sims / nb_simulations
        combo_name = f"{combo[0]().name} & {combo[1]().name}"
        
        results.append({
            "combo_name": combo_name,
            "avg_damage": avg_damage
        })
        
    # Tri des résultats du plus grand dégât au plus petit
    results.sort(key=lambda x: x["avg_damage"], reverse=True)
    
    print("===== CLASSEMENT DES MEILLEURES COMBINAISONS =====")
    for i, res in enumerate(results):
        print(f"#{i+1} : {res['combo_name']} -> {res['avg_damage']:,.0f} dégâts en moyenne")

# Lancer la recherche
launch_optimizer()