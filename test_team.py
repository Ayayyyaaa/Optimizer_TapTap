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
from combat_engine import simulate_team, simulate_team_with_breakdown

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

myteam = {
        0: {"fighter_cls": Zura, "weapons": [Weapon_Knuckles, Weapon_Cobra, Weapon_Dart], "dragons": [Tianlu, Yamata]},
        1: {"fighter_cls": Ruby, "weapons": [Weapon_Pipe, Weapon_Bomb, Weapon_Bow], "dragons": [Toronbo, Matsu]},
        2: {"fighter_cls": Zemus, "weapons": [Weapon_Sai, Weapon_Shuriken, Weapon_Spear], "dragons": [Yamata, Naga]},
        3: {"fighter_cls": Spekkio, "weapons": [Weapon_Nunchucks, Weapon_Katana, Weapon_Katar], "dragons": [Zhulong, Naga]},
        4: {"fighter_cls": Laguna, "weapons": [Weapon_Kusarigama, Weapon_Haladie, Weapon_Claw], "dragons": [Toronbo, Mingshe]},
        5: {"fighter_cls": Chancer, "weapons": [Weapon_Knife, Weapon_Kunai, Weapon_Khopesh], "dragons": [Naga, Dabei]},
    }
team = {
        0: {"fighter_cls": Zura, "weapons": [Weapon_Kusarigama, Weapon_Cobra, Weapon_Kunai], "dragons": [Zhulong, Naga]},
        1: {"fighter_cls": Chancer, "weapons": [Weapon_Katar, Weapon_Katana, Weapon_Khopesh], "dragons": [Toronbo, Matsu]},
        2: {"fighter_cls": Zemus, "weapons": [Weapon_Knife, Weapon_Haladie, Weapon_FanAxe], "dragons": [Toronbo, Dabei]},
        3: {"fighter_cls": Terryx, "weapons": [Weapon_Nunchucks, Weapon_Dart, Weapon_Claw], "dragons": [Toronbo, Yinglong]},
        4: {"fighter_cls": Laguna, "weapons": [Weapon_Knuckles, Weapon_Bow, Weapon_Bomb], "dragons": [Yamata, Mingshe]},
        5: {"fighter_cls": Teepo, "weapons": [Weapon_Sai, Weapon_Shuriken, Weapon_Tomahawk], "dragons": [Zhulong, Yinglong]},
    }
teamtest = {
        0: {"fighter_cls": Zura, "weapons": [Weapon_Kusarigama, Weapon_Cobra, Weapon_Kunai], "dragons": [Toronbo, Mingshe]},
        1: {"fighter_cls": Terryx, "weapons": [Weapon_Knuckles, Weapon_Bow, Weapon_Claw], "dragons": [Yamata, Zhulong]},
        2: {"fighter_cls": Zemus, "weapons": [Weapon_Knife, Weapon_Haladie, Weapon_FanAxe], "dragons": [Toronbo, Dabei]},
        3: {"fighter_cls": Chancer, "weapons": [Weapon_Knife, Weapon_Kunai, Weapon_Khopesh], "dragons": [Naga, Zhulong]},
        4: {"fighter_cls": Laguna, "weapons": [Weapon_Knuckles, Weapon_Dart, Weapon_Bomb], "dragons": [Toronbo, Mingshe]},
        5 :{"fighter_cls": Spekkio, "weapons": [Weapon_Katar, Weapon_Katana, Weapon_Nunchucks], "dragons": [Yinglong, Zhulong]},
    }

simulate_team(
    teamtest,
    nb_rounds=10,
    nb_simulations=1,
    boss_cls=BossDefault
)