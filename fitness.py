from utils import parse_catalog, parse_students


# ============================================================
# SCORE 1: TIME PREFERENCE (30% weight)
# ============================================================

def score_time_preference(student, assignments, catalog):
    """
    How many of the student's class hours fall in their preferred times?
    Returns 0-1, higher is better.
    """
    if not assignments:
        return 0.0

    preferred = set(student.time_preference.preferred_slots)
    score = 0
    total_slots = 0

    for a in assignments:
        section = catalog[a.course_id].sections[a.section - 1]
        for slot in section.schedule:
            total_slots += 1
            if slot.time in preferred:
                score += 1

    return score / total_slots if total_slots > 0 else 0.0


# ============================================================
# SCORE 2: GAP MINIMIZATION (25% weight)
# ============================================================

def score_gap_minimisation(student, assignments, catalog):
    """
    Penalizes big gaps between classes.
    If you have classes at 9am and 2pm with nothing in between, that's bad.
    Returns 0-1, 1 means no gaps at all.
    """
    if not assignments:
        return 0.0

    # Group times by day
    day_times = {}
    for a in assignments:
        section = catalog[a.course_id].sections[a.section - 1]
        for slot in section.schedule:
            day_times.setdefault(slot.day, []).append(slot.time)

    total_gap = 0
    max_possible = 0

    for day, times in day_times.items():
        if len(times) < 2:
            continue
        times.sort()
        first = times[0]
        last = times[-1]
        span = last - first + 1  # hours from first to last
        gap = span - len(times)  # empty hours in between
        total_gap += gap
        max_possible += span - 1  # worst case

    if max_possible == 0:
        return 1.0

    return 1.0 - (total_gap / max_possible)


# ============================================================
# SCORE 3: FRIEND SATISFACTION (20% weight)
# ============================================================

def score_friend_satisfaction(student_id, assignments, all_schedules, students):
    """
    Counts how many courses friends take together (same course + same section).
    """
    if not assignments:
        return 0.0

    friends = students[student_id].friends
    if not friends:
        return 1.0  # no friends to please, perfect score

    my_sections = {a.course_id: a.section for a in assignments}

    total_possible = 0
    total_shared = 0

    for friend_id in friends:
        if friend_id not in all_schedules:
            continue

        friend_assignments = all_schedules[friend_id]
        friend_sections = {a.course_id: a.section for a in friend_assignments}

        common = set(my_sections.keys()) & set(friend_sections.keys())
        total_possible += len(common)

        for course_id in common:
            if my_sections[course_id] == friend_sections[course_id]:
                total_shared += 1

    return total_shared / total_possible if total_possible > 0 else 1.0


# ============================================================
# SCORE 4: WORKLOAD BALANCE (15% weight)
# ============================================================

def score_workload_balance(student, assignments, catalog):
    """
    Penalizes days where all classes are hard (difficulty 3).
    You don't want three hard classes on the same day!
    """
    if not assignments:
        return 0.0

    day_difficulties = {}
    for a in assignments:
        course = catalog[a.course_id]
        section = course.sections[a.section - 1]
        for slot in section.schedule:
            day_difficulties.setdefault(slot.day, []).append(course.difficulty)

    if not day_difficulties:
        return 1.0

    bad_days = 0
    for day, diffs in day_difficulties.items():
        if len(diffs) >= 2 and all(d == 3 for d in diffs):
            bad_days += 1

    return 1.0 - (bad_days / len(day_difficulties))


# ============================================================
# SCORE 5: LUNCH BREAK (10% weight)
# ============================================================

def score_lunch_break(student, assignments, catalog):
    """
    Counts days where 12pm-1pm is free.
    Perfect score if at least 3 days have lunch free.
    """
    all_days = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday"}
    busy_days = set()

    for a in assignments:
        section = catalog[a.course_id].sections[a.section - 1]
        for slot in section.schedule:
            if slot.time == 12:  # lunch hour
                busy_days.add(slot.day)

    free_days = len(all_days - busy_days)
    return min(free_days / 3.0, 1.0)  # 3 free days = full score


# ============================================================
# PENALTIES - these hurt the fitness score
# ============================================================

def calculate_penalties(student, assignments, catalog, fitness_config):
    """
    Checks all the hard constraints. Each violation subtracts points.
    """
    penalty = 0

    # Time conflicts - can't be in two places at once
    seen_slots = set()
    for a in assignments:
        section = catalog[a.course_id].sections[a.section - 1]
        for slot in section.schedule:
            key = (slot.day, slot.time)
            if key in seen_slots:
                penalty += fitness_config.penalty_time_conflict
            seen_slots.add(key)

    # Blocked time violations - student said they're not available
    blocked = {(s.day, s.time) for s in student.time_preference.blocked_slots}
    for a in assignments:
        section = catalog[a.course_id].sections[a.section - 1]
        for slot in section.schedule:
            if (slot.day, slot.time) in blocked:
                penalty += fitness_config.penalty_blocked_time

    # Credit requirements - must have exactly 15 credits
    total_credits = sum(catalog[a.course_id].credits for a in assignments)
    if total_credits != student.required_credits:
        penalty += fitness_config.penalty_missing_credits

    # Max courses per day - can't have 4 classes on the same day
    day_counts = {}
    for a in assignments:
        section = catalog[a.course_id].sections[a.section - 1]
        days_this_course = {slot.day for slot in section.schedule}
        for day in days_this_course:
            day_counts[day] = day_counts.get(day, 0) + 1

    for day, count in day_counts.items():
        if count > student.max_courses_per_day:
            penalty += fitness_config.penalty_too_many_courses

    # S5 hates 8am classes
    if student.avoid_early:
        for a in assignments:
            section = catalog[a.course_id].sections[a.section - 1]
            for slot in section.schedule:
                if slot.time == 8:
                    penalty += 200  # soft penalty, not as harsh as hard constraints

    return penalty


# ============================================================
# MAIN FITNESS - puts it all together
# ============================================================

def evaluate_student(student_id, assignments, all_schedules, students, catalog, fitness_config):
    """Calculates fitness for one student"""
    student = students[student_id]

    # Get all component scores (each 0-1)
    s_time = score_time_preference(student, assignments, catalog)
    s_gap = score_gap_minimisation(student, assignments, catalog)
    s_friend = score_friend_satisfaction(student_id, assignments, all_schedules, students)
    s_workload = score_workload_balance(student, assignments, catalog)
    s_lunch = score_lunch_break(student, assignments, catalog)

    # Weighted sum
    score = (
            fitness_config.w_time_preference * s_time +
            fitness_config.w_gap_minimization * s_gap +
            fitness_config.w_friend_satisfaction * s_friend +
            fitness_config.w_workload_balance * s_workload +
            fitness_config.w_lunch_break * s_lunch
    )

    # Subtract penalties
    score += calculate_penalties(student, assignments, catalog, fitness_config)

    return score


def evaluate_chromosome(chromosome, students, catalog, fitness_config):
    """Evaluates all 5 students and sums their scores"""
    total = 0.0

    for student_id, assignments in chromosome.schedule.items():
        total += evaluate_student(
            student_id, assignments, chromosome.schedule,
            students, catalog, fitness_config
        )

    chromosome.fitness = total
    return total


def evaluate_population(population, students, catalog, fitness_config):
    """Evaluates every chromosome in the population"""
    fitnesses = []
    for chrom in population:
        fitnesses.append(evaluate_chromosome(chrom, students, catalog, fitness_config))
    return fitnesses