import random
import copy
import inspect
from boss import Boss
from weapon import * # Tes classes d'armes
# Tes personnages (à importer depuis tes fichiers)
from characters.masamune import Masamune
from characters.spekkio import Spekkio
from characters.benji import Benji
from characters.chancer import Chancer
from characters.laguna import Laguna
from characters.zemus import Zemus
from characters.zura import Zura
from char import Hero

# ==========================================
# 1. LE MOTEUR DE COMBAT
# ==========================================

ALLOWED_GROUPS_PER_SLOT = {
    0: [1, 4], # Emplacement 1 (Index 0) accepte les groupes 1 et 4
    1: [2, 4], # Emplacement 2 (Index 1) accepte les groupes 2 et 4
    2: [3, 4]  # Emplacement 3 (Index 2) accepte les groupes 3 et 4
}

def simulate_10_turns_vs_dummy(team):
    """Simule le combat de l'équipe contre le Boss."""
    total_team_damage = 0

    # --- RECRÉATION PROPRE DES HÉROS DEPUIS LEURS CLASSES ---
    # On recrée chaque héros depuis sa classe pour avoir des stats vierges.
    # Les passifs __init__ (ex: Spekkio +35% attack) sont ainsi appliqués
    # une seule fois, proprement, sans accumulation entre simulations.
    fresh_heroes = []
    for hero in team["heroes"]:
        fresh = hero.__class__()           # Recrée l'instance via __init__
        fresh.weapons = copy.deepcopy(hero.weapons)  # Copie les armes du build
        fresh_heroes.append(fresh)
    allies = fresh_heroes

    # Création du Boss (Sac à PV)
    boss = Boss(name="Mech Boss Dummy", hp=999999999, armor=1000, speed=0)
    enemies = [boss]

    # --- ÉTAPE 1 : DÉBUT DU COMBAT ---
    for hero in allies:
        hero.energy = 50
        hero.active_buffs = []
        hero.active_debuffs = []

        if hasattr(hero, 'on_battle_start'):
            hero.on_battle_start(enemies, allies)
        for weapon in hero.weapons:
            if hasattr(weapon, 'on_battle_start'):
                weapon.on_battle_start(hero)

    # --- ÉTAPE 2 : LA BOUCLE DES 10 TOURS ---
    for round_number in range(1, 11):

        # A. Début du tour (Hooks héros + armes)
        for hero in allies:
            # FIX: appel du hook on_round_start du héros (ex: Chancer relance son dé)
            if hasattr(hero, 'on_round_start'):
                sig = inspect.signature(hero.on_round_start)
                params = list(sig.parameters.keys())
                if len(params) >= 2:
                    hero.on_round_start(enemies=enemies, allies=allies)
                else:
                    hero.on_round_start()
            for weapon in hero.weapons:
                if hasattr(weapon, 'on_round_start'):
                    weapon.on_round_start(hero)

        # B. Calcul de l'Initiative (Héros + Boss)
        turn_order = sorted(allies + enemies, key=lambda f: f.speed, reverse=True)

        # C. Résolution des actions
        for fighter in turn_order:
            if fighter.hp <= 0:
                continue

            damage = 0

            if getattr(fighter, 'is_boss', False):
                boss_dmg = fighter.take_turn(targets=allies)
                damage = boss_dmg if boss_dmg is not None else 0
            else:
                # Track si ce héros va utiliser son skill (energy >= 100) pour Benji
                _used_skill = fighter.energy >= 100 and "Silence" not in fighter.active_debuffs

                damage = fighter.take_turn(enemies=enemies, allies=allies)

                # FIX: Déclenche Benji.on_ally_skill_used quand un allié utilise son skill
                if _used_skill:
                    for ally in allies:
                        if ally is not fighter and hasattr(ally, 'on_ally_skill_used'):
                            pursuit_dmg = ally.on_ally_skill_used(
                                target=enemies[0], enemies=enemies, allies=allies
                            )
                            if pursuit_dmg:
                                # Poursuite soumise au damage cap aussi
                                max_pursuit = ally.base_attack * 90.0
                                pursuit_dmg = min(pursuit_dmg, max_pursuit)
                                total_team_damage += pursuit_dmg

                for weapon in fighter.weapons:
                    if hasattr(weapon, 'modify_damage_dealt'):
                        damage = weapon.modify_damage_dealt(fighter, enemies[0], damage)

                # Damage Cap (Mech Boss = 9000%)
                max_damage_allowed = fighter.base_attack * 90.0
                damage = min(damage, max_damage_allowed)

                total_team_damage += damage

        # D. Fin du tour (Hooks héros et armes)
        for hero in allies:
            if hasattr(hero, 'on_round_end'):
                sig = inspect.signature(hero.on_round_end)
                if len(sig.parameters) >= 2:
                    hero.on_round_end(enemies, allies)
                else:
                    hero.on_round_end(enemies)

            for weapon in hero.weapons:
                if hasattr(weapon, 'on_round_end'):
                    weapon.on_round_end(hero, round_number)

    return total_team_damage

# ==========================================
# 2. L'ALGORITHME GÉNÉTIQUE
# ==========================================

def evaluate_team(team):
    return simulate_10_turns_vs_dummy(team)

def generate_random_team(all_hero_classes, all_weapons, all_dragons):
    """Génère une équipe avec des héros uniques, des armes uniques respectant les groupes."""
    # all_hero_classes est une liste de CLASSES (pas d'instances)
    chosen_classes = random.sample(all_hero_classes, 6)
    team_heroes = [cls() for cls in chosen_classes]  # On instancie ici
    used_weapon_classes = set()

    for hero in team_heroes:
        hero.weapons = [None, None, None]

        for slot_index in range(3):
            valid_classes = [
                wc for wc in all_weapons
                if getattr(wc, 'group', 0) in ALLOWED_GROUPS_PER_SLOT[slot_index]
                and wc not in used_weapon_classes
            ]
            chosen_weapon_class = random.choice(valid_classes)
            hero.weapons[slot_index] = chosen_weapon_class()
            used_weapon_classes.add(chosen_weapon_class)

    return {"heroes": team_heroes, "dragons": []}

def run_genetic_optimizer(all_hero_classes, all_weapons, all_dragons=[], generations=50, population_size=100):
    print("Génération de la population initiale...")
    population = [generate_random_team(all_hero_classes, all_weapons, all_dragons) for _ in range(population_size)]

    # Tracking du VRAI meilleur absolu toutes générations confondues
    all_time_best_score = -1
    all_time_best_team = None
    stagnation_counter = 0
    STAGNATION_LIMIT = 8  # Injection de diversité si pas de progrès pendant N gens

    for generation in range(generations):
        scored_population = [(evaluate_team(team), team) for team in population]
        scored_population.sort(key=lambda x: x[0], reverse=True)

        gen_best_score = scored_population[0][0]

        # Mise à jour du meilleur absolu
        if gen_best_score > all_time_best_score:
            all_time_best_score = gen_best_score
            all_time_best_team = copy.deepcopy(scored_population[0][1])
            stagnation_counter = 0
            marker = " ★ NOUVEAU RECORD"
        else:
            stagnation_counter += 1
            marker = f" (stagnation {stagnation_counter}/{STAGNATION_LIMIT})"

        print(f"Génération {generation} - Dégâts : {gen_best_score:.0f}{marker}  |  Record : {all_time_best_score:.0f}")

        elite_count = max(2, int(population_size * 0.10))
        elites = [item[1] for item in scored_population[:elite_count]]

        # Anti-stagnation : injection de nouvelles équipes aléatoires
        if stagnation_counter >= STAGNATION_LIMIT:
            nb_injection = population_size // 4
            print(f"  → Stagnation! Injection de {nb_injection} équipes aléatoires.")
            stagnation_counter = 0
            injection = [generate_random_team(all_hero_classes, all_weapons, all_dragons)
                         for _ in range(nb_injection)]
            new_population = copy.deepcopy(elites) + injection
        else:
            new_population = copy.deepcopy(elites)

        while len(new_population) < population_size:
            # --- 1. CROISEMENT ---
            parent1 = random.choice(elites)
            parent2 = random.choice(elites)

            # Fusion des héros des deux parents (3 de chaque)
            raw_heroes = copy.deepcopy(parent1["heroes"][:3] + parent2["heroes"][3:])

            # --- 2. RÉSOLUTION DES DOUBLONS DE HÉROS ---
            # Un même type de héros ne peut apparaître qu'une seule fois
            seen_hero_classes = set()
            unique_heroes = []
            duplicate_slots_count = 0
            for h in raw_heroes:
                if type(h) not in seen_hero_classes:
                    seen_hero_classes.add(type(h))
                    unique_heroes.append(h)
                else:
                    duplicate_slots_count += 1

            # On complète avec des héros pas encore dans l'équipe
            available_classes = [cls for cls in all_hero_classes if cls not in seen_hero_classes]
            if len(available_classes) >= duplicate_slots_count:
                replacements = random.sample(available_classes, duplicate_slots_count)
            else:
                replacements = available_classes  # Cas limite (peu de héros dans le catalogue)
            for cls in replacements:
                new_hero = cls()
                # On lui assigne des armes valides aléatoires
                new_hero.weapons = [None, None, None]
                temp_used = {type(w) for h in unique_heroes for w in h.weapons if w is not None}
                for slot_index in range(3):
                    valid = [wc for wc in all_weapons
                             if getattr(wc, 'group', 0) in ALLOWED_GROUPS_PER_SLOT[slot_index]
                             and wc not in temp_used]
                    if valid:
                        chosen = random.choice(valid)
                        new_hero.weapons[slot_index] = chosen()
                        temp_used.add(chosen)
                unique_heroes.append(new_hero)

            child_heroes = unique_heroes

            # --- 3. RÉSOLUTION DES DOUBLONS D'ARMES ---
            equipped_weapon_classes = set()
            duplicates_to_replace = []

            for hero in child_heroes:
                for slot_index, weapon in enumerate(hero.weapons):
                    if weapon is None:
                        duplicates_to_replace.append((hero, slot_index))
                        continue
                    weapon_type = type(weapon)
                    if weapon_type in equipped_weapon_classes:
                        duplicates_to_replace.append((hero, slot_index))
                    else:
                        equipped_weapon_classes.add(weapon_type)

            for hero, slot_index in duplicates_to_replace:
                valid_replacement_classes = [
                    wc for wc in all_weapons
                    if wc not in equipped_weapon_classes
                    and getattr(wc, 'group', 0) in ALLOWED_GROUPS_PER_SLOT[slot_index]
                ]
                if valid_replacement_classes:
                    new_weapon_class = random.choice(valid_replacement_classes)
                    hero.weapons[slot_index] = new_weapon_class()
                    equipped_weapon_classes.add(new_weapon_class)

            child_team = {"heroes": child_heroes, "dragons": []}

            # --- 4. MUTATION ---
            if random.random() < 0.10:
                mutated_hero = random.choice(child_team["heroes"])
                slot_to_mutate = random.randint(0, 2)

                old_weapon_class = type(mutated_hero.weapons[slot_to_mutate])
                current_equipped = {type(w) for h in child_team["heroes"] for w in h.weapons if w is not None} - {old_weapon_class}

                valid_mutations = [
                    wc for wc in all_weapons
                    if wc not in current_equipped
                    and getattr(wc, 'group', 0) in ALLOWED_GROUPS_PER_SLOT[slot_to_mutate]
                ]

                if valid_mutations:
                    new_weapon_class = random.choice(valid_mutations)
                    mutated_hero.weapons[slot_to_mutate] = new_weapon_class()

            new_population.append(child_team)

        population = new_population

    print("\n=== OPTIMISATION TERMINÉE ===")
    # On retourne le meilleur ABSOLU, pas juste la dernière génération
    # On retourne le meilleur ABSOLU, pas juste la dernière génération
    print(f"Dégâts max trouvés : {all_time_best_score:,.0f}")
    for hero in all_time_best_team["heroes"]:
        weapon_names = [w.name for w in hero.weapons if w is not None]
        print(f"- {hero.name} (Armes: " + ", ".join(weapon_names) + ")")

    return all_time_best_team

# ==========================================
# 3. LANCEMENT DU SCRIPT
# ==========================================
if __name__ == "__main__":
    from char import Hero

    class GenericHero(Hero):
        def __init__(self, name="Héros Générique"):
            super().__init__(name=name, hp=5000000, attack=80000, armor=3000, speed=1000)
        def use_active_skill(self, enemies, allies):
            return (self.base_attack * self.attack_multiplier) * 3.0

    class HeroD(GenericHero):
        def __init__(self): super().__init__("Héros D")

    class HeroE(GenericHero):
        def __init__(self): super().__init__("Héros E")

    # IMPORTANT : catalogue de CLASSES (pas d'instances)
    catalogue_hero_classes = [Masamune, Spekkio, Benji, Chancer, Laguna, Zemus, Zura, HeroE]

    def create_dummy_weapon_class(weapon_name, grp):
        class DummyWeapon:
            group = grp
            def __init__(self): self.name = weapon_name
            def on_battle_start(self, fighter): pass
            def on_round_start(self, fighter): pass
            def on_basic_attack(self, fighter): pass
            def on_round_end(self, fighter, round_number): pass
            def modify_damage_dealt(self, fighter, target, current_damage): return current_damage
        DummyWeapon.__name__ = weapon_name  # Pour que type() soit unique par arme
        return DummyWeapon

    catalogue_weapons = [
        Weapon_Katar, Weapon_Shuriken, Weapon_Sai, Weapon_Khopesh, Weapon_Nunchucks,
        Weapon_Katana, Weapon_Pipe, Weapon_Tomahawk, Weapon_FanAxe, Weapon_Spear,
        Weapon_Dart, Weapon_Kusarigama, Weapon_Haladie, Weapon_Claw, Weapon_Bomb,
        Weapon_Knuckles, Weapon_Kunai, Weapon_CobraStaff, Weapon_Bow, Weapon_Knife
    ]
    for i in range(2):
        catalogue_weapons.append(create_dummy_weapon_class(f"Random_weapon_g1_{i}", 1))
        catalogue_weapons.append(create_dummy_weapon_class(f"Random_weapon_g2_{i}", 2))
        catalogue_weapons.append(create_dummy_weapon_class(f"Random_weapon_g3_{i}", 3))

    run_genetic_optimizer(catalogue_hero_classes, catalogue_weapons, generations=100, population_size=500)