# ═══════════════════════════════════════════════════════════════
#  CONFIG.PY  —  Inventaire du joueur & pool de personnages
# ═══════════════════════════════════════════════════════════════

from boss import BossDefault, BossAOE, BossStunner
from fighter.chancer import Chancer
from fighter.laguna import Laguna
from weapon import *
from dragons import *
from fighter.okami import Okami 
from fighter.spekkio import Spekkio
from fighter.zemus import Zemus
from fighter.saban import Saban # Ajoute ici tous tes fighters
from fighter.ruby import Ruby

# ───────────────────────────────────────────────────────────────
#  POOL DE PERSOS (les 60 disponibles)
#  Format : liste de callables (classes fighter)
#  Ex: [Spekkio, Spekkio, AutrePerso, ...]
# ───────────────────────────────────────────────────────────────
FIGHTER_POOL = [
    Spekkio,  # Remplace/duplique avec tes 60 persos réels
    Okami,
    Saban, 
    Chancer,
    Laguna,
    Zemus,
    Ruby
]

# ───────────────────────────────────────────────────────────────
#  TAILLE DE L'ÉQUIPE
# ───────────────────────────────────────────────────────────────
TEAM_SIZE = 5

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
    Weapon_FanAxe,
    Weapon_Tomahawk,
    Weapon_Bomb
]

# ───────────────────────────────────────────────────────────────
#  INVENTAIRE DRAGONS
#  Format : { ClasseDragon: nb_exemplaires }
#  Un perso ne peut pas avoir 2x le même dragon.
# ───────────────────────────────────────────────────────────────
DRAGON_INVENTORY = {
    Zhulong:  2,
    Yinglong: 2,
    Yamata:   2,
    Naga:     2,
    Tianlu:   2,
    Dabei:    3,
    Matsu:     3,
    Toronbo:   3,
    Mingshe:   3,
}

# ───────────────────────────────────────────────────────────────
#  PARAMÈTRES ALGORITHME GÉNÉTIQUE
# ───────────────────────────────────────────────────────────────
GA_CONFIG = {
    "population_size":  250,    # Individus par génération
    "generations":      80,    # Nombre de générations
    "elite_ratio":      0.10,  # Top 10% survivent directement
    "crossover_ratio":  0.70,  # 60% issus de croisement
    "mutation_rate":    0.20,  # Probabilité de mutation par gène
    "simulations":      50,     # Combats simulés par évaluation (vitesse vs précision)
    "rounds":           10,    # Tours par simulation
    "stagnation_limit": 15,    # Arrêt anticipé si pas d'amélioration après N générations
}

# ───────────────────────────────────────────────────────────────
#  BOSS CIBLE DE L'OPTIMISATION
#  Change cette ligne pour optimiser contre un boss différent :
#    BossDefault  → Training Dummy (Howler, attaques basiques)
#    BossAOE      → Warlord       (Kodiak, AoE + debuffs)
#    BossStunner  → Mindbreaker   (Crane, contrôle intensif)
# ───────────────────────────────────────────────────────────────
TARGET_BOSS = BossDefault