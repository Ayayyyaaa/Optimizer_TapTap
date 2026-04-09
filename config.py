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
from fighter.teepo import Teepo  
from fighter.zura import Zura
from fighter.scythe import Scythe
from fighter.necro import Necro
from fighter.terryx import Terryx
from fighter.otto import Otto
from fighter.komodo import Komodo
from fighter.leene import Leene

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
    Ruby,
    Teepo, 
    Zura,
    Scythe,
    Necro,
    Terryx,
    Otto,
    Komodo,
    Leene,
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
    "population_size":  250,   # ↓ de 500 : le cache compense #250
    "generations":      175,   # ↑ de 120 : arrêt anticipé protège
    "elite_ratio":      0.15,  # ↓ de 0.15 : moins de deepcopy
    "crossover_ratio":  0.65,  # ↑ léger
    "mutation_rate":    0.20,  # ↓ de 0.25 : moins de réparations
    "simulations":      80,   # ↓ de 150 : le cache rattrape #75
    "rounds":           10,
    "stagnation_limit": 20,    # ↓ de 20 : économise ~5 générations inutiles
}

# ───────────────────────────────────────────────────────────────
#  BOSS CIBLE DE L'OPTIMISATION
#  Change cette ligne pour optimiser contre un boss différent :
#    BossDefault  → Training Dummy (Howler, attaques basiques)
#    BossAOE      → Warlord       (Kodiak, AoE + debuffs)
#    BossStunner  → Mindbreaker   (Crane, contrôle intensif)
# ───────────────────────────────────────────────────────────────
TARGET_BOSS = BossDefault