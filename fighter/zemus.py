# ═══════════════════════════════════════════════════════════════
#  ZEMUS.PY  —  Fighter : Zemus
#  Faction : Cobra
# ═══════════════════════════════════════════════════════════════
#
#  SKILLS :
#
#  [ACTIVE] Noxious Strike
#    - Inflige 1000% ATK aux 2 ennemis avec le moins de HP
#    - 75% chance d'appliquer Curse 3 tours (400% ATK dmg supplémentaire)
#    - Si Killing Blow : 60% chance de réduire ATK, Hit Chance et Crit Chance
#      de TOUS les ennemis de 25% pendant 3 tours
#    - Retire tous les effets de soin (Heal Over Time) des cibles
#
#  [PASSIVE 1] Death Machine
#    - ATK +30%, Crit Chance +30%, Crit Damage +50%, SPD +80, Armor Break +50%
#    - Inflige 50% de dégâts supplémentaires aux ennemis Griffin
#    - Immune à Curse
#
#  [PASSIVE 2] Defense Disintegration
#    - Basic attacks : cible l'ennemi avec le plus de Max HP, 200% ATK dmg
#    - Réduit le Block de la cible de 10% pendant 5 rounds
#    - Si l'attaque est bloquée : réduit le Block de 25% supplémentaires pendant 5 rounds
#                                 et augmente le Hit Chance de Zemus de 30% pendant 3 rounds
#    - Killing Blow → purifie Zemus + booste Armor Break et Hit Chance
#      de 3 alliés aléatoires de 25% pendant 3 rounds
#
#  [PASSIVE 3] Reactive Armor
#    - S'il ne reste qu'un seul ennemi : attaque 2 fois par tour
#    - En fin de round, si Zemus a Bleed, Burn ou Poison :
#      inflige 200% ATK dmg du même type à TOUS les ennemis pendant 5 rounds
#      (une seule fois par combat)
#    - En fin de round, pour chaque ennemi Cursed :
#      augmente le CD des 2 alliés avec le plus d'ATK de 50% pendant 5 rounds
#
#  Stats de base calquées sur Laguna / Chancer (même tier)
# ═══════════════════════════════════════════════════════════════

import random
from character import Character
from debuffs import apply_debuff, has_debuff, apply_buff, remove_debuff
from muta import Mutagen


class Zemus:
    """Fighter Zemus — Faction Cobra."""

    BASE_HP    = 3_121_813
    BASE_ATK   = 79_070
    BASE_DEF   = 1_990
    BASE_SPD   = 1_392
    BASE_CR    = 0.15   # avant Death Machine
    BASE_CD    = 1.50   # avant Death Machine

    def __init__(self):
        self.character = Character(
            name               = "Zemus",
            faction            = "Cobra",
            hp                 = self.BASE_HP,
            atk                = self.BASE_ATK,
            defense            = self.BASE_DEF,
            spd                = self.BASE_SPD,
            skill_dmg          = 0.0,
            block              = 0.0,
            cr                 = self.BASE_CR,
            cd                 = self.BASE_CD,
            dmg_reduce         = 0.0,
            control_resist     = 0.0,
            hit_chance         = 0.0,   # 0 = ne rate jamais (miss_chance interprétation)
            armor_break        = 0.0,   # avant Death Machine
            control_precision  = 0.0,
            stealth            = False,
            weapon             = [],
            dragons            = [],
            pos                = "back",
            mutagen            = Mutagen(self, "E"),
        )
        self.character.mutagen.apply()
        self.character.mutagen.perk1()
        self.character.mutagen.perk2()

        # Immunité Curse (Death Machine P1)
        self.character._immune = ["cursed"]

        # Flags internes
        self._reactive_armor_triggered = False   # P3 : DoT retaliation once per combat
        self._killing_blow_happened    = False    # flag pour éviter double-déclenchement

    # ══════════════════════════════════════════════════════════
    #  BATTLE START — Death Machine (P1)
    # ══════════════════════════════════════════════════════════

    def battle_start(self, allies: list, enemies: list):
        char = self.character

        # Death Machine (P1) passive stats
        char.atk         += 0.30 * char.base_atk
        char.cr          += 0.30
        char.cd          += 0.50
        char.spd         += 80
        char.armor_break += 0.50

    # ══════════════════════════════════════════════════════════
    #  ROUND START
    # ══════════════════════════════════════════════════════════

    def on_round_start(self, allies: list):
        pass   # rien de spécial au début du round

    # ══════════════════════════════════════════════════════════
    #  ATTAQUE BASIQUE — Defense Disintegration (P2)
    # ══════════════════════════════════════════════════════════

    def basic_atk(self, enemies: list, allies: list) -> float:
        """
        Cible l'ennemi avec le plus de Max HP.
        200% ATK dmg.
        Réduit le Block de 10% pendant 5 rounds.
        Si bloqué : -25% Block supplémentaires + Zemus +30% Hit Chance 3 rounds.
        Killing Blow → purifie Zemus + boost Armor Break/Hit Chance 3 alliés.
        """
        char = self.character

        alive_enemies = [e for e in enemies
                         if getattr(getattr(e, "character", e), "is_alive", True)]
        if not alive_enemies:
            return 0.0

        # Reactive Armor (P3) : si un seul ennemi, attaque deux fois
        nb_attacks = 2 if len(alive_enemies) == 1 else 1

        # Cible = ennemi avec le plus de Max HP
        target = max(alive_enemies,
                     key=lambda e: getattr(getattr(e, "character", e), "max_hp", 0))
        target_char = getattr(target, "character", target)

        total_dmg = 0.0
        for _ in range(nb_attacks):
            if not target_char.is_alive:
                break

            raw = char.atk * char.attack_multiplier * 2.0   # 200%
            dmg, was_crit = self._calc_damage(char, raw, is_skill=False)

            # Vérification block
            block_chance = max(0.0, getattr(target_char, "block", 0.0))
            if random.random() < block_chance:
                # Bloqué → malus Block supplémentaire + Hit Chance bonus
                apply_debuff(target_char, "bleeding", duration=5, source=self)   # proxy block -15%
                # Bonus Hit Chance Zemus (+30% pendant 3 rounds)
                if not has_debuff(char, "hit_bonus_zemus"):
                    apply_buff(char, "skill_dmg_up", duration=3, source=self)    # proxy : on utilise skill_dmg_up comme marqueur
                    char.hit_chance = max(0.0, char.hit_chance - 0.30)           # hit_chance = miss_chance → réduire = plus précis
                dmg *= 0.5
            else:
                total_dmg += dmg

                # Réduction Block normale (-10% pendant 5 rounds) via proxy bleeding
                apply_debuff(target_char, "bleeding", duration=5, source=self)

                # Killing Blow ?
                was_killing_blow = target_char.hp <= 0
                if was_killing_blow:
                    target_char.hp      = 0
                    target_char.is_alive = False
                    self._on_killing_blow(char, allies)

            for w in char.weapon:
                w.on_basic_attack(char, dmg)

        char.energy += 20
        return total_dmg

    # ══════════════════════════════════════════════════════════
    #  ULT — NOXIOUS STRIKE
    # ══════════════════════════════════════════════════════════

    def ult(self, enemies: list, allies: list) -> float:
        """
        Noxious Strike :
        - 1000% ATK aux 2 ennemis avec le moins de HP
        - 75% chance Curse 3 tours (400% ATK dmg bonus)
        - Killing Blow → 60% chance : ATK/Hit/CR tous ennemis -25% 3 tours
        - Retire les HoT des cibles
        """
        char = self.character

        alive_enemies = [e for e in enemies
                         if getattr(getattr(e, "character", e), "is_alive", True)]
        if not alive_enemies:
            return 0.0

        # 2 ennemis avec le moins de HP
        targets = sorted(alive_enemies,
                         key=lambda e: getattr(getattr(e, "character", e), "hp", 0))[:2]

        total_dmg = 0.0
        killing_blow_happened = False

        for target in targets:
            target_char = getattr(target, "character", target)
            if not target_char.is_alive:
                continue

            # Retire les HoT (on supprime le buff heal_effect via proxy)
            # Dans le système actuel, on nettoie les buffs bénéfiques de type soin
            target_char.buffs = [b for b in target_char.buffs
                                  if b["type"] not in ("heal_over_time",)]

            # Dégâts principaux : 1000% ATK
            raw = char.atk * char.attack_multiplier * 10.0
            raw *= (1.0 + char.skill_dmg)
            dmg, _ = self._calc_damage(char, raw, is_skill=True)

            # Bonus Griffin (Death Machine P1) : +50% vs Griffin
            if getattr(target_char, "faction", "") == "Griffin":
                dmg *= 1.50

            total_dmg += dmg

            was_killing_blow = target_char.hp <= 0
            if was_killing_blow:
                target_char.hp       = 0
                target_char.is_alive = False
                killing_blow_happened = True

            # 75% chance Curse 3 tours + 400% ATK dégâts maudits
            if random.random() < 0.75:
                applied = apply_debuff(target_char, "cursed", duration=3, source=self, dot_multiplier=4)
                if applied:
                    curse_dmg = char.atk * 4.0   # 400%
                    # Amplifié par les armes qui ont modify_dot_damage (ex: Knife)
                    for w in char.weapon:
                        if hasattr(w, "modify_dot_damage"):
                            curse_dmg = w.modify_dot_damage(char, curse_dmg)
                    total_dmg += curse_dmg
                    if target_char.hp <= 0 and target_char.is_alive:
                        target_char.hp       = 0
                        target_char.is_alive = False
                        killing_blow_happened = True

        # Killing Blow → debuff global tous ennemis (60% chance)
        if killing_blow_happened and random.random() < 0.60:
            all_alive = [e for e in enemies
                         if getattr(getattr(e, "character", e), "is_alive", True)]
            for e in all_alive:
                ec = getattr(e, "character", e)
                apply_debuff(ec, "atk_reduce",  duration=3, source=self)
                apply_debuff(ec, "taunted",      duration=3, source=self)   # proxy hit_chance -15%
                # CR -25% : on réduit directement (pas de debuff dédié)
                ec.cr = max(0.0, ec.cr - 0.25)

        self._cursed_enemies_count = sum(
            1 for e in enemies
            if has_debuff(getattr(e, "character", e), "cursed")
        )

        return total_dmg

    # ══════════════════════════════════════════════════════════
    #  ROUND END — Reactive Armor (P3)
    # ══════════════════════════════════════════════════════════

    def on_round_end(self, allies: list, round_number: int):
        char = self.character

        # ── DoT retaliation (une seule fois par combat) ───────
        if not self._reactive_armor_triggered:
            active_dots = [d["type"] for d in char.debuffs
                           if d["type"] in ("bleeding", "burning", "poisoned")]
            if active_dots:
                self._reactive_armor_triggered = True
                # On applique le premier dot trouvé à tous les ennemis
                # (le moteur ne donne pas accès aux ennemis ici, donc on stocke
                #  l'info pour que le moteur la lise via _pending_aoe_dot)
                self._pending_aoe_dot = {
                    "type":     active_dots[0],
                    "duration": 5,
                    "dmg":      char.atk * 2.0,   # 200% ATK
                }

        # ── CD boost pour les 2 alliés avec le plus d'ATK ────
        # (pour chaque ennemi Cursed — le moteur centralisé gère les ennemis,
        #  ici on accède aux alliés uniquement)
        # Implémentation simplifiée : on boost à chaque fin de round si un buff
        # "cursed_enemies" est présent (posé par le moteur) — sinon, on skip.
        # Dans fight.py (dummy boss), on applique systématiquement si ult a été castée.
        if getattr(self, "_cursed_enemies_count", 0) > 0:
            sorted_allies = sorted(
                [a for a in allies if a.character.is_alive],
                key=lambda a: a.character.atk,
                reverse=True,
            )[:2]
            for ally in sorted_allies:
                ac = ally.character
                apply_buff(ac, "skill_dmg_up", duration=5, source=self)  # proxy CD boost
                ac.cd += 0.50

        # Callbacks armes / dragons
        for w in char.weapon:
            w.on_round_end(char, allies, round_number)
        for d in char.dragons:
            d.on_round_end(char, allies, round_number)

    def on_ally_die(self, allies: list):
        pass

    def on_self_death(self, allies: list):
        pass

    # ══════════════════════════════════════════════════════════
    #  HELPER — Killing Blow (P2)
    # ══════════════════════════════════════════════════════════

    def _on_killing_blow(self, char, allies: list):
        """
        Defense Disintegration (P2) :
        Purifie Zemus de ses debuffs.
        Boost Armor Break et Hit Chance de 3 alliés aléatoires de 25% pendant 3 rounds.
        """
        # Purification de Zemus
        char.debuffs.clear()
        char.is_stunned = False

        # Boost 3 alliés aléatoires
        alive_allies = [a for a in allies if a is not self and a.character.is_alive]
        chosen = random.sample(alive_allies, min(3, len(alive_allies)))
        for ally in chosen:
            ac = ally.character
            ac.armor_break  = getattr(ac, "armor_break", 0.0) + 0.25
            ac.hit_chance   = max(0.0, getattr(ac, "hit_chance", 0.15) - 0.25)  # moins de miss

    # ══════════════════════════════════════════════════════════
    #  HELPER — Calcul dégâts
    # ══════════════════════════════════════════════════════════

    def _calc_damage(self, char, raw_dmg: float, is_skill: bool) -> tuple[float, bool]:
        """Retourne (dmg_final, was_crit)."""
        is_crit = random.random() < char.cr
        if is_crit:
            raw_dmg *= char.cd
        return max(0.0, raw_dmg), is_crit