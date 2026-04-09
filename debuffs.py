import random
# ═══════════════════════════════════════════════════════════════
#  DEBUFFS.PY  —  Système de debuffs avec durée
# ═══════════════════════════════════════════════════════════════

DEBUFF_DEFS = {
    # ── Debuffs existants ─────────────────────────────────────
    "bleeding":        {"stat": "block",           "delta": -0.15, "mode": "flat"},
    "poisoned":        {"stat": "control_resist",  "delta": -0.15, "mode": "flat"},
    "burning":         {"stat": "defense",         "delta": -0.15, "mode": "percent_base"},
    "cursed":          {"stat": "heal_effect",     "delta": -0.50, "mode": "flat"},
    "frozen":          {"stat": "basic_dmg_taken", "delta": +0.20, "mode": "flat"},
    "petrified":       {"stat": "skill_dmg_taken", "delta": +0.10, "mode": "flat"},
    "taunted":         {"stat": "hit_chance",      "delta": -0.15, "mode": "flat"},
    "stun":            {"stat": None,              "delta":  0,    "mode": "flat"},
    "frostbite":       {"stat": None,              "delta":  0,    "mode": "flat"},
    "armor_break":     {"stat": "defense",         "delta": -0.25, "mode": "percent_base"},
    "atk_reduce":      {"stat": "atk",             "delta": -0.15, "mode": "percent_base"},
    "spd_reduce":      {"stat": "spd",             "delta": -100,  "mode": "flat"},
    "crit_shred":      {"stat": "cr",              "delta": -0.35, "mode": "flat"},
    "armor_reduction": {"stat": "defense",         "delta": -0.40, "mode": "percent_base"},

    # ── Nouveaux debuffs ──────────────────────────────────────

    # burn : alias de burning (Ruby P1/P3 — Draconic Artillery).
    # Même effet que burning : réduit la défense de la cible.
    "burn":            {"stat": "defense",         "delta": -0.15, "mode": "percent_base"},

    # freeze : alias de frozen (Ruby — cleanse freeze dans l'ult).
    # Même effet que frozen : augmente les dégâts basiques reçus.
    "freeze":          {"stat": "basic_dmg_taken", "delta": +0.20, "mode": "flat"},

    # dark_corruption : la cible reçoit 20% de dégâts supplémentaires
    # de toutes sources (Necro — Dark Affliction active).
    # Implémenté via dmg_taken_bonus, vérifié à chaque calcul de dégâts.
    "dark_corruption": {"stat": "dmg_taken_bonus", "delta": +0.20, "mode": "flat"},

    # heal_reduce : réduit le Heal Effect de la cible de 35%
    # (Scythe P2 — Skullbound Harvest, attaque basique).
    # distinct de cursed qui réduit de 50% — les deux peuvent coexister.
    "heal_reduce":     {"stat": "heal_effect",     "delta": -0.35, "mode": "flat"},

    # cr_reduce : réduit la Crit Chance de la cible de 40%
    # (Necro P2 — Cursed Strikes, attaque basique).
    "cr_reduce":       {"stat": "cr",              "delta": -0.40, "mode": "flat"},

    # skullbound_seal : marqueur de Scythe (P2 & P3).
    # Pas d'effet de stat direct — la logique est gérée dans scythe.py
    # (ignore armure, 200% dmg bonus, Curse AoE au prochain skill, etc.).
    "skullbound_seal": {"stat": None,              "delta":  0,    "mode": "flat"},

    # molten_fury : la cible reçoit 20% de dégâts supplémentaires
    # (Terryx active & P2 — Dino Strike). Vérifié dans _calc_damage de Terryx.
    "molten_fury":     {"stat": "dmg_taken_bonus", "delta": +0.20, "mode": "flat"},

    # dmg_reduce_shred : réduit le Damage Reduction de la cible de 30%
    # (Terryx active — Attaque 3, 50% chance).
    "dmg_reduce_shred":{"stat": "dmg_reduce",      "delta": -0.30, "mode": "flat"},
}

CONTROL_DEBUFFS = {"stun", "frozen"}


def apply_debuff(character, debuff_type: str, duration: int, source=None, dot_multiplier: float = None) -> bool:
    """
    Applique un debuff sur le personnage.

    Règle de stacking :
    - Debuff DoT (dot_multiplier fourni) : TOUJOURS une nouvelle instance,
      même si le même type existe déjà (ex: Chancer + Zemus appliquent
      chacun leur propre "cursed" ; Chancer réapplique frostbite → x2 dmg).
    - Debuff de stat pur (dot_multiplier=None) : une seule instance par type,
      on refresh seulement la durée (pour éviter un double malus de stat).
    """
    immune_list = getattr(character, "_immune", [])
    if debuff_type in immune_list:
        return False

    if debuff_type in CONTROL_DEBUFFS:
        resist_roll = random.random()
        resist_value = getattr(character, "control_resist", 0)
        if resist_roll < resist_value:
            return False

    # ── Debuff DoT : toujours empiler ────────────────────────
    if dot_multiplier is not None:
        already_exists = any(d["type"] == debuff_type for d in character.debuffs)
        character.debuffs.append({
            "type":           debuff_type,
            "duration":       duration,
            "source":         source,
            "dot_multiplier": dot_multiplier,
        })
        # L'effet de stat (ex: frostbite → +20% basic_dmg_taken) n'est appliqué
        # qu'une seule fois, à la première instance.
        if not already_exists:
            _apply_stat_effect(character, debuff_type, apply=True)
        return True

    # ── Debuff de stat pur : une seule instance, refresh durée ───
    for existing in character.debuffs:
        if existing["type"] == debuff_type:
            existing["duration"] = max(existing["duration"], duration)
            return True

    character.debuffs.append({
        "type":           debuff_type,
        "duration":       duration,
        "source":         source,
        "dot_multiplier": None,
    })
    _apply_stat_effect(character, debuff_type, apply=True)
    if debuff_type == "stun":
        character.is_stunned = True
    return True


def remove_debuff(character, debuff_type: str):
    """
    Retire UNE instance du debuff (la première expirée trouvée).
    L'effet de stat n'est reversé que quand la DERNIÈRE instance disparaît.
    """
    # Compte les instances avant suppression
    instances = [d for d in character.debuffs if d["type"] == debuff_type]
    if not instances:
        return

    # Retire la première instance trouvée
    character.debuffs.remove(instances[0])

    # Ne reverser l'effet de stat que si c'était la dernière instance
    remaining = [d for d in character.debuffs if d["type"] == debuff_type]
    if not remaining:
        _apply_stat_effect(character, debuff_type, apply=False)
        if debuff_type == "stun":
            character.is_stunned = False


def tick_debuffs(character):
    total_dot_dmg = 0.0
    for debuff in character.debuffs:
        multi = debuff.get("dot_multiplier")
        if multi is None:
            continue

        source = debuff.get("source")
        source_char = getattr(source, "character", source) if source else None
        source_atk  = getattr(source_char, "atk", 0.0) if source_char else 0.0
        source_weapons = getattr(source_char, "weapon", []) if source_char else []
        #print(f"{character.name} takes DoT from {debuff['type']} from {source_char.name} (multi={multi:.2f}, source_atk={source_atk:.2f})")
        base_dot = source_atk * multi

        for w in source_weapons:
            if hasattr(w, "modify_dot_damage"):
                #print(f"{source_char.name} dot damage before {w.__class__.__name__}: {base_dot:.2f}")
                base_dot = w.modify_dot_damage(source_char, base_dot)
                #print(f"{source_char.name} dot damage after {w.__class__.__name__}: {base_dot:.2f}")

        character.hp      -= base_dot
        total_dot_dmg     += base_dot

        #if source_char and source_char.name == "Chancer":
            #print(f"Chancer inflige DOT {total_dot_dmg:.2f} total DoT damage from Chancer's {debuff['type']} (base_dot={base_dot:.2f})")
    if character.hp <= 0:
        character.is_alive = False

    # Décrément + expiration — inchangé
    expired = []
    for debuff in character.debuffs:
        debuff["duration"] -= 1
        if debuff["duration"] <= 0:
            expired.append(debuff["type"])
    for dtype in expired:
        remove_debuff(character, dtype)

    return total_dot_dmg


def has_debuff(character, debuff_type: str) -> bool:
    return any(d["type"] == debuff_type for d in character.debuffs)


def get_debuff_stacks(character, debuff_type: str) -> int:
    return sum(1 for d in character.debuffs if d["type"] == debuff_type)


def _apply_stat_effect(character, debuff_type: str, apply: bool):
    defn = DEBUFF_DEFS.get(debuff_type)
    if defn is None or defn["stat"] is None:
        return

    stat  = defn["stat"]
    mode  = defn["mode"]
    delta = defn["delta"]

    if not apply:
        delta = -delta

    if not hasattr(character, stat):
        setattr(character, stat, 0)

    if mode == "percent_base":
        base_stat = "base_" + stat
        base_val  = getattr(character, base_stat, getattr(character, stat, 0))
        setattr(character, stat, getattr(character, stat) + delta * abs(base_val))
    else:
        setattr(character, stat, getattr(character, stat) + delta)


# ═══════════════════════════════════════════════════════════════
#  SYSTÈME DE BUFFS
# ═══════════════════════════════════════════════════════════════

BUFF_DEFS = {
    # ── Buffs existants ───────────────────────────────────────
    "skill_dmg_up":      {"stat": "skill_dmg",      "delta": +0.25, "mode": "flat"},
    "atk_steal":         {"stat": "atk",             "delta":  0,    "mode": "flat"},

    # ── Nouveaux buffs ────────────────────────────────────────

    # atk_up : augmente l'ATK (Scythe active — HP < 50%).
    # La valeur réelle est toujours passée via delta_override.
    "atk_up":            {"stat": "atk",             "delta": +0.25, "mode": "percent_base"},

    # cd_up : augmente le Crit Damage (Ruby P3, Scythe active & P3).
    "cd_up":             {"stat": "cd",              "delta": +0.20, "mode": "flat"},

    # cr_up : augmente la Crit Chance (Scythe P3 — on_seal_kill).
    "cr_up":             {"stat": "cr",              "delta": +0.35, "mode": "flat"},

    # armor_break_up : augmente l'Armor Break (Scythe active — Killing Blow).
    "armor_break_up":    {"stat": "armor_break",     "delta": +0.30, "mode": "flat"},

    # control_resist_up : augmente la Control Resist (Scythe active — HP > 50%).
    "control_resist_up": {"stat": "control_resist",  "delta": +0.50, "mode": "flat"},

    # magic_shield : bouclier magique (Ruby P2, Chancer P2 ODD).
    # Pas de stat directe — géré manuellement dans on_hit_received().
    "magic_shield":      {"stat": None,              "delta":  0,    "mode": "flat"},

    # tristrike_atk_up : bonus ATK temporaire post-ult de Terryx (+15% par cible touchée).
    # La valeur est toujours passée via delta_override (en valeur absolue d'ATK).
    "tristrike_atk_up":  {"stat": "atk",             "delta":  0,    "mode": "flat"},

    # ── Otto ──────────────────────────────────────────────────
    "otto_cr_up":        {"stat": "cr",              "delta":  0,    "mode": "flat"},
    "otto_atk_up":       {"stat": "atk",             "delta":  0,    "mode": "flat"},
    "otto_dr_up":        {"stat": "dmg_reduce",      "delta":  0,    "mode": "flat"},
    "otto_spd_up":       {"stat": "spd",             "delta":  0,    "mode": "flat"},

    # ── Zura ──────────────────────────────────────────────────
    "last_bastion_heal_zura": {"stat": "heal_effect", "delta": 0,    "mode": "flat"},
    "rally_atk_zura":    {"stat": "atk",             "delta":  0,    "mode": "flat"},

    # ── Ruby ──────────────────────────────────────────────────
    "trigger_happy_spd": {"stat": "spd",             "delta":  0,    "mode": "flat"},
    "trigger_happy_cr":  {"stat": "cr",              "delta":  0,    "mode": "flat"},
    "trigger_happy_cd":  {"stat": "cd",              "delta":  0,    "mode": "flat"},

    # ── Teepo ─────────────────────────────────────────────────
    "survival_dmg_reduce": {"stat": "dmg_reduce",   "delta":  0,    "mode": "flat"},

    # ── Leene ─────────────────────────────────────────────────
    "leene_armor_steal":    {"stat": "defense",      "delta":  0,    "mode": "flat"},
    "leene_armorbreak_up":  {"stat": "armor_break",  "delta":  0,    "mode": "flat"},
    "leene_skill_dmg_up":   {"stat": "skill_dmg",    "delta":  0,    "mode": "flat"},
}


def apply_buff(character, buff_type: str, duration: int, delta_override: float = None, source=None) -> bool:
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
    for b in list(character.buffs):
        if b["type"] == buff_type:
            defn = BUFF_DEFS.get(buff_type, {})
            _apply_buff_stat(character, defn.get("stat"), b["delta"], defn.get("mode", "flat"), apply=False)
            character.buffs.remove(b)


def tick_buffs(character):
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