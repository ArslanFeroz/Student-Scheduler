import random
from utils import get_valid_sections


# ============================================================
# DATA CLASSES - simple and clean
# ============================================================

class CourseAssignment:
    """Just a simple pair: which course and which section"""

    def __init__(self, course_id, section):
        self.course_id = course_id
        self.section = section  # 1, 2, or 3


class Chromosome:
    """
    A chromosome represents a complete schedule for all 5 students.

    Why this encoding? Because it's straightforward:
    - Each student gets a list of courses they're taking
    - Each course has a section number (1-3) which determines time/day
    - The actual time info is looked up from the catalog

    This is basically a direct encoding - no fancy binary stuff.
    It makes crossover and mutation easy to understand and implement.

    Example:
        chromosome.schedule["S1"] = [
            CourseAssignment("DS", 1),    # Data Structures, section 1 (MWF 9am)
            CourseAssignment("ALG", 2),   # Algorithms, section 2 (TTh 1pm)
            ...
        ]
    """

    def __init__(self):
        self.schedule = {}  # {student_id: [CourseAssignment, ...]}
        self.fitness = None  # will be filled by fitness function

    def set_student_schedule(self, student_id, assignments):
        self.schedule[student_id] = assignments

    def get_student_schedule(self, student_id):
        return self.schedule.get(student_id, [])


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def pick_electives(student, catalog, assigned_courses):
    """
    Chooses which electives a student will take.
    Tries to pick from their elective pool, skipping only if
    ALL sections are blocked or cause conflicts.
    """
    chosen = []
    needed = student.required_electives

    # First pass: try to pick valid electives
    for elective_id in student.elective_pool:
        if len(chosen) >= needed:
            break

        valid = get_valid_sections(catalog, student, elective_id, assigned_courses)
        if valid:
            chosen.append(elective_id)

    # Fallback: if we didn't get enough, just add whatever's left
    # Better to have a schedule than crash
    if len(chosen) < needed:
        for elective_id in student.elective_pool:
            if elective_id not in chosen:
                chosen.append(elective_id)
            if len(chosen) >= needed:
                break

    return chosen


def get_friend_pairs(students):
    """Extracts unique friend pairs so we don't double count"""
    seen = set()
    pairs = []
    for sid, student in students.items():
        for fid in student.friends:
            pair = tuple(sorted([sid, fid]))
            if pair not in seen:
                pairs.append(pair)
                seen.add(pair)
    return pairs


# ============================================================
# INITIALIZATION STRATEGY 1: RANDOM
# ============================================================

def create_random_chromosome(students, catalog):
    """
    Random but valid - picks sections randomly but respects
    prerequisites, blocked times, and conflicts.
    """
    chrom = Chromosome()

    for sid, student in students.items():
        assignments = []

        # Core courses first
        for course_id in student.required_core:
            valid = get_valid_sections(catalog, student, course_id, assignments)
            if not valid:
                valid = [1, 2, 3]  # fallback, shouldn't happen
            assignments.append(CourseAssignment(course_id, random.choice(valid)))

        # Pick electives that fit
        electives = pick_electives(student, catalog, assignments)

        # Assign electives
        for course_id in electives:
            valid = get_valid_sections(catalog, student, course_id, assignments)
            if not valid:
                valid = [1, 2, 3]
            assignments.append(CourseAssignment(course_id, random.choice(valid)))

        chrom.set_student_schedule(sid, assignments)

    return chrom


# ============================================================
# INITIALIZATION STRATEGY 2: GREEDY TIME
# ============================================================

def create_greedy_time_chromosome(students, catalog):
    """
    Tries to put classes in the student's preferred time slots.
    For each course, picks the section with most preferred times.
    """
    chrom = Chromosome()

    for sid, student in students.items():
        assignments = []
        preferred = set(student.time_preference.preferred_slots)

        def preference_score(course_id, sec_id):
            """Higher score = more preferred time slots"""
            section = catalog[course_id].sections[sec_id - 1]
            return sum(1 for slot in section.schedule if slot.time in preferred)

        # Core courses - pick best time match
        for course_id in student.required_core:
            valid = get_valid_sections(catalog, student, course_id, assignments)
            if not valid:
                valid = [1, 2, 3]
            best = max(valid, key=lambda s: preference_score(course_id, s))
            assignments.append(CourseAssignment(course_id, best))

        # Electives
        electives = pick_electives(student, catalog, assignments)
        for course_id in electives:
            valid = get_valid_sections(catalog, student, course_id, assignments)
            if not valid:
                valid = [1, 2, 3]
            best = max(valid, key=lambda s: preference_score(course_id, s))
            assignments.append(CourseAssignment(course_id, best))

        chrom.set_student_schedule(sid, assignments)

    return chrom


# ============================================================
# INITIALIZATION STRATEGY 3: GREEDY FRIEND
# ============================================================

def create_greedy_friend_chromosome(students, catalog, friend_pairs):
    """
    Tries to put friends in the same sections.
    Schedules friends together when possible.
    """
    chrom = Chromosome()
    scheduled = set()

    for (sid_a, sid_b) in friend_pairs:
        for sid in [sid_a, sid_b]:
            if sid in scheduled:
                continue

            student = students[sid]
            assignments = []
            friend_id = sid_b if sid == sid_a else sid_a

            def get_friend_section(course_id, valid):
                """If friend already has this course, try to match them"""
                if friend_id not in chrom.schedule:
                    return None
                for fa in chrom.schedule[friend_id]:
                    if fa.course_id == course_id and fa.section in valid:
                        return fa.section
                return None

            # Core courses - try to match friend
            for course_id in student.required_core:
                valid = get_valid_sections(catalog, student, course_id, assignments)
                if not valid:
                    valid = [1, 2, 3]
                friend_sec = get_friend_section(course_id, valid)
                chosen = friend_sec if friend_sec else random.choice(valid)
                assignments.append(CourseAssignment(course_id, chosen))

            # Electives
            electives = pick_electives(student, catalog, assignments)
            for course_id in electives:
                valid = get_valid_sections(catalog, student, course_id, assignments)
                if not valid:
                    valid = [1, 2, 3]
                friend_sec = get_friend_section(course_id, valid)
                chosen = friend_sec if friend_sec else random.choice(valid)
                assignments.append(CourseAssignment(course_id, chosen))

            chrom.set_student_schedule(sid, assignments)
            scheduled.add(sid)

    # Any stragglers? Schedule them randomly
    for sid, student in students.items():
        if sid not in scheduled:
            assignments = []
            for course_id in student.required_core:
                valid = get_valid_sections(catalog, student, course_id, assignments)
                if not valid:
                    valid = [1, 2, 3]
                assignments.append(CourseAssignment(course_id, random.choice(valid)))

            electives = pick_electives(student, catalog, assignments)
            for course_id in electives:
                valid = get_valid_sections(catalog, student, course_id, assignments)
                if not valid:
                    valid = [1, 2, 3]
                assignments.append(CourseAssignment(course_id, random.choice(valid)))

            chrom.set_student_schedule(sid, assignments)

    return chrom


def initialise_population(config, students, catalog):
    """
    Creates the starting population using all three strategies.

    Why 60? Found that 50 was too small (got stuck in local optima)
    and 80 was too slow. 60 seems like a sweet spot for this problem.
    """
    pop_size = config.population.size
    n_random = int(pop_size * 0.4)
    n_greedy_time = int(pop_size * 0.4)
    n_greedy_friend = pop_size - n_random - n_greedy_time

    friend_pairs = get_friend_pairs(students)
    population = []

    for _ in range(n_random):
        population.append(create_random_chromosome(students, catalog))

    for _ in range(n_greedy_time):
        population.append(create_greedy_time_chromosome(students, catalog))

    for _ in range(n_greedy_friend):
        population.append(create_greedy_friend_chromosome(students, catalog, friend_pairs))

    return population