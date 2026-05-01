import random
from utils import get_valid_sections
from chromosome import Chromosome, CourseAssignment, pick_electives


# ============================================================
# DEEP COPY - makes an independent copy
# ============================================================

def copy_chromosome(chrom):
    """Returns a completely independent copy"""
    new_chrom = Chromosome()
    for sid, assignments in chrom.schedule.items():
        new_assignments = [CourseAssignment(a.course_id, a.section) for a in assignments]
        new_chrom.set_student_schedule(sid, new_assignments)
    return new_chrom


# ============================================================
# REPAIR - fixes broken schedules after crossover/mutation
# ============================================================

def repair(chromosome, students, catalog, max_attempts=10):
    """
    Tries to fix any hard constraint violations.
    This is crucial - crossover can create invalid schedules,
    so we need to patch them up.
    """
    for sid, assignments in chromosome.schedule.items():
        student = students[sid]
        blocked = {(s.day, s.time) for s in student.time_preference.blocked_slots}

        for attempt in range(max_attempts):
            fixed = True

            # Check every pair for time conflicts
            for i in range(len(assignments)):
                sec_i = catalog[assignments[i].course_id].sections[assignments[i].section - 1]
                slots_i = {(s.day, s.time) for s in sec_i.schedule}

                # Check blocked times
                if slots_i & blocked:
                    others = assignments[:i] + assignments[i + 1:]
                    valid = get_valid_sections(catalog, student, assignments[i].course_id, others)
                    if valid:
                        assignments[i].section = random.choice(valid)
                    fixed = False
                    continue

                for j in range(i + 1, len(assignments)):
                    sec_j = catalog[assignments[j].course_id].sections[assignments[j].section - 1]
                    slots_j = {(s.day, s.time) for s in sec_j.schedule}

                    if slots_i & slots_j:
                        # Try to fix j first
                        others = assignments[:j] + assignments[j + 1:]
                        valid = get_valid_sections(catalog, student, assignments[j].course_id, others)
                        if valid:
                            assignments[j].section = random.choice(valid)
                        else:
                            # If that fails, try fixing i
                            others = assignments[:i] + assignments[i + 1:]
                            valid = get_valid_sections(catalog, student, assignments[i].course_id, others)
                            if valid:
                                assignments[i].section = random.choice(valid)
                        fixed = False

            if fixed:
                break

    return chromosome


# ============================================================
# CROSSOVER 1: SINGLE POINT - cut at a student boundary
# ============================================================

def crossover_single_point(parent_a, parent_b, students, catalog):
    """
    Cut the chromosome at a random student.
    Child gets first few students from A, rest from B.
    """
    student_ids = list(parent_a.schedule.keys())
    cut = random.randint(1, len(student_ids) - 1)

    child_1 = Chromosome()
    child_2 = Chromosome()

    for i, sid in enumerate(student_ids):
        if i < cut:
            child_1.set_student_schedule(sid,
                                         [CourseAssignment(a.course_id, a.section) for a in parent_a.schedule[sid]])
            child_2.set_student_schedule(sid,
                                         [CourseAssignment(a.course_id, a.section) for a in parent_b.schedule[sid]])
        else:
            child_1.set_student_schedule(sid,
                                         [CourseAssignment(a.course_id, a.section) for a in parent_b.schedule[sid]])
            child_2.set_student_schedule(sid,
                                         [CourseAssignment(a.course_id, a.section) for a in parent_a.schedule[sid]])

    child_1 = repair(child_1, students, catalog)
    child_2 = repair(child_2, students, catalog)

    return child_1, child_2


# ============================================================
# CROSSOVER 2: UNIFORM - flip a coin for each student
# ============================================================

def crossover_uniform(parent_a, parent_b, students, catalog):
    """
    For each student, randomly choose which parent they inherit from.
    """
    student_ids = list(parent_a.schedule.keys())

    child_1 = Chromosome()
    child_2 = Chromosome()

    for sid in student_ids:
        if random.random() < 0.5:
            child_1.set_student_schedule(sid,
                                         [CourseAssignment(a.course_id, a.section) for a in parent_a.schedule[sid]])
            child_2.set_student_schedule(sid,
                                         [CourseAssignment(a.course_id, a.section) for a in parent_b.schedule[sid]])
        else:
            child_1.set_student_schedule(sid,
                                         [CourseAssignment(a.course_id, a.section) for a in parent_b.schedule[sid]])
            child_2.set_student_schedule(sid,
                                         [CourseAssignment(a.course_id, a.section) for a in parent_a.schedule[sid]])

    child_1 = repair(child_1, students, catalog)
    child_2 = repair(child_2, students, catalog)

    return child_1, child_2


# ============================================================
# CROSSOVER 3: COURSE BASED - swap specific courses
# ============================================================

def crossover_course_based(parent_a, parent_b, students, catalog):
    """
    For a random subset of courses, swap sections between parents.
    """
    child_1 = copy_chromosome(parent_a)
    child_2 = copy_chromosome(parent_b)

    for sid in parent_a.schedule.keys():
        assignments_a = parent_a.schedule[sid]
        assignments_b = parent_b.schedule[sid]

        # Pick random courses to swap
        n_courses = len(assignments_a)
        n_swap = random.randint(1, max(1, n_courses // 2))
        swap_indices = random.sample(range(n_courses), n_swap)

        for idx in swap_indices:
            if idx < len(assignments_b):
                # Swap sections
                sec_a = assignments_a[idx].section
                sec_b = assignments_b[idx].section
                child_1.schedule[sid][idx].section = sec_b
                child_2.schedule[sid][idx].section = sec_a

    child_1 = repair(child_1, students, catalog)
    child_2 = repair(child_2, students, catalog)

    return child_1, child_2


def crossover(parent_a, parent_b, students, catalog, crossover_config):
    """Picks a crossover method based on configured weights"""
    if random.random() > crossover_config.probability:
        return copy_chromosome(parent_a), copy_chromosome(parent_b)

    roll = random.random()

    if roll < 0.35:
        return crossover_single_point(parent_a, parent_b, students, catalog)
    elif roll < 0.7:
        return crossover_uniform(parent_a, parent_b, students, catalog)
    else:
        return crossover_course_based(parent_a, parent_b, students, catalog)


# ============================================================
# MUTATION 1: CHANGE A SECTION
# ============================================================

def mutate_section_change(chromosome, students, catalog, rate):
    """Change a random course to a different section"""
    for sid, assignments in chromosome.schedule.items():
        if random.random() > rate:
            continue

        student = students[sid]
        idx = random.randint(0, len(assignments) - 1)
        others = assignments[:idx] + assignments[idx + 1:]
        valid = get_valid_sections(catalog, student, assignments[idx].course_id, others)

        # Remove current section so we actually change something
        valid = [v for v in valid if v != assignments[idx].section]

        if valid:
            assignments[idx].section = random.choice(valid)

    return chromosome


# ============================================================
# MUTATION 2: SWAP TWO COURSES
# ============================================================

def mutate_course_swap(chromosome, students, catalog, rate):
    """Swap sections between two courses for a student"""
    for sid, assignments in chromosome.schedule.items():
        if random.random() > rate:
            continue
        if len(assignments) < 2:
            continue

        i, j = random.sample(range(len(assignments)), 2)
        assignments[i].section, assignments[j].section = assignments[j].section, assignments[i].section

    return repair(chromosome, students, catalog)


# ============================================================
# MUTATION 3: TIME SHIFT - move to a different time
# ============================================================

def mutate_time_shift(chromosome, students, catalog, rate):
    """Move a course to a section that meets at a different time"""
    for sid, assignments in chromosome.schedule.items():
        if random.random() > rate:
            continue

        student = students[sid]
        idx = random.randint(0, len(assignments) - 1)
        course_id = assignments[idx].course_id

        current_section = catalog[course_id].sections[assignments[idx].section - 1]
        current_time = current_section.schedule[0].time

        others = assignments[:idx] + assignments[idx + 1:]
        valid = get_valid_sections(catalog, student, course_id, others)

        different = [v for v in valid
                     if catalog[course_id].sections[v - 1].schedule[0].time != current_time]

        if different:
            assignments[idx].section = random.choice(different)

    return chromosome


# ============================================================
# MUTATION 4: FRIEND ALIGNMENT - match with a friend
# ============================================================

def mutate_friend_align(chromosome, students, catalog, rate):
    """Try to align a course section with a friend"""
    # Build friend pairs
    friend_pairs = []
    seen = set()
    for sid, student in students.items():
        for fid in student.friends:
            pair = tuple(sorted([sid, fid]))
            if pair not in seen:
                friend_pairs.append(pair)
                seen.add(pair)

    for (sid_a, sid_b) in friend_pairs:
        if random.random() > rate:
            continue
        if sid_a not in chromosome.schedule or sid_b not in chromosome.schedule:
            continue

        assignments_a = chromosome.schedule[sid_a]
        assignments_b = chromosome.schedule[sid_b]

        courses_a = {a.course_id: i for i, a in enumerate(assignments_a)}
        courses_b = {a.course_id: i for i, a in enumerate(assignments_b)}

        shared = set(courses_a.keys()) & set(courses_b.keys())
        if not shared:
            continue

        course_id = random.choice(list(shared))
        idx_a = courses_a[course_id]
        idx_b = courses_b[course_id]

        # Try to align B to A's section
        student_b = students[sid_b]
        others_b = assignments_b[:idx_b] + assignments_b[idx_b + 1:]
        valid_b = get_valid_sections(catalog, student_b, course_id, others_b)

        target = assignments_a[idx_a].section
        if target in valid_b:
            assignments_b[idx_b].section = target

    return chromosome


def mutate(chromosome, students, catalog, mutation_config, adaptive=False):
    """Apply all mutation operators. If adaptive, increase rates."""
    multiplier = mutation_config.rate_multiplier if adaptive else 1.0

    r_section = mutation_config.rate_section_change * multiplier
    r_swap = mutation_config.rate_course_swap * multiplier
    r_shift = mutation_config.rate_time_shift * multiplier
    r_friend = mutation_config.rate_friend_align * multiplier

    chromosome = mutate_section_change(chromosome, students, catalog, r_section)
    chromosome = mutate_course_swap(chromosome, students, catalog, r_swap)
    chromosome = mutate_time_shift(chromosome, students, catalog, r_shift)
    chromosome = mutate_friend_align(chromosome, students, catalog, r_friend)

    return chromosome