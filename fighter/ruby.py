# ═══════════════════════════════════════════════════════════════
#  FIGHTER_RUBY.PY  —  Ruby
# ═══════════════════════════════════════════════════════════════
#
#  SKILLS :
#
#  [ACTIVE] Draconic Artillery :
#    - 400% dmg à 4 ennemis aléatoires. 25% chance d'appliquer Dynamite Mark.
#    - Self : +25% Skill Damage pour 5 rounds.
#    - Alliés : Cleans Freeze + donne +40% Skill Damage (3 rounds) si Frozen.
#    - Dynamite Mark (End of round) : Si cible a l'énergie max -> Explose (500% dmg
#      à sa rangée + 500% Burn dmg sur 3 tours). Perd 50 Énergie.
#
#  [PASSIVE 1] Flameheart :
#    - ATK +25%, CR +25%, Skill DMG +25%, Armor Break +40%, CD +25%.
#    - Immunité Burn & Freeze.
#    - Dégâts vs cibles avec Burn +25%.
#    - Attaque basique vs Burn : +40 Énergie supplémentaire.
#
#  [PASSIVE 2] Trigger Happy :
#    - Début de combat : SPD +40 pour soi et alliés même rangée (3 rounds).
#    - Après 1 round  : CR +20%, CD +25% soi et même rangée (3 rounds).
#    - Après 3 rounds : Magic Shield sur 2 alliés aléatoires (3 rounds) + 
#      "Trigger Happy" sur soi (Permanent).
#    - Trigger Happy buff : ATK/CR +40%, gagne 100 Énergie après un Skill Attack.
#
#  [PASSIVE 3] Dragon Shell :
#    - Début de combat : Bouclier de 60% Max HP.
#    - Si le bouclier casse : 250% Burn dmg à tous les ennemis (3 rounds) + 40 Énergie tous alliés.
#    - Crit sur Skill Attack : +20% CD self (5 rounds) + 25% chance de donner 20 Énergie aux alliés.
# ═══════════════════════════════════════════════════════════════

import random
from character import Character
from debuffs import apply_debuff, has_debuff, apply_buff

class Ruby:
    """Fighter Ruby."""

    # Stats tirées de l'image
    BASE_HP          = 6_368_499
    BASE_ATK         = 92_261
    BASE_DEF         = 3_442
    BASE_SPD         = 1_443
    BASE_CR          = 0.40
    BASE_CD          = 1.25 # Base 100% + 25% de l'image
    BASE_SKILL_DMG   = 0.25
    BASE_BLOCK       = 0.00
    BASE_ARMOR_BREAK = 0.40
    BASE_DMG_REDUCE  = 0.00

    def __init__(self):
        self.character = Character(
            name              = "Ruby",
            faction           = "Dragon",  # À ajuster si sa faction est différente
            hp                = self.BASE_HP,
            atk               = self.BASE_ATK,
            defense           = self.BASE_DEF,
            spd               = self.BASE_SPD,
            skill_dmg         = self.BASE_SKILL_DMG,
            block             = self.BASE_BLOCK,
            cr                = self.BASE_CR,
            cd                = self.BASE_CD,
            dmg_reduce        = self.BASE_DMG_REDUCE,
            control_resist    = 0.0,
            hit_chance        = 0.0,
            armor_break       = self.BASE_ARMOR_BREAK,
            control_precision = 0.0,
            stealth           = False,
            weapon            = [],
            dragons           = [],
            pos               = "front",
        )

        # Variables internes pour ses passifs complexes
        self._round_counter = 0
        self._dragon_shell_hp = 0
        self._has_trigger_happy = False
        self._dynamite_marks = {}  # {ennemi: duration_restante}
        
        # Référence pour pouvoir toucher les ennemis quand le bouclier pète
        self._last_enemies_ref = []

        # Immunité Flameheart (P1)
        self.character._immune = ["burn", "frozen", "freeze"]

    # ══════════════════════════════════════════════════════════
    #  BATTLE START & ROUND START
    # ══════════════════════════════════════════════════════════
    def battle_start(self, allies: list, enemies: list):
        char = self.character
        self._last_enemies_ref = enemies

        # ── Flameheart (P1) - Stats bonus ──
        char.atk         += 0.25 * char.base_atk
        char.cr          += 0.25
        char.skill_dmg   += 0.25
        char.armor_break += 0.40
        char.cd          += 0.25

        # ── Dragon Shell (P3) - Bouclier Initial ──
        self._dragon_shell_hp = char.max_hp * 0.60

        # ── Trigger Happy (P2) - Début combat ──
        # +40 SPD soi et même rangée pour 3 rounds
        self._apply_row_buff(allies, "spd", 40, duration=3)

    def on_round_start(self, allies: list):
        self._round_counter += 1

        # ── Trigger Happy (P2) - Évolution temporelle ──
        if self._round_counter == 2: # "After 1 round" = Début du round 2
            # CR +20%, CD +25% soi et même rangée (3 rounds)
            self._apply_row_buff(allies, "cr", 0.20, duration=3)
            self._apply_row_buff(allies, "cd", 0.25, duration=3)
            
        elif self._round_counter == 4: # "After 3 rounds" = Début du round 4
            # Magic Shield à 2 alliés aléatoires
            alive_allies = [a for a in allies if getattr(a.character, "is_alive", True)]
            targets = random.sample(alive_allies, min(2, len(alive_allies)))
            for t in targets:
                apply_buff(t.character, "magic_shield", duration=3, source=self)
            
            # "Trigger Happy" sur Ruby (Permanent)
            self._has_trigger_happy = True
            self.character.atk += 0.40 * self.character.base_atk
            self.character.cr  += 0.40

    # ══════════════════════════════════════════════════════════
    #  ATTAQUE BASIQUE
    # ══════════════════════════════════════════════════════════
    def basic_atk(self, enemies: list, allies: list) -> float:
        if not enemies: return 0.0
        self._last_enemies_ref = enemies

        alive_enemies = [e for e in enemies if getattr(e.character if hasattr(e, "character") else e, "is_alive", True)]
        if not alive_enemies: return 0.0

        target = alive_enemies[0]
        target_char = target.character if hasattr(target, "character") else target

        # On suppose 250% ATK de base comme la majorité des persos
        raw = self.character.atk * self.character.attack_multiplier * 2.50
        dmg = self._calc_damage(target_char, raw)

        target_char.hp -= dmg
        if target_char.hp <= 0:
            target_char.is_alive = False

        # Modificateurs d'armes
        for w in self.character.weapon:
            w.on_basic_attack(self.character, dmg)

        # ── Flameheart (P1) : Bonus Énergie sur attaque basique vs Burn ──
        if has_debuff(target_char, "burn"):
            self.character.energy += 40

        self.character.energy += 20
        return dmg

    # ══════════════════════════════════════════════════════════
    #  ULTIME — DRACONIC ARTILLERY
    # ══════════════════════════════════════════════════════════
    def ult(self, enemies: list, allies: list) -> float:
        if not enemies: return 0.0
        self._last_enemies_ref = enemies

        alive_enemies = [e for e in enemies if getattr(getattr(e, "character", e), "is_alive", True)]
        if not alive_enemies: return 0.0

        # Cible 4 ennemis aléatoires
        nb_targets = min(4, len(alive_enemies))
        targets = random.sample(alive_enemies, nb_targets)

        # Self buff : +25% Skill Damage pour 5 rounds
        apply_buff(self.character, "skill_dmg_up", duration=5, delta_override=0.25, source=self)

        # Alliés : Cleanse Frozen & +40% Skill Damage
        for ally in allies:
            ally_char = ally.character if hasattr(ally, "character") else ally
            if has_debuff(ally_char, "frozen") or has_debuff(ally_char, "freeze"):
                # Cleanse
                ally_char.debuffs = [d for d in ally_char.debuffs if d["type"] not in ["frozen", "freeze"]]
                # Buff
                apply_buff(ally_char, "skill_dmg_up", duration=3, delta_override=0.40, source=self)

        total_dmg = 0.0
        for target in targets:
            target_char = target.character if hasattr(target, "character") else target

            # 400% ATK + bonus Skill DMG
            raw = self.character.atk * self.character.attack_multiplier * 4.00
            raw *= (1.0 + self.character.skill_dmg)
            
            # Vérification Crit pour P3 (Dragon Shell - Skill attack crit)
            is_crit = random.random() < self.character.cr
            if is_crit:
                raw *= self.character.cd
                self._on_skill_crit(allies)

            dmg = self._calc_damage(target_char, raw, bypass_crit=True) # Crit déjà géré au dessus
            
            target_char.hp -= dmg
            if target_char.hp <= 0:
                target_char.is_alive = False
            total_dmg += dmg

            # Dynamite Mark (25% chance)
            if random.random() < 0.25:
                self._dynamite_marks[target] = 3 # Dure théoriquement un certain temps, disons 3 tours

        # ── Trigger Happy (P2) : +100 Énergie si buff actif ──
        if self._has_trigger_happy:
            self.character.energy += 100

        return total_dmg

    # ══════════════════════════════════════════════════════════
    #  ON HIT RECEIVED (Gestion Dragon Shell)
    # ══════════════════════════════════════════════════════════
    def on_hit_received(self, attacker, damage: float, allies: list) -> float:
        """Intercepte les dégâts pour le Dragon Shell (P3)."""
        if self._dragon_shell_hp > 0:
            if damage < self._dragon_shell_hp:
                self._dragon_shell_hp -= damage
                return 0.0 # Dégâts totalement absorbés
            else:
                damage -= self._dragon_shell_hp
                self._dragon_shell_hp = 0
                self._break_dragon_shell(allies)
                # Le reste des dégâts passe sur les HP

        self.character.hp -= damage
        return damage

    # ══════════════════════════════════════════════════════════
    #  CUSTOM ENGINE HOOKS (À appeler par ton moteur)
    # ══════════════════════════════════════════════════════════
    def on_round_end(self, allies: list, round_number: int):
        """
        Appelé par fight.py en fin de round.
        Gère les Dynamite Marks et les callbacks armes/dragons.
        """
        char = self.character
        enemies = self._last_enemies_ref

        # ── Dynamite Mark tick ──
        to_remove = []
        for enemy, duration in self._dynamite_marks.items():
            enemy_char = enemy.character if hasattr(enemy, "character") else enemy

            if not enemy_char.is_alive:
                to_remove.append(enemy)
                continue

            # Check explosion condition (Full Energy)
            if getattr(enemy_char, "energy", 0) >= 100:
                self._trigger_dynamite_explosion(enemy, enemies)
                to_remove.append(enemy)
            else:
                self._dynamite_marks[enemy] -= 1
                if self._dynamite_marks[enemy] <= 0:
                    to_remove.append(enemy)

        for e in to_remove:
            if e in self._dynamite_marks:
                del self._dynamite_marks[e]

        # ── Callbacks armes / dragons ──
        for w in char.weapon:
            w.on_round_end(char, allies, round_number)
        for d in char.dragons:
            d.on_round_end(char, allies, round_number)

    # ══════════════════════════════════════════════════════════
    #  HELPERS PRIVÉS
    # ══════════════════════════════════════════════════════════
    def _calc_damage(self, target_char, raw_dmg: float, bypass_crit=False) -> float:
        """Calcul dégâts standard avec le bonus Flameheart (P1)."""
        if not bypass_crit and random.random() < self.character.cr:
            raw_dmg *= self.character.cd
            
        # P1 : +25% dégâts si cible a Burn
        if has_debuff(target_char, "burn"):
            raw_dmg *= 1.25
            
        return max(0.0, raw_dmg)

    def _apply_row_buff(self, allies, stat, value, duration):
        """Applique un buff à Ruby et aux alliés de sa rangée."""
        my_pos = getattr(self.character, "position", "front")
        for ally in allies:
            ally_char = ally.character if hasattr(ally, "character") else ally
            if getattr(ally_char, "position", "front") == my_pos:
                # Bypass le dictionnaire BUFF_DEFS en l'appliquant directement avec un custom flag
                apply_buff(ally_char, f"trigger_happy_{stat}", duration=duration, delta_override=value, source=self)

    def _on_skill_crit(self, allies):
        """P3 : Déclenché lors d'un coup critique pendant l'ult."""
        # +20% CD self pour 5 rounds
        apply_buff(self.character, "cd_up", duration=5, delta_override=0.20, source=self)
        
        # 25% chance : +20 Énergie à tous les alliés
        if random.random() < 0.25:
            for ally in allies:
                ally_char = ally.character if hasattr(ally, "character") else ally
                ally_char.energy = min(100, getattr(ally_char, "energy", 0) + 20)

    def _break_dragon_shell(self, allies):
        """P3 : Si le bouclier est brisé."""
        alive_enemies = [e for e in self._last_enemies_ref if getattr(e.character if hasattr(e, "character") else e, "is_alive", True)]
        
        # 250% Burn dmg à tous les ennemis
        burn_base = self.character.atk * 2.50
        for e in alive_enemies:
            e_char = e.character if hasattr(e, "character") else e
            apply_debuff(e_char, "burn", duration=3, source=self)
            # Applique directement le dégat de Burn (ou laisse le tick du moteur gérer selon ton archi)
            e_char.hp -= burn_base
            if e_char.hp <= 0: e_char.is_alive = False

        # +40 Énergie tous alliés
        for ally in allies:
            ally_char = ally.character if hasattr(ally, "character") else ally
            ally_char.energy = min(100, getattr(ally_char, "energy", 0) + 40)

    def _trigger_dynamite_explosion(self, marked_enemy, all_enemies):
        """Ult : Explosion de la Dynamite Mark."""
        marked_char = marked_enemy.character if hasattr(marked_enemy, "character") else marked_enemy
        
        # -50 énergie
        marked_char.energy = max(0, getattr(marked_char, "energy", 0) - 50)

        # Trouver tous les ennemis sur la même rangée
        target_pos = getattr(marked_char, "position", "front")
        row_enemies = [e for e in all_enemies 
                       if getattr(e.character if hasattr(e, "character") else e, "position", "front") == target_pos
                       and getattr(e.character if hasattr(e, "character") else e, "is_alive", True)]

        base_explosion = self.character.atk * 5.00
        base_burn = self.character.atk * 5.00

        for e in row_enemies:
            e_char = e.character if hasattr(e, "character") else e
            # 500% degats immédiats
            e_char.hp -= base_explosion
            if e_char.hp <= 0: e_char.is_alive = False
            
            # + 500% Burn sur 3 tours
            if e_char.is_alive:
                apply_debuff(e_char, "burn", duration=3, source=self)
                # Appliquer le reste au tick du moteur