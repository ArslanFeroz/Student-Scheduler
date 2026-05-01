import random


# ============================================================
# ELITISM - keep the best ones
# ============================================================

def get_elite(population, fitnesses, elite_rate):
    """Returns the top chromosomes unchanged"""
    n_elite = max(1, int(len(population) * elite_rate))

    # Sort by fitness descending
    sorted_pairs = sorted(zip(fitnesses, population), key=lambda x: x[0], reverse=True)

    return [chrom for _, chrom in sorted_pairs[:n_elite]]


# ============================================================
# TOURNAMENT SELECTION - pick best from random group
# ============================================================

def tournament_select(population, fitnesses, tournament_size=5):
    """
    Pick a few random individuals, return the best one.
    This tends to favor higher fitness without being too greedy.
    """
    indices = random.sample(range(len(population)), min(tournament_size, len(population)))
    best_idx = max(indices, key=lambda i: fitnesses[i])
    return population[best_idx]


# ============================================================
# ROULETTE WHEEL - probability proportional to fitness
# ============================================================

def roulette_select(population, fitnesses):
    """
    Each individual's chance is proportional to their fitness.
    Need to handle negative fitness by shifting values up.
    """
    min_fit = min(fitnesses)
    # Shift so minimum becomes slightly positive
    shifted = [f - min_fit + 1e-6 for f in fitnesses]
    total = sum(shifted)

    pick = random.uniform(0, total)
    running = 0.0

    for i, weight in enumerate(shifted):
        running += weight
        if running >= pick:
            return population[i]

    return population[-1]  # fallback


def select_parent(population, fitnesses, selection_config):
    """
    Picks one parent using tournament or roulette.
    Tournament is 70%, roulette is 30% as per assignment.
    """
    if random.random() < 0.7:
        return tournament_select(population, fitnesses, selection_config.tournament_size)
    else:
        return roulette_select(population, fitnesses)