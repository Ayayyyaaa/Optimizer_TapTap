# ═══════════════════════════════════════════════════════════════
#  BOSS.PY  —  Classe Boss configurable
# ═══════════════════════════════════════════════════════════════

import random
from debuffs import apply_debuff, has_debuff, CONTROL_DEBUFFS

# Factions (importé depuis data.py si dispo, sinon redéfini ici)
try:
    from data import factions as FACTION_COUNTER
except ImportError:
    FACTION_COUNTER = {}


class Boss:
    """
    Boss configurable. Attaque chaque tour, peut appliquer des debuffs.

    Paramètres principaux :
      name        : str
      faction     : str   (ex: "Howler")
      hp          : int
      atk         : int
      defense     : float (valeur brute, réduit les dégâts reçus)
      spd         : int
      cr          : float (crit rate, 0.0 – 1.0)
      cd          : float (crit damage multiplier, ex: 1.5)
      hit_chance  : float (0.0 – 1.0, chance de toucher)
      dmg_reduce  : float (réduction % des dégâts reçus)
      atk_pattern : list[dict]
        Chaque entrée = une attaque du pattern, utilisée en rotation :
        {
          "name"       : str,
          "multiplier" : float,   # dégâts = atk * multiplier
          "aoe"        : bool,    # touche tous les alliés si True
          "debuffs"    : [        # liste de debuffs à appliquer sur les cibles
              {"type": "stun", "chance": 0.3, "duration": 1},
              ...
          ],
        }
    """

    def __init__(
        self,
        name:        str   = "Boss",
        faction:     str   = "Howler",
        hp:          int   = 5_000_000,
        atk:         int   = 50_000,
        defense:     float = 1000.0,
        spd:         int   = 900,
        cr:          float = 0.20,
        cd:          float = 1.50,
        hit_chance:  float = 0.90,
        dmg_reduce:  float = 0.10,
        atk_pattern: list  = None,
    ):
        self.name       = name
        self.faction    = faction
        self.max_hp     = hp
        self.hp         = hp
        self.base_atk   = atk
        self.atk        = atk
        self.base_defense = defense
        self.defense    = defense
        self.spd        = spd
        self.cr         = cr
        self.cd         = cd
        self.hit_chance = hit_chance
        self.dmg_reduce = dmg_reduce
        self.is_alive   = True
        self.is_stunned = False
        self.debuffs    = []
        self.buffs      = []
        self.control_resist = 0.0
        self._immune    = []

        # Stats reçues (pour calcul dégâts entrants)
        self.basic_dmg_taken = 0.0   # +X% dégâts basic reçus (frozen)
        self.skill_dmg_taken = 0.0   # +X% dégâts skill reçus (petrified)
        self.heal_effect     = 1.0

        # Pattern d'attaque : si non fourni, une attaque basique
        self.atk_pattern = atk_pattern or [
            {
                "name": "Basic Attack",
                "multiplier": 1.5,
                "aoe": False,
                "debuffs": [],
            }
        ]
        self._pattern_index = 0

    # ── Attaque du boss ───────────────────────────────────────
    def act(self, allies: list) -> float:
        """
        Le boss joue son tour.
        allies : liste de fighters (objets avec .character).
        Retourne les dégâts totaux infligés (pour log).
        """
        if not self.is_alive or self.is_stunned:
            return 0.0

        alive_allies = [a for a in allies if a.character.is_alive]
        if not alive_allies:
            return 0.0

        attack = self.atk_pattern[self._pattern_index % len(self.atk_pattern)]
        self._pattern_index += 1

        targets = alive_allies if attack.get("aoe") else [random.choice(alive_allies)]
        total_dmg = 0.0

        for fighter in targets:
            char = fighter.character

            # Vérification hit_chance vs evasion du perso
            evasion = max(0.0, 1.0 - getattr(char, "hit_chance", 0.15))
            if random.random() < evasion:
                continue  # esquive

            # Calcul dégât brut
            raw = self.atk * attack["multiplier"]

            # Critique
            if random.random() < self.cr:
                raw *= self.cd

            # Application
            dealt = _apply_incoming_damage(raw, self, char, skill=False)
            total_dmg += dealt

            # Application des debuffs de l'attaque
            for debuff_def in attack.get("debuffs", []):
                if random.random() < debuff_def.get("chance", 1.0):
                    apply_debuff(char, debuff_def["type"], debuff_def["duration"], source=self)

        return total_dmg

    def take_damage(self, raw_damage: float, attacker_char, is_skill: bool = False) -> float:
        """
        Reçoit des dégâts de la part d'un fighter.
        Applique : armor, dmg_reduce, true_dmg, faction bonus, block.
        Retourne les dégâts effectivement subis.
        """
        if not self.is_alive:
            return 0.0

        dmg = _apply_incoming_damage(raw_damage, attacker_char, self, skill=is_skill)
        self.hp -= dmg

        if self.hp <= 0:
            self.hp = 0
            self.is_alive = False

        return dmg


# ═══════════════════════════════════════════════════════════════
#  BOSSES PRÉDÉFINIS (exemples)
# ═══════════════════════════════════════════════════════════════

class BossDefault(Boss):
    """Boss standard — pas de mecanique spéciale."""
    def __init__(self):
        super().__init__(
            name        = "Training Dummy",
            faction     = "Cobra",
            hp          = 9_999_999_999,
            atk         = 1_000,
            defense     = 800,
            spd         = 800,
            cr          = 0.15,
            cd          = 1.50,
            hit_chance  = 0.85,
            dmg_reduce  = 0,
            atk_pattern = [
                {"name": "Slash",      "multiplier": 1.5, "aoe": False, "debuffs": []},
                {"name": "Heavy Blow", "multiplier": 2.2, "aoe": False,
                 "debuffs": [{"type": "bleeding", "chance": 0.4, "duration": 3}]},
            ],
        )


class BossAOE(Boss):
    """Boss qui alterne attaque simple et AoE avec debuffs."""
    def __init__(self):
        super().__init__(
            name        = "Warlord",
            faction     = "Kodiak",
            hp          = 80_000_000,
            atk         = 60_000,
            defense     = 1200,
            spd         = 950,
            cr          = 0.25,
            cd          = 1.75,
            hit_chance  = 0.90,
            dmg_reduce  = 0.10,
            atk_pattern = [
                {"name": "Strike",    "multiplier": 1.8, "aoe": False,
                 "debuffs": [{"type": "burning",  "chance": 0.5, "duration": 2}]},
                {"name": "Quake",     "multiplier": 1.2, "aoe": True,
                 "debuffs": [{"type": "taunted",  "chance": 0.3, "duration": 2}]},
                {"name": "Ice Wave",  "multiplier": 1.5, "aoe": True,
                 "debuffs": [{"type": "frozen",   "chance": 0.4, "duration": 1},
                              {"type": "frostbite","chance": 0.3, "duration": 2}]},
            ],
        )


class BossStunner(Boss):
    """Boss spécialisé dans le contrôle."""
    def __init__(self):
        super().__init__(
            name        = "Mindbreaker",
            faction     = "Crane",
            hp          = 40_000_000,
            atk         = 55_000,
            defense     = 600,
            spd         = 1100,
            cr          = 0.30,
            cd          = 2.00,
            hit_chance  = 0.95,
            dmg_reduce  = 0.0,
            atk_pattern = [
                {"name": "Paralyze",  "multiplier": 1.2, "aoe": False,
                 "debuffs": [{"type": "stun",      "chance": 0.45, "duration": 1}]},
                {"name": "Petrify",   "multiplier": 1.4, "aoe": False,
                 "debuffs": [{"type": "petrified", "chance": 0.60, "duration": 2}]},
                {"name": "Poison Nova","multiplier": 1.0, "aoe": True,
                 "debuffs": [{"type": "poisoned",  "chance": 0.70, "duration": 3}]},
            ],
        )


# ═══════════════════════════════════════════════════════════════
#  FORMULE DE DÉGÂTS CENTRALISÉE
# ═══════════════════════════════════════════════════════════════

def _apply_incoming_damage(
    raw_damage:     float,
    attacker,               # Character ou Boss (source)
    defender,               # Character ou Boss (cible)
    skill:          bool = False,
) -> float:
    """
    Calcule les dégâts effectifs reçus par defender.

    Ordre d'application :
      1. True damage (bypass armor & dmg_reduce)
      2. Armor (réduction flat)
      3. Armor break de l'attaquant
      4. dmg_reduce du défenseur
      5. Bonus de faction (+30% atk si faction favorable)
      6. Modificateurs debuffs (frozen, petrified, frostbite)
      7. Block (chance d'annuler 100% des dégâts)
    """
    from data import factions as FACTION_COUNTER

    # ── 1. True damage ───────────────────────────────────────
    true_dmg_ratio = getattr(attacker, "true_dmg", 0.0)
    # true_dmg_ratio = fraction des dégâts qui bypass les défenses
    true_part   = raw_damage * true_dmg_ratio
    normal_part = raw_damage * (1.0 - true_dmg_ratio)

    # ── 2 & 3. Armor & armor break ───────────────────────────
    armor       = max(0.0, getattr(defender, "defense", 0.0))
    armor_break = getattr(attacker, "armor_break", 0.0)
    effective_armor = armor * (1.0 - armor_break)
    # Formule : dégâts × (1 - armor / (armor + K)) où K = constante d'équilibre
    K = 3000.0
    armor_factor = 1.0 - (effective_armor / (effective_armor + K))
    normal_part *= armor_factor

    # ── 4. dmg_reduce du défenseur ───────────────────────────
    dmg_reduce = min(0.90, max(0.0, getattr(defender, "dmg_reduce", 0.0)))
    normal_part *= (1.0 - dmg_reduce)

    damage = true_part + normal_part

    # ── 5. Bonus de faction ───────────────────────────────────
    att_faction = getattr(attacker, "faction", "")
    def_faction = getattr(defender, "faction", "")
    if att_faction and FACTION_COUNTER.get(att_faction) == def_faction:
        damage *= 1.30

    # ── 6. Modificateurs de debuffs (sur le défenseur) ───────
    from debuffs import has_debuff
    if not skill and has_debuff(defender, "frozen"):
        damage *= (1.0 + getattr(defender, "basic_dmg_taken", 0.20))
    if skill and has_debuff(defender, "petrified"):
        damage *= (1.0 + getattr(defender, "skill_dmg_taken", 0.10))
    if has_debuff(defender, "frostbite") and has_debuff(defender, "frozen"):
        damage *= 3.0  # +200% = ×3 total

    # ── 7. Block ─────────────────────────────────────────────
    block_chance = max(0.0, getattr(defender, "block", 0.0))
    if random.random() < block_chance:
        return 0.0

    return max(0.0, damage)