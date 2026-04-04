# ═══════════════════════════════════════════════════════════════
#  FIGHTER_SABAN.PY  —  Saban
# ═══════════════════════════════════════════════════════════════
#
# ═══════════════════════════════════════════════════════════════

import random
from character import Character
from debuffs import apply_debuff, apply_buff, remove_buff, has_buff, tick_buffs


class Saban:
    def __init__(self):
        self.character = Character(
            name              = "Saban",
            faction           = "Kodiak",   # à ajuster selon le jeu
            hp                = 3_496_431,
            atk               = 61_613,
            defense           = 1_990,
            spd               = 1_277,
            skill_dmg         = 0,
            block             = 0.7,
            cr                = 0.15,       # Crit Chance = 55 (image avancée)
            cd                = 1.3,
            dmg_reduce        = 0,
            control_resist    = 0,
            hit_chance        = 0,
            armor_break       = 0,
            control_precision = 0,
            stealth           = 0,
            weapon            = [],
            dragons           = [],
            pos               = 1,
        )
        self.immune   = []
        self.character._immune = self.immune
        self.position = 1

        # Compteur interne d'alliés morts (pour Last One Standing)
        self._allies_dead = 0

        # ── Passive #1 : Lust for Blood (appliquée au battle start) ──
        # HP +55%, CR +40%, SPD +80 → appliqués dans on_battle_start via weapon/dragon
        # On les applique directement ici à l'init pour que les stats soient correctes
        self.character.max_hp  = int(self.character.max_hp * 1.55)
        self.character.hp      = self.character.max_hp
        self.character.cr     += 0.40
        self.character.spd    += 80

    # ═══════════════════════════════════════════════════════════
    #  ATTAQUE DE BASE
    # ═══════════════════════════════════════════════════════════
    def basic_atk(self, enemies: list, allies: list) -> float:
        """
        Armor Shred :
        - 250% dégâts sur un ennemi de première ligne aléatoire.
        - Ignore l'armure (géré via un attribut ou dans le calcul de mitigation du moteur).
        - Réduit les chances de critique (Crit Chance) de la cible de 35% pendant 3 tours.
        """
        if not enemies:
            return 0.0

        alive_enemies = [e for e in enemies 
                         if getattr(e.character if hasattr(e, "character") else e, "is_alive", True)]
        if not alive_enemies:
            return 0.0

        # Filtre pour la première ligne (positions 1, 2, 3 généralement)
        front_line = [e for e in alive_enemies 
                      if getattr(e.character if hasattr(e, "character") else e, "pos", 4) <= 3]
        
        # S'il n'y a plus de première ligne, on tape au hasard sur ceux qui restent
        if not front_line:
            front_line = alive_enemies

        target      = random.choice(front_line)
        target_char = target.character if hasattr(target, "character") else target

        # 250% de l'ATK
        base_damage = self.character.atk * 2.50
        is_crit     = random.random() < min(1.0, self.character.cr)

        if is_crit:
            damage = base_damage * self.character.cd
        else:
            damage = base_damage

        # Application du debuff : -35% Crit Chance pour 3 tours
        # Assurez-vous que BUFF_DEFS["crit_shred"] est défini dans debuffs.py avec "stat": "cr", "delta": -0.35
        apply_debuff(target_char, "crit_shred", duration=5, source=self)

        # Modificateurs d'armes
        for w in self.character.weapon:
            damage = w.modify_damage_dealt(self.character, target_char, damage)
            w.on_basic_attack(self.character, damage)

        # Note : Pour que l'attaque "ignore l'armure", vous pouvez passer un flag à votre moteur
        # de combat ici, ou ajouter un attribut temporaire à target_char.
        setattr(self, "current_attack_ignores_armor", True) 

        return damage * self.character.attack_multiplier

    # ═══════════════════════════════════════════════════════════
    #  ULT : Revenge Trap
    # ═══════════════════════════════════════════════════════════
    def ult(self, enemies: list, allies: list) -> float:
        """
        Revenge Trap :
        - 550% dégâts aux 3 ennemis avec la plus haute ATK.
        - Réduit leur armure de 40% pour 5 tours.
        - Applique la "Revenge Mark" (Si la cible tue quelqu'un, elle subit 750% de dégâts).
        """
        if not enemies:
            return 0.0

        alive_enemies = [e for e in enemies 
                         if getattr(e.character if hasattr(e, "character") else e, "is_alive", True)]
        if not alive_enemies:
            return 0.0

        # Trie les ennemis par ATK décroissante et sélectionne les 3 plus forts
        sorted_by_atk = sorted(alive_enemies, 
                               key=lambda e: getattr(e.character if hasattr(e, "character") else e, "atk", 0), 
                               reverse=True)
        targets = sorted_by_atk[:3]

        total_damage = 0.0

        for target in targets:
            target_char = target.character if hasattr(target, "character") else target

            # ── 550% ATK, amplifié par skill_dmg ──
            damage = self.character.atk * 5.50
            damage *= (1.0 + self.character.skill_dmg)

            # Armes
            for w in self.character.weapon:
                damage = w.modify_damage_dealt(self.character, target_char, damage)

            # ── Debuff 1 : Réduction d'armure de 40% pour 5 tours ──
            # On assume que apply_debuff gère la logique de réduction en pourcentage (mode="pct")
            apply_debuff(target_char, "armor_reduction", duration=5, source=self)


            total_damage += damage * self.character.attack_multiplier

        return total_damage