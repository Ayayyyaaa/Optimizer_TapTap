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
#  Les contraintes (unicité armes, stock dragons) sont gérées à la
#  construction et à la réparation post-mutation/croisement.
# ═══════════════════════════════════════════════════════════════

import random
import copy
from collections import Counter
from multiprocessing import Pool, cpu_count
from fight import simulate_team
from config import (
    FIGHTER_POOL, TEAM_SIZE, WEAPON_INVENTORY,
    DRAGON_INVENTORY, GA_CONFIG
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
        )
        return self.fitness

    def __repr__(self):
        return f"<Genome fitness={self.fitness:,.0f}>"


# ═══════════════════════════════════════════════════════════════
#  FONCTIONS D'ALLOCATION (contraintes)
# ═══════════════════════════════════════════════════════════════

def _pick_fighters() -> list[int]:
    """Tire TEAM_SIZE fighters distincts dans FIGHTER_POOL."""
    idxs = list(range(len(FIGHTER_POOL)))
    if len(idxs) < TEAM_SIZE:
        # Pool trop petit : on autorise les doublons
        return [random.choice(idxs) for _ in range(TEAM_SIZE)]
    return random.sample(idxs, TEAM_SIZE)


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
        cls = type(DRAGON_POOL[di]) if not isinstance(DRAGON_POOL[di], type) else DRAGON_POOL[di]
        # DRAGON_POOL contient des classes, pas des instances
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
    Les contraintes (unicité armes/dragons) sont réparées après.
    """
    point = random.randint(1, TEAM_SIZE - 1)

    child_a = Genome()
    child_b = Genome()

    child_a.slots = (copy.deepcopy(parent_a.slots[:point]) +
                     copy.deepcopy(parent_b.slots[point:]))
    child_b.slots = (copy.deepcopy(parent_b.slots[:point]) +
                     copy.deepcopy(parent_a.slots[point:]))

    _repair(child_a)
    _repair(child_b)
    return child_a, child_b


def mutate(genome: Genome) -> Genome:
    """
    Mutation : pour chaque slot, avec probabilité mutation_rate,
    on remplace aléatoirement le fighter, une arme, ou un dragon.
    """
    rate = GA_CONFIG["mutation_rate"]
    mutant = copy.deepcopy(genome)

    for slot in mutant.slots:
        if random.random() < rate:
            slot["fighter_idx"] = random.randint(0, len(FIGHTER_POOL) - 1)
        if random.random() < rate and len(slot["weapon_idxs"]) > 0:
            pos = random.randint(0, len(slot["weapon_idxs"]) - 1)
            slot["weapon_idxs"][pos] = random.randint(0, len(WEAPON_INVENTORY) - 1)
        if random.random() < rate and len(slot["dragon_idxs"]) > 0:
            pos = random.randint(0, len(slot["dragon_idxs"]) - 1)
            slot["dragon_idxs"][pos] = random.randint(0, len(DRAGON_POOL) - 1)

    _repair(mutant)
    return mutant


def _repair(genome: Genome):
    """
    Répare les violations de contraintes après crossover/mutation :
    - Unicité des armes entre fighters
    - Stock de dragons respecté
    - Pas de doublon de dragon sur le même perso
    - Règle de groupe des armes par perso
    """
    _repair_weapons(genome)
    _repair_dragons(genome)


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
    # Repairs dragon stock violations and per-slot duplicates.
    # Always guarantees exactly 2 dragons per slot.
    usage_count: Counter = Counter()

    for slot in genome.slots:
        repaired = []
        slot_classes: set = set()

        # Pass 1: validate existing dragons
        for di in slot["dragon_idxs"]:
            d_cls = DRAGON_POOL[di]
            if usage_count[di] < 1 and d_cls not in slot_classes:
                repaired.append(di)
                usage_count[di] += 1
                slot_classes.add(d_cls)

        # Pass 2: fill up to 2
        attempts = 0
        while len(repaired) < 2 and attempts < 50:
            attempts += 1
            replacement = _find_dragon_replacement(usage_count, slot_classes)
            if replacement is not None:
                repaired.append(replacement)
                usage_count[replacement] += 1
                slot_classes.add(DRAGON_POOL[replacement])
            else:
                # Fallback: ignore stock, just avoid per-slot duplicate
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