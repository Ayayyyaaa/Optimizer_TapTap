# ═══════════════════════════════════════════════════════════════
#  OPTIMIZER.PY  —  Algorithme génétique pour optimisation d'équipe
# ═══════════════════════════════════════════════════════════════
#
#  POURQUOI UN ALGO GÉNÉTIQUE ?
#  ─────────────────────────────
#  Brute-force sur 60 persos × 20 armes × dragons = des milliards
#  de combinaisons. L'algo génétique explore intelligemment l'espace
#  en faisant "évoluer" une population de builds vers le meilleur score.
#
#  STRUCTURE D'UN GÉNOME (= un build d'équipe)
#  ────────────────────────────────────────────
#  Un génome encode pour chaque slot de l'équipe :
#    - l'index du fighter dans FIGHTER_POOL
#    - 3 index d'armes dans WEAPON_INVENTORY (règle de groupe respectée)
#    - 2 index de dragons dans DRAGON_INVENTORY (pas de doublon par perso)
#
#  Contraintes gérées :
#    - Unicité des fighters dans l'équipe (1 seul exemplaire par perso)
#    - Unicité des armes entre fighters
#    - Stock de dragons respecté (pas de doublon par perso, stock global)
# ═══════════════════════════════════════════════════════════════

import random
import copy
from collections import Counter
from multiprocessing import Pool, cpu_count
from combat_engine import simulate_team
from config import (
    FIGHTER_POOL, TEAM_SIZE, WEAPON_INVENTORY,
    DRAGON_INVENTORY, GA_CONFIG, TARGET_BOSS
)

# ── Pré-calculs globaux (faits une seule fois) ────────────────
# Liste à plat des dragons disponibles (avec doublons selon stock)
DRAGON_POOL = []
for dragon_cls, count in DRAGON_INVENTORY.items():
    DRAGON_POOL.extend([dragon_cls] * count)

# Index des armes groupées : group_map[g] = [idx, idx, ...]
_group_map: dict[int, list[int]] = {}
for idx, w_cls in enumerate(WEAPON_INVENTORY):
    g = w_cls.group
    _group_map.setdefault(g, []).append(idx)


# ═══════════════════════════════════════════════════════════════
#  GÉNOME
# ═══════════════════════════════════════════════════════════════

class Genome:
    """
    Encode un build complet pour TEAM_SIZE fighters.

    self.slots : list[dict] de longueur TEAM_SIZE
      {
        "fighter_idx": int,   # index dans FIGHTER_POOL
        "weapon_idxs": [int, int, int],  # index dans WEAPON_INVENTORY
        "dragon_idxs": [int, int],       # index dans DRAGON_POOL
      }
    self.fitness : float  (DPS moyen de l'équipe, -1 = non évalué)
    """

    def __init__(self):
        self.slots: list[dict] = []
        self.fitness: float = -1.0

    # ── Construction aléatoire valide ─────────────────────────
    @classmethod
    def random(cls) -> "Genome":
        g = cls()
        fighter_idxs = _pick_fighters()
        weapon_alloc = _pick_weapons_for_team()   # liste de 3-tuples d'index
        dragon_alloc = _pick_dragons_for_team()   # liste de 2-tuples d'index

        for i in range(TEAM_SIZE):
            g.slots.append({
                "fighter_idx": fighter_idxs[i],
                "weapon_idxs": list(weapon_alloc[i]),
                "dragon_idxs": list(dragon_alloc[i]),
            })
        return g

    # ── Conversion vers dict utilisable par fight.py ─────────
    def to_team_build(self) -> dict:
        build = {}
        for i, slot in enumerate(self.slots):
            build[i] = {
                "fighter_cls": FIGHTER_POOL[slot["fighter_idx"]],
                "weapons":     [WEAPON_INVENTORY[wi] for wi in slot["weapon_idxs"]],
                "dragons":     [DRAGON_POOL[di] for di in slot["dragon_idxs"]],
            }
        return build

    # ── Évaluation ───────────────────────────────────────────
    def evaluate(self) -> float:
        cfg = GA_CONFIG
        self.fitness = simulate_team(
            self.to_team_build(),
            nb_rounds=cfg["rounds"],
            nb_simulations=cfg["simulations"],
            boss_cls=TARGET_BOSS,
        )
        return self.fitness

    def __repr__(self):
        return f"<Genome fitness={self.fitness:,.0f}>"


# ═══════════════════════════════════════════════════════════════
#  FONCTIONS D'ALLOCATION (contraintes)
# ═══════════════════════════════════════════════════════════════

def _pick_fighters() -> list[int]:
    """
    Tire TEAM_SIZE fighters DISTINCTS dans FIGHTER_POOL.
    Chaque fighter ne peut apparaître qu'une seule fois dans l'équipe.
    Si le pool est plus petit que TEAM_SIZE, on remplit avec des doublons
    en dernier recours (cas extrême, à éviter en pratique).
    """
    idxs = list(range(len(FIGHTER_POOL)))
    if len(idxs) >= TEAM_SIZE:
        return random.sample(idxs, TEAM_SIZE)
    else:
        # Pool trop petit — on prend tous les fighters disponibles
        # puis on complète avec des doublons des moins utilisés
        chosen = list(idxs)
        while len(chosen) < TEAM_SIZE:
            chosen.append(random.choice(idxs))
        return chosen


def _pick_weapons_for_team() -> list[tuple]:
    """
    Alloue 3 armes par fighter (règle de groupe : max 1 par groupe 1/2/3)
    en respectant l'unicité globale des armes.
    Retourne une liste de TEAM_SIZE tuples d'index.
    """
    available = list(range(len(WEAPON_INVENTORY)))
    random.shuffle(available)
    allocations = []

    for _ in range(TEAM_SIZE):
        combo = _draw_valid_weapon_combo(available)
        for wi in combo:
            available.remove(wi)
        allocations.append(combo)

    return allocations


def _draw_valid_weapon_combo(available: list[int]) -> tuple:
    """
    Tire 3 armes parmi available sans doublon de groupe (groupes 1, 2, 3).
    Groupe 4 = pas de contrainte de doublon entre elles.
    """
    used_groups = set()
    chosen = []
    candidates = available.copy()
    random.shuffle(candidates)

    for wi in candidates:
        g = WEAPON_INVENTORY[wi].group
        if g in (1, 2, 3) and g in used_groups:
            continue
        chosen.append(wi)
        if g in (1, 2, 3):
            used_groups.add(g)
        if len(chosen) == 3:
            break

    # Fallback : si pas assez d'armes valides, on complète sans contrainte
    if len(chosen) < 3:
        remaining = [wi for wi in candidates if wi not in chosen]
        chosen += remaining[:3 - len(chosen)]

    return tuple(chosen[:3])


def _pick_dragons_for_team() -> list[tuple]:
    """
    Alloue 2 dragons distincts par fighter en respectant le stock global.
    Un perso ne peut pas avoir 2x le même dragon.
    """
    stock = list(range(len(DRAGON_POOL)))
    random.shuffle(stock)
    allocations = []

    for _ in range(TEAM_SIZE):
        combo = _draw_valid_dragon_combo(stock)
        for di in combo:
            stock.remove(di)
        allocations.append(combo)

    return allocations


def _draw_valid_dragon_combo(stock: list[int]) -> tuple:
    """Tire 2 dragons distincts (pas la même classe sur le même perso)."""
    candidates = stock.copy()
    random.shuffle(candidates)
    chosen = []
    chosen_classes = set()

    for di in candidates:
        dragon_cls = DRAGON_POOL[di]
        if dragon_cls in chosen_classes:
            continue
        chosen.append(di)
        chosen_classes.add(dragon_cls)
        if len(chosen) == 2:
            break

    if len(chosen) < 2:
        remaining = [di for di in candidates if di not in chosen]
        chosen += remaining[:2 - len(chosen)]

    return tuple(chosen[:2])


# ═══════════════════════════════════════════════════════════════
#  OPÉRATEURS GÉNÉTIQUES
# ═══════════════════════════════════════════════════════════════

def crossover(parent_a: Genome, parent_b: Genome) -> tuple["Genome", "Genome"]:
    """
    Croisement à point unique sur les slots.
    Les deux enfants héritent de blocs entiers de slots.
    Les contraintes (unicité fighters/armes/dragons) sont réparées après.
    """
    point = random.randint(1, TEAM_SIZE - 1)

    child_a = Genome()
    child_b = Genome()

    child_a.slots = (copy.deepcopy(parent_a.slots[:point]) +
                     copy.deepcopy(parent_b.slots[point:]))
    child_b.slots = (copy.deepcopy(parent_b.slots[:point]) +
                     copy.deepcopy(parent_a.slots[point:]))

    repair(child_a)
    repair(child_b)
    return child_a, child_b


def mutate(parent: Genome) -> Genome:
    """
    Mutation aléatoire sur un génome.
    Chaque gène (fighter, arme, dragon) a cfg['mutation_rate'] de chance de muter.
    Les contraintes sont réparées après.
    """
    cfg  = GA_CONFIG
    rate = cfg["mutation_rate"]
    child = copy.deepcopy(parent)
    child.fitness = -1.0

    for slot in child.slots:
        # Mutation du fighter
        if random.random() < rate:
            slot["fighter_idx"] = random.randrange(len(FIGHTER_POOL))

        # Mutation d'une arme aléatoire
        if random.random() < rate:
            weapon_to_mutate = random.randrange(3)
            slot["weapon_idxs"][weapon_to_mutate] = random.randrange(len(WEAPON_INVENTORY))

        # Mutation d'un dragon aléatoire
        if random.random() < rate:
            dragon_to_mutate = random.randrange(2)
            slot["dragon_idxs"][dragon_to_mutate] = random.randrange(len(DRAGON_POOL))

    repair(child)
    return child


# ═══════════════════════════════════════════════════════════════
#  RÉPARATION DES CONTRAINTES
# ═══════════════════════════════════════════════════════════════

def repair(genome: Genome):
    """
    Répare les violations de contraintes après crossover/mutation :
    - Unicité des fighters dans l'équipe (UN SEUL exemplaire par perso)
    - Unicité des armes entre fighters
    - Stock de dragons respecté
    - Pas de doublon de dragon sur le même perso
    - Règle de groupe des armes par perso
    """
    _repair_fighters(genome)   # ← NOUVEAU : unicité des persos
    _repair_weapons(genome)
    _repair_dragons(genome)


def _repair_fighters(genome: Genome):
    """
    Garantit qu'un même fighter n'apparaît qu'une seule fois dans l'équipe.
    Les doublons sont remplacés par des fighters non encore utilisés,
    tirés aléatoirement dans FIGHTER_POOL.
    """
    used_fighters: set[int] = set()
    all_idxs = list(range(len(FIGHTER_POOL)))

    for slot in genome.slots:
        fi = slot["fighter_idx"]
        if fi not in used_fighters:
            used_fighters.add(fi)
        else:
            # Ce fighter est déjà dans l'équipe → on cherche un remplaçant
            available = [i for i in all_idxs if i not in used_fighters]
            if available:
                new_fi = random.choice(available)
                slot["fighter_idx"] = new_fi
                used_fighters.add(new_fi)
            else:
                # Pool épuisé (pool < TEAM_SIZE) : on garde le doublon en dernier recours
                # et on n'ajoute pas à used_fighters pour permettre d'autres slots
                pass


def _repair_weapons(genome: Genome):
    """Résout les conflits d'armes dupliquées entre fighters."""
    used: set[int] = set()
    all_available = list(range(len(WEAPON_INVENTORY)))

    for slot in genome.slots:
        repaired = []
        used_groups_local = set()

        for wi in slot["weapon_idxs"]:
            g = WEAPON_INVENTORY[wi].group
            duplicate_global = wi in used
            duplicate_group  = g in (1, 2, 3) and g in used_groups_local

            if not duplicate_global and not duplicate_group:
                repaired.append(wi)
                used.add(wi)
                if g in (1, 2, 3):
                    used_groups_local.add(g)
            else:
                # Cherche un remplaçant valide
                replacement = _find_weapon_replacement(used, used_groups_local, all_available)
                if replacement is not None:
                    repaired.append(replacement)
                    used.add(replacement)
                    rg = WEAPON_INVENTORY[replacement].group
                    if rg in (1, 2, 3):
                        used_groups_local.add(rg)
                else:
                    repaired.append(wi)  # on garde en dernier recours

        slot["weapon_idxs"] = repaired


def _find_weapon_replacement(used: set, used_groups: set, all_available: list) -> int | None:
    candidates = [wi for wi in all_available if wi not in used]
    random.shuffle(candidates)
    for wi in candidates:
        g = WEAPON_INVENTORY[wi].group
        if g not in (1, 2, 3) or g not in used_groups:
            return wi
    return None


def _repair_dragons(genome: Genome):
    """Répare les violations de stock de dragons et doublons par slot."""
    usage_count: Counter = Counter()

    for slot in genome.slots:
        repaired = []
        slot_classes: set = set()

        # Pass 1: valide les dragons existants
        for di in slot["dragon_idxs"]:
            d_cls = DRAGON_POOL[di]
            if usage_count[di] < 1 and d_cls not in slot_classes:
                repaired.append(di)
                usage_count[di] += 1
                slot_classes.add(d_cls)

        # Pass 2: complète jusqu'à 2 dragons
        attempts = 0
        while len(repaired) < 2 and attempts < 50:
            attempts += 1
            replacement = _find_dragon_replacement(usage_count, slot_classes)
            if replacement is not None:
                repaired.append(replacement)
                usage_count[replacement] += 1
                slot_classes.add(DRAGON_POOL[replacement])
            else:
                # Fallback: ignore le stock, évite juste les doublons par slot
                candidates = [di for di in range(len(DRAGON_POOL))
                              if DRAGON_POOL[di] not in slot_classes]
                if candidates:
                    di = random.choice(candidates)
                    repaired.append(di)
                    usage_count[di] += 1
                    slot_classes.add(DRAGON_POOL[di])
                else:
                    repaired.append(random.randint(0, len(DRAGON_POOL) - 1))
                break

        slot["dragon_idxs"] = repaired[:2]


def _find_dragon_replacement(usage_count: Counter, slot_classes: set) -> int | None:
    candidates = list(range(len(DRAGON_POOL)))
    random.shuffle(candidates)
    for di in candidates:
        if usage_count[di] < 1 and DRAGON_POOL[di] not in slot_classes:
            return di
    return None


# ═══════════════════════════════════════════════════════════════
#  WORKER MULTIPROCESSING
# ═══════════════════════════════════════════════════════════════

def _evaluate_worker(genome: Genome) -> Genome:
    genome.evaluate()
    return genome


# ═══════════════════════════════════════════════════════════════
#  ALGORITHME GÉNÉTIQUE PRINCIPAL
# ═══════════════════════════════════════════════════════════════

def run_genetic_optimizer():
    cfg = GA_CONFIG
    pop_size    = cfg["population_size"]
    generations = cfg["generations"]
    elite_n     = max(1, int(pop_size * cfg["elite_ratio"]))
    cross_n     = int(pop_size * cfg["crossover_ratio"])
    stag_limit  = cfg["stagnation_limit"]
    nb_cpus     = cpu_count()

    print(f"\n{'═'*60}")
    print(f"  OPTIMISEUR GÉNÉTIQUE — Tap Force")
    print(f"{'═'*60}")
    print(f"  Boss cible    : {TARGET_BOSS().name}")
    print(f"  Population : {pop_size}  |  Générations : {generations}")
    print(f"  CPU utilisés : {nb_cpus}  |  Sims/éval : {cfg['simulations']}")
    print(f"  Fighters pool : {len(FIGHTER_POOL)}  |  Équipe : {TEAM_SIZE} persos")
    print(f"  Armes : {len(WEAPON_INVENTORY)}  |  Dragons pool : {len(DRAGON_POOL)}")
    print(f"{'═'*60}\n")

    # ── Génération initiale ───────────────────────────────────
    population = [Genome.random() for _ in range(pop_size)]

    with Pool(nb_cpus) as pool:
        population = pool.map(_evaluate_worker, population)

    population.sort(key=lambda g: g.fitness, reverse=True)
    best_ever   = copy.deepcopy(population[0])
    stagnation  = 0

    # ── Boucle évolutive ─────────────────────────────────────
    for gen in range(1, generations + 1):
        next_gen = []

        # 1. Élitisme : les meilleurs survivent directement
        next_gen.extend(copy.deepcopy(population[:elite_n]))

        # 2. Croisement : sélection par tournoi
        while len(next_gen) < elite_n + cross_n:
            pa = _tournament_select(population)
            pb = _tournament_select(population)
            ca, cb = crossover(pa, pb)
            next_gen.extend([ca, cb])

        # 3. Mutation sur le reste
        while len(next_gen) < pop_size:
            parent = _tournament_select(population)
            next_gen.append(mutate(parent))

        next_gen = next_gen[:pop_size]

        # 4. Évaluation parallèle (seulement les non-élites)
        to_eval = next_gen[elite_n:]
        with Pool(nb_cpus) as pool:
            evaluated = pool.map(_evaluate_worker, to_eval)
        next_gen = next_gen[:elite_n] + evaluated

        next_gen.sort(key=lambda g: g.fitness, reverse=True)
        population = next_gen

        # 5. Suivi convergence
        gen_best = population[0]
        if gen_best.fitness > best_ever.fitness:
            best_ever  = copy.deepcopy(gen_best)
            stagnation = 0
            marker = " ★ nouveau record"
        else:
            stagnation += 1
            marker = f" (stagnation {stagnation}/{stag_limit})"

        print(f"  Génération {gen:>3}/{generations}  |  "
              f"Meilleur : {gen_best.fitness:>15,.0f} DPS{marker}")

        if stagnation >= stag_limit:
            print(f"\n  Arrêt anticipé : pas d'amélioration depuis {stag_limit} générations.")
            break

    # ── Résultat final ────────────────────────────────────────
    _print_results(best_ever)
    return best_ever


def _tournament_select(population: list, k: int = 4) -> Genome:
    """Sélection par tournoi : on tire k individus et on garde le meilleur."""
    contestants = random.sample(population, min(k, len(population)))
    return max(contestants, key=lambda g: g.fitness)


def _print_results(best: Genome):
    print(f"\n{'═'*60}")
    print(f"  MEILLEUR BUILD TROUVÉ — {best.fitness:,.0f} DPS moyen")
    print(f"{'═'*60}")
    for i, slot in enumerate(best.slots):
        fighter_cls = FIGHTER_POOL[slot["fighter_idx"]]
        weapons     = [WEAPON_INVENTORY[wi]().name for wi in slot["weapon_idxs"]]
        dragons     = [DRAGON_POOL[di].__name__ for di in slot["dragon_idxs"]]
        print(f"\n  Perso {i+1} : {fighter_cls.__name__}")
        print(f"    Armes   : {' | '.join(weapons)}")
        print(f"    Dragons : {' | '.join(dragons)}")
    print(f"\n{'═'*60}\n")


# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    run_genetic_optimizer()