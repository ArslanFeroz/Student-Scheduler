import random
import time
import os
import matplotlib.pyplot as plt

from utils import parse_config, parse_catalog, parse_students
from chromosome import initialise_population, CourseAssignment
from fitness import evaluate_population, evaluate_chromosome
from selection import get_elite, select_parent
from operators import crossover, mutate, copy_chromosome


# ============================================================
# DIVERSITY - how different are the schedules?
# ============================================================

def measure_diversity(population):
    """Fraction of unique chromosomes in population"""

    def signature(chrom):
        sig = []
        for sid in sorted(chrom.schedule.keys()):
            for a in sorted(chrom.schedule[sid], key=lambda x: x.course_id):
                sig.append((sid, a.course_id, a.section))
        return tuple(sig)

    unique = {signature(c) for c in population}
    return len(unique) / len(population)


# ============================================================
# INJECT RANDOM - add fresh blood when diversity is low
# ============================================================

def inject_random(population, fitnesses, students, catalog, injection_rate):
    """Replace worst individuals with new random ones"""
    from chromosome import create_random_chromosome

    n_inject = max(1, int(len(population) * injection_rate))

    # Sort by fitness ascending (worst first)
    sorted_pairs = sorted(zip(fitnesses, range(len(population))), key=lambda x: x[0])
    replace_indices = [idx for _, idx in sorted_pairs[:n_inject]]

    for idx in replace_indices:
        population[idx] = create_random_chromosome(students, catalog)

    return population


# ============================================================
# TERMINATION CHECK - when to stop
# ============================================================

def should_terminate(generation, max_gen, best_history, patience, improvement_threshold,
                     fitnesses, similarity_threshold, similarity_tolerance):
    # Max generations reached?
    if generation >= max_gen:
        print(f"Stopping: reached {max_gen} generations")
        return True

    # No improvement for a while?
    if len(best_history) >= patience:
        recent = best_history[-1]
        old = best_history[-patience]
        if old != 0:
            improvement = abs(recent - old) / abs(old)
            if improvement < improvement_threshold:
                print(f"Stopping: no improvement for {patience} gens")
                return True

    # Population all similar?
    if len(fitnesses) > 0:
        max_fit = max(fitnesses)
        min_fit = min(fitnesses)
        mid = (max_fit + min_fit) / 2
        similar = sum(1 for f in fitnesses if abs(f - mid) <= similarity_tolerance * abs(mid))
        if similar / len(fitnesses) >= similarity_threshold:
            print(f"Stopping: {similar / len(fitnesses):.1%} of pop similar")
            return True

    return False


# ============================================================
# PRINT SCHEDULE - make it readable
# ============================================================

def print_best_schedule(chromosome, students, catalog):
    print("\n" + "=" * 70)
    print("BEST SCHEDULE FOUND")
    print("=" * 70)

    for sid, assignments in chromosome.schedule.items():
        student = students[sid]
        total_credits = sum(catalog[a.course_id].credits for a in assignments)

        print(f"\n{sid} - {student.name} (Year {student.year}, {total_credits} credits)")
        print("-" * 65)
        print(f"{'Course':<8} {'Name':<28} {'Sec'} {'Days':<18} {'Time'}")
        print("-" * 65)

        for a in assignments:
            course = catalog[a.course_id]
            section = course.sections[a.section - 1]
            days = "/".join(s.day[:3] for s in section.schedule)
            time = section.schedule[0].time
            am_pm = "AM" if time < 12 else "PM"
            time_str = f"{time if time <= 12 else time - 12}:00 {am_pm}"
            print(f"{a.course_id:<8} {course.name[:27]:<28} {a.section}   {days:<18} {time_str}")


# ============================================================
# PLOTTING
# ============================================================

def plot_convergence(all_runs_best, all_runs_avg, all_runs_worst, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    plt.figure(figsize=(12, 6))

    # Plot each run lightly
    for best, avg, worst in zip(all_runs_best, all_runs_avg, all_runs_worst):
        plt.plot(best, alpha=0.3, color='green')
        plt.plot(avg, alpha=0.3, color='blue')
        plt.plot(worst, alpha=0.3, color='red')

    # Plot average with bold lines
    min_len = min(len(b) for b in all_runs_best)
    mean_best = [sum(run[g] for run in all_runs_best) / len(all_runs_best) for g in range(min_len)]
    mean_avg = [sum(run[g] for run in all_runs_avg) / len(all_runs_avg) for g in range(min_len)]
    mean_worst = [sum(run[g] for run in all_runs_worst) / len(all_runs_worst) for g in range(min_len)]

    plt.plot(mean_best, color='green', linewidth=2, label='Best')
    plt.plot(mean_avg, color='blue', linewidth=2, label='Average')
    plt.plot(mean_worst, color='red', linewidth=2, label='Worst')

    plt.xlabel('Generation')
    plt.ylabel('Fitness')
    plt.title('GA Convergence')
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'convergence.png'))
    plt.close()
    print(f"Saved convergence plot to {output_dir}/convergence.png")


def plot_diversity(all_runs_diversity, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    plt.figure(figsize=(12, 6))

    for div in all_runs_diversity:
        plt.plot(div, alpha=0.3, color='purple')

    min_len = min(len(d) for d in all_runs_diversity)
    mean_div = [sum(run[g] for run in all_runs_diversity) / len(all_runs_diversity) for g in range(min_len)]
    plt.plot(mean_div, color='purple', linewidth=2, label='Mean diversity')
    plt.axhline(y=0.3, color='red', linestyle='--', label='Threshold (30%)')

    plt.xlabel('Generation')
    plt.ylabel('Diversity')
    plt.title('Population Diversity Over Time')
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'diversity.png'))
    plt.close()
    print(f"Saved diversity plot to {output_dir}/diversity.png")


# ============================================================
# MAIN GA LOOP
# ============================================================

def run_ga(config, students, catalog, seed=None):
    if seed is not None:
        random.seed(seed)

    # Create initial population
    population = initialise_population(config, students, catalog)
    fitnesses = evaluate_population(population, students, catalog, config.fitness)

    best_history = []
    avg_history = []
    worst_history = []
    diversity_history = []

    overall_best = None
    overall_best_fit = float('-inf')

    start_time = time.time()

    for generation in range(config.termination.max_generations):
        # Track stats
        best_fit = max(fitnesses)
        avg_fit = sum(fitnesses) / len(fitnesses)
        worst_fit = min(fitnesses)
        diversity = measure_diversity(population)

        best_history.append(best_fit)
        avg_history.append(avg_fit)
        worst_history.append(worst_fit)
        diversity_history.append(diversity)

        # Update best overall
        best_idx = fitnesses.index(best_fit)
        if best_fit > overall_best_fit:
            overall_best_fit = best_fit
            overall_best = copy_chromosome(population[best_idx])

        # Print progress
        if generation % 10 == 0:
            print(f"Gen {generation:3d} | Best: {best_fit:8.2f} | Avg: {avg_fit:8.2f} | Div: {diversity:.2%}")

        # Check if we should stop
        if should_terminate(generation, config.termination.max_generations,
                            best_history, config.termination.patience,
                            config.termination.improvement_threshold,
                            fitnesses, config.termination.similarity_threshold,
                            config.termination.similarity_tolerance):
            break

        # Build next generation
        next_pop = []

        # Elitism - keep the best ones
        elites = get_elite(population, fitnesses, config.population.elitism_rate)
        next_pop.extend([copy_chromosome(e) for e in elites])

        # Diversity injection if needed
        if generation % 10 == 0 and diversity < 0.3:
            population = inject_random(population, fitnesses, students, catalog, 0.2)
            fitnesses = evaluate_population(population, students, catalog, config.fitness)

        # Adaptive mutation if diversity is low
        adaptive = (diversity < 0.3)

        # Create children
        while len(next_pop) < config.population.size:
            parent_a = select_parent(population, fitnesses, config.selection)
            parent_b = select_parent(population, fitnesses, config.selection)

            child_a, child_b = crossover(parent_a, parent_b, students, catalog, config.crossover)

            child_a = mutate(child_a, students, catalog, config.mutation, adaptive)
            child_b = mutate(child_b, students, catalog, config.mutation, adaptive)

            next_pop.append(child_a)
            if len(next_pop) < config.population.size:
                next_pop.append(child_b)

        population = next_pop
        fitnesses = evaluate_population(population, students, catalog, config.fitness)

    elapsed = time.time() - start_time
    print(f"\nFinished after {generation + 1} generations in {elapsed:.2f} seconds")
    print(f"Best fitness: {overall_best_fit:.2f}")

    return overall_best, overall_best_fit, best_history, avg_history, worst_history, diversity_history


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("COURSE SCHEDULING GENETIC ALGORITHM")
    print("=" * 60)

    config = parse_config()
    catalog = parse_catalog()
    students = parse_students()

    # Create output directories
    os.makedirs("plots", exist_ok=True)
    os.makedirs("results", exist_ok=True)

    num_runs = config.experiment.num_runs
    print(f"\nRunning {num_runs} independent runs...\n")

    all_best_fitness = []
    all_best_history = []
    all_avg_history = []
    all_worst_history = []
    all_diversity_history = []
    all_best_chroms = []

    for run in range(num_runs):
        print(f"\n--- Run {run + 1}/{num_runs} ---")
        seed = config.experiment.random_seed + run

        best_chrom, best_fit, bh, ah, wh, dh = run_ga(
            config, students, catalog, seed
        )

        all_best_fitness.append(best_fit)
        all_best_history.append(bh)
        all_avg_history.append(ah)
        all_worst_history.append(wh)
        all_diversity_history.append(dh)
        all_best_chroms.append(best_chrom)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY ACROSS ALL RUNS")
    print("=" * 60)
    print(f"Best fitness:  {max(all_best_fitness):.2f}")
    print(f"Worst fitness: {min(all_best_fitness):.2f}")
    print(f"Average:       {sum(all_best_fitness) / num_runs:.2f}")

    # Find and display best overall schedule
    best_run_idx = all_best_fitness.index(max(all_best_fitness))
    best_chrom = all_best_chroms[best_run_idx]
    print_best_schedule(best_chrom, students, catalog)

    # Save plots
    plot_convergence(all_best_history, all_avg_history, all_worst_history, "plots")
    plot_diversity(all_diversity_history, "plots")

    print("\nDone! Check 'plots/' for graphs.")


if __name__ == "__main__":
    main()