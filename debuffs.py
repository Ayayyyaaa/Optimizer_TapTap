# ═══════════════════════════════════════════════════════════════
#  DEBUFFS.PY  —  Système de debuffs avec durée
# ═══════════════════════════════════════════════════════════════
#
#  Chaque debuff est un dict :
#  {
#    "type":     str,   # identifiant (voir DEBUFF_TYPES)
#    "duration": int,   # tours restants
#    "source":   obj,   # qui a appliqué le debuff (optionnel)
#  }
#
#  Application  : apply_debuff(character, debuff_type, duration, source)
#  Tick de tour : tick_debuffs(character)  → à appeler en fin de round
#  Vérification : has_debuff(character, debuff_type) → bool
# ═══════════════════════════════════════════════════════════════

# ── Définition des debuffs ────────────────────────────────────
#  Chaque entrée décrit l'effet ACTIF (appliqué à l'entrée)
#  et l'effet RETIRÉ (annulé à l'expiration).
#
#  "stat"   : attribut du Character affecté
#  "delta"  : valeur ajoutée (négative = malus)
#  "mode"   : "flat" | "percent_base"  (percent_base = % de la stat de base)

DEBUFF_DEFS = {
    # ── Debuffs de l'image ───────────────────────────────────
    "bleeding":   {"stat": "block",           "delta": -0.15, "mode": "flat"},
    "poisoned":   {"stat": "control_resist",  "delta": -0.15, "mode": "flat"},
    "burning":    {"stat": "defense",         "delta": -0.15, "mode": "percent_base"},
    "cursed":     {"stat": "heal_effect",     "delta": -0.50, "mode": "flat"},
    "frozen":     {"stat": "basic_dmg_taken", "delta": +0.20, "mode": "flat"},   # +20% dégâts basic reçus
    "petrified":  {"stat": "skill_dmg_taken", "delta": +0.10, "mode": "flat"},   # +10% dégâts skill reçus
    "taunted":    {"stat": "hit_chance",      "delta": -0.15, "mode": "flat"},
    "stun":       {"stat": None,              "delta":  0,    "mode": "flat"},   # géré séparément (skip tour)
    "frostbite":  {"stat": None,              "delta":  0,    "mode": "flat"},   # géré dans le calcul de dégâts
    # ── Debuffs supplémentaires utiles ───────────────────────
    "armor_break":{"stat": "defense",         "delta": -0.25, "mode": "percent_base"},
    "atk_reduce": {"stat": "atk",             "delta": -0.15, "mode": "percent_base"},
    "spd_reduce": {"stat": "spd",             "delta": -100,  "mode": "flat"},
}

CONTROL_DEBUFFS = {"stun", "frozen"}   # debuffs qui empêchent d'agir


def apply_debuff(character, debuff_type: str, duration: int, source=None) -> bool:
    """
    Applique un debuff sur character.
    Retourne False si le character est immunisé ou résiste.
    """
    import random

    # Vérification immunité (liste sur le fighter, pas sur le character)
    immune_list = getattr(character, "_immune", [])
    if debuff_type in immune_list:
        return False

    # Résistance au contrôle
    if debuff_type in CONTROL_DEBUFFS:
        resist_roll = random.random()
        resist_value = getattr(character, "control_resist", 0)
        if resist_roll < resist_value:
            return False

    # Si le debuff est déjà actif, on rafraîchit la durée
    for existing in character.debuffs:
        if existing["type"] == debuff_type:
            existing["duration"] = max(existing["duration"], duration)
            return True

    # Nouveau debuff : on l'ajoute et on applique l'effet immédiatement
    character.debuffs.append({
        "type": debuff_type,
        "duration": duration,
        "source": source,
    })
    _apply_stat_effect(character, debuff_type, apply=True)

    # Stun : marque le character
    if debuff_type == "stun":
        character.is_stunned = True

    return True


def remove_debuff(character, debuff_type: str):
    """Retire un debuff et annule son effet stat."""
    character.debuffs = [d for d in character.debuffs if d["type"] != debuff_type]
    _apply_stat_effect(character, debuff_type, apply=False)

    if debuff_type == "stun":
        character.is_stunned = False


def tick_debuffs(character):
    """
    À appeler en FIN de round.
    Décrémente les durées et retire les debuffs expirés.
    """
    expired = []
    for debuff in character.debuffs:
        debuff["duration"] -= 1
        if debuff["duration"] <= 0:
            expired.append(debuff["type"])

    for dtype in expired:
        remove_debuff(character, dtype)


def has_debuff(character, debuff_type: str) -> bool:
    return any(d["type"] == debuff_type for d in character.debuffs)


def get_debuff_stacks(character, debuff_type: str) -> int:
    """Retourne le nombre d'applications d'un debuff (pour futures mécaniques de stacks)."""
    return sum(1 for d in character.debuffs if d["type"] == debuff_type)


# ── Helpers internes ──────────────────────────────────────────

def _apply_stat_effect(character, debuff_type: str, apply: bool):
    """Applique ou retire l'effet stat d'un debuff."""
    defn = DEBUFF_DEFS.get(debuff_type)
    if defn is None or defn["stat"] is None:
        return

    stat  = defn["stat"]
    mode  = defn["mode"]
    delta = defn["delta"]

    if not apply:
        delta = -delta  # on annule l'effet

    if not hasattr(character, stat):
        # Initialise la stat si elle n'existe pas encore
        setattr(character, stat, 0)

    if mode == "percent_base":
        # On cherche la stat de base correspondante
        base_stat = "base_" + stat
        base_val  = getattr(character, base_stat, getattr(character, stat, 0))
        setattr(character, stat, getattr(character, stat) + delta * abs(base_val))
    else:
        setattr(character, stat, getattr(character, stat) + delta)


# ═══════════════════════════════════════════════════════════════
#  SYSTÈME DE BUFFS (même mécanique que debuffs, effet positif)
# ═══════════════════════════════════════════════════════════════

BUFF_DEFS = {
    "skill_dmg_up":  {"stat": "skill_dmg", "delta": +0.25, "mode": "flat"},
    "atk_steal":     {"stat": "atk",       "delta":  0,    "mode": "flat"},  # géré manuellement (vol d'ATK)
    # Ajoute ici d'autres buffs au besoin
}


def apply_buff(character, buff_type: str, duration: int, delta_override: float = None, source=None) -> bool:
    """
    Applique un buff sur character avec une durée.
    delta_override : remplace le delta de BUFF_DEFS (utile pour les valeurs dynamiques).
    Retourne False si le buff est déjà actif (durée rafraîchie à la place).
    """
    for existing in character.buffs:
        if existing["type"] == buff_type:
            existing["duration"] = max(existing["duration"], duration)
            return False

    defn  = BUFF_DEFS.get(buff_type, {})
    delta = delta_override if delta_override is not None else defn.get("delta", 0)
    mode  = defn.get("mode", "flat")

    character.buffs.append({
        "type":     buff_type,
        "duration": duration,
        "delta":    delta,
        "source":   source,
    })
    _apply_buff_stat(character, defn.get("stat"), delta, mode, apply=True)
    return True


def remove_buff(character, buff_type: str):
    """Retire un buff et annule son effet stat."""
    for b in list(character.buffs):
        if b["type"] == buff_type:
            defn = BUFF_DEFS.get(buff_type, {})
            _apply_buff_stat(character, defn.get("stat"), b["delta"], defn.get("mode", "flat"), apply=False)
            character.buffs.remove(b)


def tick_buffs(character):
    """À appeler en FIN de round. Décrémente les durées et retire les buffs expirés."""
    expired = []
    for buff in character.buffs:
        buff["duration"] -= 1
        if buff["duration"] <= 0:
            expired.append(buff["type"])
    for btype in expired:
        remove_buff(character, btype)


def has_buff(character, buff_type: str) -> bool:
    return any(b["type"] == buff_type for b in character.buffs)


def _apply_buff_stat(character, stat, delta, mode, apply: bool):
    if stat is None or delta == 0:
        return
    if not hasattr(character, stat):
        setattr(character, stat, 0)
    actual_delta = delta if apply else -delta
    if mode == "percent_base":
        base_val = getattr(character, "base_" + stat, getattr(character, stat, 0))
        setattr(character, stat, getattr(character, stat) + actual_delta * abs(base_val))
    else:
        setattr(character, stat, getattr(character, stat) + actual_delta)