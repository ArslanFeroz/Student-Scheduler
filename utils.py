import json
import yaml


# ============================================================
# CONFIG CLASSES - just simple data holders
# ============================================================

class PopulationConfig:
    def __init__(self):
        self.size = 60
        self.random_valid_rate = 0.4
        self.greedy_time_rate = 0.4
        self.greedy_friend_rate = 0.2
        self.elitism_enabled = True
        self.elitism_rate = 0.1


class SelectionConfig:
    def __init__(self):
        self.tournament_enabled = True
        self.tournament_rate = 0.7
        self.tournament_size = 5
        self.roulette_enabled = True
        self.roulette_rate = 0.3


class CrossoverConfig:
    def __init__(self):
        self.probability = 0.8
        self.single_point_weight = 0.35
        self.uniform_weight = 0.35
        self.course_based_weight = 0.3
        self.repair_max_attempts = 10


class MutationConfig:
    def __init__(self):
        self.rate_section_change = 0.12
        self.rate_course_swap = 0.10
        self.rate_time_shift = 0.08
        self.rate_friend_align = 0.15
        self.adaptive_enabled = True
        self.diversity_threshold = 0.30
        self.rate_multiplier = 1.5
        self.check_interval = 10


class FitnessConfig:
    def __init__(self):
        self.w_time_preference = 0.30
        self.w_gap_minimization = 0.25
        self.w_friend_satisfaction = 0.20
        self.w_workload_balance = 0.15
        self.w_lunch_break = 0.10
        self.penalty_time_conflict = -1000
        self.penalty_missing_credits = -800
        self.penalty_too_many_courses = -500
        self.penalty_blocked_time = -1000


class DiversityConfig:
    def __init__(self):
        self.metric = "unique_schedules"
        self.maintenance_enabled = True
        self.check_interval = 10
        self.low_threshold = 0.30
        self.injection_rate = 0.20
        self.plot_enabled = True


class TerminationConfig:
    def __init__(self):
        self.max_generations = 300
        self.patience = 40
        self.improvement_threshold = 0.001
        self.similarity_threshold = 0.85
        self.similarity_tolerance = 0.02


class LoggingConfig:
    def __init__(self):
        self.console_enabled = True
        self.console_frequency = 10


class VisualizationConfig:
    def __init__(self):
        self.convergence_plot_enabled = True
        self.convergence_plot_path = "plots/convergence.png"
        self.diversity_plot_enabled = True
        self.diversity_plot_path = "plots/diversity.png"


class ExperimentConfig:
    def __init__(self):
        self.random_seed = 42
        self.num_runs = 10


class GAConfig:
    def __init__(self):
        self.population = PopulationConfig()
        self.selection = SelectionConfig()
        self.crossover = CrossoverConfig()
        self.mutation = MutationConfig()
        self.fitness = FitnessConfig()
        self.diversity = DiversityConfig()
        self.termination = TerminationConfig()
        self.logging = LoggingConfig()
        self.visualization = VisualizationConfig()
        self.experiment = ExperimentConfig()


# ============================================================
# COURSE CATALOG CLASSES
# ============================================================

class TimeSlot:
    def __init__(self, day="", time=0):
        self.day = day
        self.time = time  # 8-17, representing hour


class Section:
    def __init__(self):
        self.section_id = 0
        self.professor = ""
        self.schedule = []  # list of TimeSlot
        self.capacity = 30
        self.enrolled = 0


class Course:
    def __init__(self):
        self.course_id = ""
        self.name = ""
        self.type = ""  # "core" or "elective"
        self.credits = 3
        self.difficulty = 2  # 1=Easy, 2=Medium, 3=Hard
        self.prerequisites = []
        self.sections = []


# ============================================================
# STUDENT CLASSES
# ============================================================

class TimePreference:
    def __init__(self):
        self.preferred_slots = []  # list of hours like [8,9,10]
        self.blocked_slots = []  # list of TimeSlot


class Student:
    def __init__(self):
        self.student_id = ""
        self.name = ""
        self.year = 0
        self.required_credits = 15
        self.required_core = []
        self.required_electives = 0
        self.elective_pool = []
        self.completed_courses = []
        self.time_preference = TimePreference()
        self.friends = []
        self.max_courses_per_day = 3
        self.avoid_early = False  # for S5


# ============================================================
# PARSER FUNCTIONS
# ============================================================

def parse_config():
    """Loads config from yaml or returns defaults if file missing"""
    cfg = GAConfig()

    try:
        with open("config.yaml", "r") as f:
            raw = yaml.safe_load(f)

        # Population
        cfg.population.size = raw["population"]["size"]
        cfg.population.random_valid_rate = raw["population"]["initialization_strategy"]["random_valid"]
        cfg.population.greedy_time_rate = raw["population"]["initialization_strategy"]["greedy_time"]
        cfg.population.elitism_rate = raw["population"]["elitism"]["rate"]

        # Selection
        cfg.selection.tournament_rate = raw["selection"]["tournament"]["rate"]
        cfg.selection.tournament_size = raw["selection"]["tournament"]["tournament_size"]

        # Crossover
        cfg.crossover.probability = raw["crossover"]["probability"]
        cfg.crossover.single_point_weight = raw["crossover"]["operators"]["single_point"]["weight"]
        cfg.crossover.uniform_weight = raw["crossover"]["operators"]["uniform"]["weight"]

        # Mutation
        cfg.mutation.rate_section_change = raw["mutation"]["base_rates"]["section_change"]
        cfg.mutation.rate_course_swap = raw["mutation"]["base_rates"]["course_swap"]
        cfg.mutation.rate_time_shift = raw["mutation"]["base_rates"]["time_shift"]
        cfg.mutation.rate_friend_align = raw["mutation"]["base_rates"]["friend_align"]

        # Fitness weights
        cfg.fitness.w_time_preference = raw["fitness"]["weights"]["time_preference"]
        cfg.fitness.w_gap_minimization = raw["fitness"]["weights"]["gap_minimization"]
        cfg.fitness.w_friend_satisfaction = raw["fitness"]["weights"]["friend_satisfaction"]
        cfg.fitness.w_workload_balance = raw["fitness"]["weights"]["workload_balance"]
        cfg.fitness.w_lunch_break = raw["fitness"]["weights"]["lunch_break"]

        # Termination
        cfg.termination.max_generations = raw["termination"]["max_generations"]
        cfg.termination.patience = raw["termination"]["convergence"]["patience"]
        cfg.termination.improvement_threshold = raw["termination"]["convergence"]["improvement_threshold"]

        # Experiment
        cfg.experiment.random_seed = raw["experiment"]["random_seed"]
        cfg.experiment.num_runs = raw["experiment"]["num_runs"]

    except FileNotFoundError:
        print("config.yaml not found, using defaults")

    return cfg


def parse_catalog():
    """Loads the course catalog from JSON"""
    catalog = {}

    with open("course_catalog.json", "r") as f:
        raw = json.load(f)["courses"]

    for course_id, data in raw.items():
        c = Course()
        c.course_id = course_id
        c.name = data["name"]
        c.type = data["type"]
        c.credits = data["credits"]
        c.difficulty = data["difficulty"]
        c.prerequisites = data["prerequisites"]

        for sec_data in data["sections"]:
            s = Section()
            s.section_id = sec_data["section_id"]
            s.professor = sec_data["professor"]
            s.capacity = sec_data["capacity"]

            for slot_data in sec_data["schedule"]:
                t = TimeSlot(slot_data["day"], slot_data["time"])
                s.schedule.append(t)

            c.sections.append(s)

        catalog[course_id] = c

    return catalog


def parse_students():
    """Loads student requirements from JSON"""
    students = {}

    with open("student_requirements.json", "r") as f:
        raw = json.load(f)["students"]

    for student_id, data in raw.items():
        s = Student()
        s.student_id = student_id
        s.name = data["name"]
        s.year = data["year"]
        s.required_credits = data["required_credits"]
        s.required_core = data["required_courses"]["core"]
        s.required_electives = data["required_courses"]["electives"]
        s.elective_pool = data["required_courses"]["elective_pool"]
        s.completed_courses = data["completed_courses"]
        s.friends = data["friends"]
        s.max_courses_per_day = data["max_courses_per_day"]

        # Time preferences
        s.time_preference.preferred_slots = data["time_preferences"]["preferred"]["time_slots"]

        for slot_data in data["time_preferences"]["blocked"]["slots"]:
            t = TimeSlot(slot_data["day"], slot_data["time"])
            s.time_preference.blocked_slots.append(t)

        # Special constraints (like S5 avoiding 8am)
        if "special_constraints" in data:
            if data["special_constraints"].get("avoid_early"):
                s.avoid_early = True

        students[student_id] = s

    return students


def get_valid_sections(catalog, student, course_id, assigned_courses):
    """
    Returns list of section IDs that are valid for this student
    given their schedule so far.

    Checks:
    - Prerequisites (completed OR being taken this semester)
    - Blocked times (student can't be in class then)
    - Time conflicts with already assigned courses
    """
    # Prerequisite check - need to have completed the prereq
    prereqs = catalog[course_id].prerequisites
    completed = set(student.completed_courses)
    # Also courses we're taking this semester count
    taking_now = {a.course_id for a in assigned_courses}
    all_available = completed | taking_now

    for prereq in prereqs:
        if prereq not in all_available:
            return []  # nope, can't take this yet

    # Blocked times
    blocked = {(slot.day, slot.time) for slot in student.time_preference.blocked_slots}

    valid = []
    for sec_id in [1, 2, 3]:
        section = catalog[course_id].sections[sec_id - 1]
        this_slots = {(slot.day, slot.time) for slot in section.schedule}

        # Check blocked times
        if this_slots & blocked:
            continue

        # Check for conflicts with assigned courses
        conflict = False
        for assigned in assigned_courses:
            assigned_section = catalog[assigned.course_id].sections[assigned.section - 1]
            assigned_slots = {(slot.day, slot.time) for slot in assigned_section.schedule}
            if this_slots & assigned_slots:
                conflict = True
                break

        if not conflict:
            valid.append(sec_id)

    return valid