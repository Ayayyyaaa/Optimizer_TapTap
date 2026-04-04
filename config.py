# ═══════════════════════════════════════════════════════════════
#  CONFIG.PY  —  Inventaire du joueur & pool de personnages
# ═══════════════════════════════════════════════════════════════

from weapon import *
from dragons import *
from fighter import Spekkio  # Ajoute ici tous tes fighters

# ───────────────────────────────────────────────────────────────
#  POOL DE PERSOS (les 60 disponibles)
#  Format : liste de callables (classes fighter)
#  Ex: [Spekkio, Spekkio, AutrePerso, ...]
# ───────────────────────────────────────────────────────────────
FIGHTER_POOL = [
    Spekkio,  # Remplace/duplique avec tes 60 persos réels
]

# ───────────────────────────────────────────────────────────────
#  TAILLE DE L'ÉQUIPE
# ───────────────────────────────────────────────────────────────
TEAM_SIZE = 6

# ───────────────────────────────────────────────────────────────
#  INVENTAIRE ARMES
#  Chaque entrée = 1 exemplaire. Duplique si tu en as plusieurs.
# ───────────────────────────────────────────────────────────────
WEAPON_INVENTORY = [
    Weapon_Kusarigama,
    Weapon_Pipe,
    Weapon_Haladie,
    Weapon_Claw,
    Weapon_Knuckles,
    Weapon_Cobra,
    Weapon_Bow,
    Weapon_Nunchucks,
    Weapon_Shuriken,
    Weapon_Khopesh,
    Weapon_Katana,
    Weapon_Sai,
    Weapon_Kunai,
    Weapon_Katar,
    Weapon_Knife,
    Weapon_Dart,
    Weapon_Spear,
]

# ───────────────────────────────────────────────────────────────
#  INVENTAIRE DRAGONS
#  Format : { ClasseDragon: nb_exemplaires }
#  Un perso ne peut pas avoir 2x le même dragon.
# ───────────────────────────────────────────────────────────────
DRAGON_INVENTORY = {
    Zhulong:  2,
    Yinglong: 2,
    Yamata:   1,
    Naga:     2,
    Tianlu:   1,
}

# ───────────────────────────────────────────────────────────────
#  PARAMÈTRES ALGORITHME GÉNÉTIQUE
# ───────────────────────────────────────────────────────────────
GA_CONFIG = {
    "population_size":  80,    # Individus par génération
    "generations":      60,    # Nombre de générations
    "elite_ratio":      0.10,  # Top 10% survivent directement
    "crossover_ratio":  0.60,  # 60% issus de croisement
    "mutation_rate":    0.20,  # Probabilité de mutation par gène
    "simulations":      8,     # Combats simulés par évaluation (vitesse vs précision)
    "rounds":           10,    # Tours par simulation
    "stagnation_limit": 15,    # Arrêt anticipé si pas d'amélioration après N générations
}