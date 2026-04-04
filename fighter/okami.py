# ═══════════════════════════════════════════════════════════════
#  FIGHTER_OKAMI.PY  —  Okami
# ═══════════════════════════════════════════════════════════════
#
#  Skills :
#   • Lust for Blood  (Passive #1) : HP +55%, Crit Chance +40%, SPD +80
#   • Fresh Meat      (Passive #2) : Si basic attack = crit → self-heal 600% ATK
#   • Last One Standing (Passive #3) : Par allié mort → +40% base ATK & +40% Crit pour le reste du combat
#   • Werewolf Form   (Active/ULT)  : 1500% dmg sur cible aléatoire + vole 80% de son ATK pendant 4 tours
# ═══════════════════════════════════════════════════════════════

import random
from character import Character
from debuffs import apply_debuff, apply_buff, remove_buff, has_buff, tick_buffs


class Okami:
    def __init__(self):
        # ── Stats de base (image : HP 6368499, ATK 92261, DEF 3442, SPD 1443) ──
        # On prend les stats MAX (barre pleine) visibles dans l'image
        self.character = Character(
            name              = "Okami",
            faction           = "Crane",   # à ajuster selon le jeu
            hp                = 6368_499,
            atk               = 92_261,
            defense           = 3_442,
            spd               = 1_443,
            skill_dmg         = 0,
            block             = 0,
            cr                = 0.55,       # Crit Chance = 55 (image avancée)
            cd                = 1.8,
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
        if not enemies:
            return 0.0

        target      = self._pick_target(enemies)
        target_char = target.character if hasattr(target, "character") else target

        base_damage = self.character.atk * 2.50
        is_crit     = random.random() < min(1.0, self.character.cr)

        if is_crit:
            self.on_crit()
            damage = base_damage * self.character.cd

            # ── Passive #2 : Fresh Meat — heal 600% ATK on crit basic ──
            heal = self.character.atk * 6.0
            self.character.hp = min(self.character.max_hp, self.character.hp + heal)

            self.character.energy += 20
        else:
            damage = base_damage

        # Modificateurs d'armes
        for w in self.character.weapon:
            damage = w.modify_damage_dealt(self.character, target_char, damage)
            w.on_basic_attack(self.character, damage)

        return damage * self.character.attack_multiplier

    # ═══════════════════════════════════════════════════════════
    #  ULT : Werewolf Form
    # ═══════════════════════════════════════════════════════════
    def ult(self, enemies: list, allies: list) -> float:
        """
        Werewolf Form :
        - 1500% dégâts sur une cible aléatoire (skill damage → appliqué via skill_dmg)
        - Vole 80% de l'ATK de la cible pendant 4 tours
        """
        if not enemies:
            return 0.0

        alive_enemies = [e for e in enemies
                         if getattr(e.character if hasattr(e, "character") else e, "is_alive", True)]
        if not alive_enemies:
            return 0.0

        target      = random.choice(alive_enemies)
        target_char = target.character if hasattr(target, "character") else target

        # ── 1500% ATK, amplifié par skill_dmg ──
        damage = self.character.atk * 15.0
        damage *= (1.0 + self.character.skill_dmg)

        # Armes
        for w in self.character.weapon:
            damage = w.modify_damage_dealt(self.character, target_char, damage)

        # ── Vol d'ATK : 80% de l'ATK de la cible pendant 4 tours ──
        stolen_atk = getattr(target_char, "atk", 0) * 0.80
        self._steal_atk(target_char, stolen_atk, duration=4)

        return damage * self.character.attack_multiplier

    # ═══════════════════════════════════════════════════════════
    #  PASSIVE #3 : Last One Standing
    #  Appelé par combat_engine via on_ally_die des weapons/dragons
    #  → On l'expose ici pour que combat_engine puisse l'appeler
    # ═══════════════════════════════════════════════════════════
    def on_ally_die(self, allies: list):
        """
        Pour chaque allié qui meurt : +40% base ATK & +40% CR, permanent.
        """
        self._allies_dead += 1
        self.character.atk += 0.40 * self.character.base_atk
        self.character.cr  = min(1.0, self.character.cr + 0.40)

    # ═══════════════════════════════════════════════════════════
    #  HELPERS
    # ═══════════════════════════════════════════════════════════
    def on_crit(self):
        pass  # Pas de mécanique supplémentaire sur crit pour Okami (hors Fresh Meat)

    def _pick_target(self, enemies):
        alive = [e for e in enemies
                 if getattr(e.character if hasattr(e, "character") else e, "is_alive", True)]
        if not alive:
            return enemies[0]
        # Position 1-3 : cible le plus fort en ATK
        if 1 <= self.position <= 3:
            return max(alive, key=lambda e: getattr(
                e.character if hasattr(e, "character") else e, "atk", 0))
        return min(alive, key=lambda e: getattr(
            e.character if hasattr(e, "character") else e, "hp", 0))

    def _steal_atk(self, target_char, amount: float, duration: int):
        """
        Réduit l'ATK de la cible de `amount` et ajoute la même valeur à Okami
        pendant `duration` tours, puis restitue.
        """
        # Réduction sur la cible (debuff)
        target_char.atk = max(0, target_char.atk - amount)

        # Buff sur Okami (buff temporaire avec delta exact)
        buff_key = "werewolf_atk_steal"
        if has_buff(self.character, buff_key):
            # Rafraîchit et cumule
            for b in self.character.buffs:
                if b["type"] == buff_key:
                    b["duration"] = duration
                    b["delta"]   += amount
                    break
            self.character.atk += amount
        else:
            # Nouveau buff — on bypass BUFF_DEFS pour une valeur dynamique
            self.character.buffs.append({
                "type":     buff_key,
                "duration": duration,
                "delta":    amount,
                "source":   self,
            })
            self.character.atk += amount

        # Mémorise la cible pour restituer à expiration
        # (géré dans tick_buffs → remove_buff → _apply_buff_stat nécessite stat+delta)
        # On enregistre la stat pour la restitution automatique
        from debuffs import BUFF_DEFS
        BUFF_DEFS[buff_key] = {"stat": "atk", "delta": amount, "mode": "flat"}