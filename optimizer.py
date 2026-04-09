# ═══════════════════════════════════════════════════════════════
#  OPTIMIZER.PY  —  Algorithme génétique pour optimisation d'équipe
#  Version optimisée :
#    • Pool de workers persistant (créé une seule fois, pas par génération)
#    • Cache de fitness (évite de réévaluer un génome déjà vu)
#    • deepcopy uniquement sur les élites (pas sur tout le génome)
#    • Croisement uniforme par slot (meilleure exploration vs point unique)
#    • Réparation dragons O(n) sans shuffle répété
# ═══════════════════════════════════════════════════════════════

import random
import copy
from collections import Counter
from multiprocessing import Pool, cpu_count
from combat_engine import simulate_team, simulate_team_with_breakdown
from config import (
    FIGHTER_POOL, TEAM_SIZE, WEAPON_INVENTORY,
    DRAGON_INVENTORY, GA_CONFIG, TARGET_BOSS
)

# ── Pré-calculs globaux ───────────────────────────────────────
DRAGON_POOL: list = []
for dragon_cls, count in DRAGON_INVENTORY.items():
    DRAGON_POOL.extend([dragon_cls] * count)

_group_map: dict[int, list[int]] = {}
for idx, w_cls in enumerate(WEAPON_INVENTORY):
    g = w_cls.group
    _group_map.setdefault(g, []).append(idx)

# ── Cache de fitness (process principal uniquement) ───────────
_fitness_cache: dict[tuple, float] = {}


def _genome_key(genome: "Genome") -> tuple:
    """Clé hashable unique pour ce génome.
    L'index i est inclus : même roster dans un ordre différent = clé différente,
    car la position (front/back) change le comportement des fighters.
    """
    return tuple(
        (i, s["fighter_idx"], tuple(s["weapon_idxs"]), tuple(s["dragon_idxs"]))
        for i, s in enumerate(genome.slots)
    )


# ═══════════════════════════════════════════════════════════════
#  GÉNOME
# ═══════════════════════════════════════════════════════════════

class Genome:
    __slots__ = ("slots", "fitness")

    def __init__(self):
        self.slots: list[dict] = []
        self.fitness: float = -1.0

    @classmethod
    def random(cls) -> "Genome":
        g = cls()
        fighter_idxs = _pick_fighters()
        weapon_alloc = _pick_weapons_for_team()
        dragon_alloc = _pick_dragons_for_team()
        for i in range(TEAM_SIZE):
            g.slots.append({
                "fighter_idx": fighter_idxs[i],
                "weapon_idxs": list(weapon_alloc[i]),
                "dragon_idxs": list(dragon_alloc[i]),
            })
        return g

    def to_team_build(self) -> dict:
        build = {}
        for i, slot in enumerate(self.slots):
            build[i] = {
                "fighter_cls": FIGHTER_POOL[slot["fighter_idx"]],
                "weapons":     [WEAPON_INVENTORY[wi] for wi in slot["weapon_idxs"]],
                "dragons":     [DRAGON_POOL[di] for di in slot["dragon_idxs"]],
                "position":    "front" if i < 3 else "back",
            }
        return build

    def evaluate(self) -> float:
        key = _genome_key(self)
        if key in _fitness_cache:
            self.fitness = _fitness_cache[key]
            return self.fitness
        cfg = GA_CONFIG
        self.fitness = simulate_team(
            self.to_team_build(),
            nb_rounds=cfg["rounds"],
            nb_simulations=cfg["simulations"],
            boss_cls=TARGET_BOSS,
        )
        _fitness_cache[key] = self.fitness
        return self.fitness

    def __repr__(self):
        return f"<Genome fitness={self.fitness:,.0f}>"


# ═══════════════════════════════════════════════════════════════
#  FONCTIONS D'ALLOCATION (contraintes)
# ═══════════════════════════════════════════════════════════════

def _pick_fighters() -> list[int]:
    idxs = list(range(len(FIGHTER_POOL)))
    if len(idxs) >= TEAM_SIZE:
        return random.sample(idxs, TEAM_SIZE)
    chosen = list(idxs)
    while len(chosen) < TEAM_SIZE:
        chosen.append(random.choice(idxs))
    return chosen


def _pick_weapons_for_team() -> list[tuple]:
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
    if len(chosen) < 3:
        remaining = [wi for wi in candidates if wi not in chosen]
        chosen += remaining[:3 - len(chosen)]
    return tuple(chosen[:3])


def _pick_dragons_for_team() -> list[tuple]:
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
    Croisement UNIFORME par slot : chaque slot est hérité de A ou B avec 50/50.
    Bien plus expressif qu'un croisement à point unique sur seulement 6 slots.
    """
    child_a = Genome()
    child_b = Genome()
    for i in range(TEAM_SIZE):
        if random.random() < 0.5:
            sa = parent_a.slots[i]
            sb = parent_b.slots[i]
        else:
            sa = parent_b.slots[i]
            sb = parent_a.slots[i]
        child_a.slots.append({
            "fighter_idx": sa["fighter_idx"],
            "weapon_idxs": list(sa["weapon_idxs"]),
            "dragon_idxs": list(sa["dragon_idxs"]),
        })
        child_b.slots.append({
            "fighter_idx": sb["fighter_idx"],
            "weapon_idxs": list(sb["weapon_idxs"]),
            "dragon_idxs": list(sb["dragon_idxs"]),
        })
    repair(child_a)
    repair(child_b)
    return child_a, child_b


def mutate(parent: Genome) -> Genome:
    """
    Mutation sans deepcopy global : on recopie manuellement les listes imbriquées.
    """
    cfg  = GA_CONFIG
    rate = cfg["mutation_rate"]
    child = Genome()
    child.slots = [
        {
            "fighter_idx": s["fighter_idx"],
            "weapon_idxs": list(s["weapon_idxs"]),
            "dragon_idxs": list(s["dragon_idxs"]),
        }
        for s in parent.slots
    ]
    for slot in child.slots:
        if random.random() < rate:
            slot["fighter_idx"] = random.randrange(len(FIGHTER_POOL))
        if random.random() < rate:
            slot["weapon_idxs"][random.randrange(3)] = random.randrange(len(WEAPON_INVENTORY))
        if random.random() < rate:
            slot["dragon_idxs"][random.randrange(2)] = random.randrange(len(DRAGON_POOL))
    repair(child)
    return child


def swap_rows(parent: Genome) -> Genome:
    """
    Mutation de repositionnement : échange un slot front (0-2) avec un slot back (3-5).
    Armes et dragons suivent le fighter dans son nouveau slot.
    Permet à l'algo d'explorer qui doit être en avant/arrière sans changer le roster.
    """
    child = Genome()
    child.slots = [
        {
            "fighter_idx": s["fighter_idx"],
            "weapon_idxs": list(s["weapon_idxs"]),
            "dragon_idxs": list(s["dragon_idxs"]),
        }
        for s in parent.slots
    ]
    front_slot = random.randrange(0, 3)
    back_slot  = random.randrange(3, TEAM_SIZE)
    child.slots[front_slot], child.slots[back_slot] = (
        child.slots[back_slot], child.slots[front_slot]
    )
    repair(child)
    return child


# ═══════════════════════════════════════════════════════════════
#  RÉPARATION DES CONTRAINTES
# ═══════════════════════════════════════════════════════════════

def repair(genome: Genome):
    _repair_fighters(genome)
    _repair_weapons(genome)
    _repair_dragons(genome)


def _repair_fighters(genome: Genome):
    used_fighters: set[int] = set()
    all_idxs = list(range(len(FIGHTER_POOL)))
    for slot in genome.slots:
        fi = slot["fighter_idx"]
        if fi not in used_fighters:
            used_fighters.add(fi)
        else:
            available = [i for i in all_idxs if i not in used_fighters]
            if available:
                new_fi = random.choice(available)
                slot["fighter_idx"] = new_fi
                used_fighters.add(new_fi)


def _repair_weapons(genome: Genome):
    used: set[int] = set()
    all_available = list(range(len(WEAPON_INVENTORY)))
    for slot in genome.slots:
        repaired = []
        used_groups_local = set()
        for wi in slot["weapon_idxs"]:
            g = WEAPON_INVENTORY[wi].group
            if wi not in used and not (g in (1, 2, 3) and g in used_groups_local):
                repaired.append(wi)
                used.add(wi)
                if g in (1, 2, 3):
                    used_groups_local.add(g)
            else:
                replacement = _find_weapon_replacement(used, used_groups_local, all_available)
                if replacement is not None:
                    repaired.append(replacement)
                    used.add(replacement)
                    rg = WEAPON_INVENTORY[replacement].group
                    if rg in (1, 2, 3):
                        used_groups_local.add(rg)
                else:
                    repaired.append(wi)
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
    """
    Version O(n) : un seul shuffle par slot, pas de tentatives répétées.
    """
    usage_count: Counter = Counter()
    for slot in genome.slots:
        repaired     = []
        slot_classes = set()
        # Pass 1 : garde les dragons valides
        for di in slot["dragon_idxs"]:
            d_cls = DRAGON_POOL[di]
            if usage_count[di] < 1 and d_cls not in slot_classes:
                repaired.append(di)
                usage_count[di] += 1
                slot_classes.add(d_cls)
        # Pass 2 : complète avec disponibles (un seul shuffle)
        if len(repaired) < 2:
            available = [
                di for di in range(len(DRAGON_POOL))
                if usage_count[di] < 1 and DRAGON_POOL[di] not in slot_classes
            ]
            random.shuffle(available)
            for di in available:
                repaired.append(di)
                usage_count[di] += 1
                slot_classes.add(DRAGON_POOL[di])
                if len(repaired) == 2:
                    break
            # Fallback absolu (ignore le stock)
            if len(repaired) < 2:
                for di in range(len(DRAGON_POOL)):
                    if DRAGON_POOL[di] not in slot_classes:
                        repaired.append(di)
                        slot_classes.add(DRAGON_POOL[di])
                        if len(repaired) == 2:
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
    cfg         = GA_CONFIG
    pop_size    = cfg["population_size"]
    generations = cfg["generations"]
    elite_n     = max(1, int(pop_size * cfg["elite_ratio"]))
    cross_n     = int(pop_size * cfg["crossover_ratio"])
    stag_limit  = cfg["stagnation_limit"]
    nb_cpus     = cpu_count()

    print(f"\n{'='*60}")
    print(f"  OPTIMISEUR GÉNÉTIQUE — Tap Force")
    print(f"{'='*60}")
    print(f"  Boss cible    : {TARGET_BOSS().name}")
    print(f"  Population : {pop_size}  |  Générations : {generations}")
    print(f"  CPU utilisés : {nb_cpus}  |  Sims/éval : {cfg['simulations']}")
    print(f"  Fighters pool : {len(FIGHTER_POOL)}  |  Équipe : {TEAM_SIZE} persos")
    print(f"  Armes : {len(WEAPON_INVENTORY)}  |  Dragons pool : {len(DRAGON_POOL)}")
    print(f"{'='*60}\n")

    # ── Génération initiale ───────────────────────────────────
    population = [Genome.random() for _ in range(pop_size)]

    # ── Pool PERSISTANT : ouvert une seule fois pour tout l'algo ─
    with Pool(nb_cpus) as pool:
        population = pool.map(_evaluate_worker, population)
        population.sort(key=lambda g: g.fitness, reverse=True)
        best_ever  = copy.deepcopy(population[0])
        stagnation = 0

        # ── Boucle évolutive ──────────────────────────────────
        for gen in range(1, generations + 1):
            next_gen = []

            # 1. Élitisme : deepcopy uniquement sur elite_n individus
            next_gen.extend(copy.deepcopy(population[:elite_n]))

            # 2. Croisement uniforme
            while len(next_gen) < elite_n + cross_n:
                pa = _tournament_select(population)
                pb = _tournament_select(population)
                ca, cb = crossover(pa, pb)
                next_gen.extend([ca, cb])

            # 3. Mutation du reste (classique + swap de ligne front/back)
            while len(next_gen) < pop_size:
                parent = _tournament_select(population)
                # 30% de chance d'échanger un fighter front ↔ back plutôt que
                # de muter ses stats — explore les positions sans changer le roster
                if random.random() < 0.30:
                    next_gen.append(swap_rows(parent))
                else:
                    next_gen.append(mutate(parent))

            next_gen = next_gen[:pop_size]

            # 4. Évaluation parallèle — élites non réévalués (fitness déjà connue)
            to_eval  = next_gen[elite_n:]
            evaluated = pool.map(_evaluate_worker, to_eval)
            next_gen  = next_gen[:elite_n] + evaluated
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

            # Nettoyage du cache toutes les 20 générations (évite fuite mémoire)
            if gen % 20 == 0 and len(_fitness_cache) > 50_000:
                _fitness_cache.clear()

            print(f"  Gen {gen:>3}/{generations}  |  "
                  f"Best : {gen_best.fitness:>15,.0f} DPS{marker}  |  "
                  f"Cache : {len(_fitness_cache):,}")

            if stagnation >= stag_limit:
                print(f"\n  Arrêt anticipé : pas d'amélioration depuis {stag_limit} générations.")
                break

    _print_results(best_ever)
    return best_ever


def _tournament_select(population: list, k: int = 4) -> Genome:
    contestants = random.sample(population, min(k, len(population)))
    return max(contestants, key=lambda g: g.fitness)


def _print_results(best: Genome):
    cfg = GA_CONFIG
    _, breakdown = simulate_team_with_breakdown(
        best.to_team_build(),
        nb_rounds=cfg["rounds"],
        nb_simulations=cfg["simulations"],
        boss_cls=TARGET_BOSS,
    )

    print(f"\n{'='*60}")
    print(f"  MEILLEUR BUILD TROUVÉ — {best.fitness:,.0f} DPS moyen")
    print(f"{'='*60}")

    for row_label, row_slots in [("▶  LIGNE AVANT  (positions 1-3)", range(0, 3)),
                                  ("▶  LIGNE ARRIÈRE (positions 4-6)", range(3, TEAM_SIZE))]:
        print(f"\n  {row_label}")
        print(f"  {'-'*50}")
        for i in row_slots:
            slot        = best.slots[i]
            fighter_cls = FIGHTER_POOL[slot["fighter_idx"]]
            weapons     = [WEAPON_INVENTORY[wi]().name for wi in slot["weapon_idxs"]]
            dragons     = [DRAGON_POOL[di].__name__ for di in slot["dragon_idxs"]]
            name        = fighter_cls.__name__
            dmg         = breakdown.get(name, {})
            direct      = dmg.get("direct", 0.0)
            dot         = dmg.get("dot",    0.0)
            orb         = dmg.get("orb",    0.0)
            total_f     = direct + dot + orb
            pct         = (total_f / best.fitness * 100) if best.fitness > 0 else 0.0
            print(f"\n    Slot {i+1} → {name}  ({total_f:,.0f} dmg — {pct:.1f}%)")
            print(f"      Direct  : {direct:>15,.0f}  |  DoT : {dot:>15,.0f}  |  Orb : {orb:>15,.0f}")
            print(f"      Armes   : {' | '.join(weapons)}")
            print(f"      Dragons : {' | '.join(dragons)}")

    print(f"\n{'='*60}\n")


# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    run_genetic_optimizer()