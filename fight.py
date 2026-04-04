# ═══════════════════════════════════════════════════════════════
#  FIGHT.PY  —  Moteur de simulation d'équipe
# ═══════════════════════════════════════════════════════════════

def simulate_team(team_build: dict, nb_rounds: int = 10, nb_simulations: int = 8) -> float:
    """
    Simule nb_simulations combats pour une équipe et retourne le DPS moyen total.

    team_build : dict retourné par Genome.to_team_build()
    {
        0: {
            "fighter_cls": FighterClass,
            "weapons":     [WeaponClass, WeaponClass, WeaponClass],
            "dragons":     [DragonClass, DragonClass],
        },
        ...
    }
    """
    total = sum(
        _run_once(team_build, nb_rounds)
        for _ in range(nb_simulations)
    )
    return total / nb_simulations


def _run_once(team_build: dict, nb_rounds: int) -> float:
    """Un seul combat complet. Retourne les dégâts totaux de l'équipe."""

    # ── Instanciation de l'équipe ──────────────────────────────
    fighters = []
    for slot in team_build.values():
        f = slot["fighter_cls"]()
        f.character.weapon  = [w() for w in slot["weapons"]]
        f.character.dragons = [d(f.character) for d in slot["dragons"]]
        fighters.append(f)

    allies  = fighters
    dummy   = team_build[0]["fighter_cls"]()
    dummy.character.hp = 9_999_999_999
    enemies = [dummy]

    # ── Battle start ──────────────────────────────────────────
    for f in fighters:
        for w in f.character.weapon:
            w.on_battle_start(f.character)
        for d in f.character.dragons:
            d.on_battle_start(f.character)

    total_dmg = 0

    # ── Boucle de combat ─────────────────────────────────────
    for round_num in range(1, nb_rounds + 1):
        for f in fighters:
            for w in f.character.weapon:
                w.on_round_start(f.character, allies)
            for d in f.character.dragons:
                d.on_round_start(f.character, allies)

        for f in fighters:
            if not f.character.is_alive or f.character.is_stunned:
                continue
            if f.character.energy >= 100:
                f.character.energy = 0
                total_dmg += f.ult(enemies, allies)
            else:
                total_dmg += f.basic_atk(enemies, allies)

        for f in fighters:
            for w in f.character.weapon:
                w.on_round_end(f.character, allies, round_num)
            for d in f.character.dragons:
                d.on_round_end(f.character, allies, round_num)

    return total_dmg