---

# README for Q2_GA (Question 2)

````markdown
# Q2_GA - Course Scheduling Genetic Algorithm

## Overview

This is a Genetic Algorithm (GA) for optimizing university course schedules for 5 students. It assigns courses and sections to each student while satisfying hard constraints (credit requirements, no time conflicts, prerequisites, max courses per day, availability) and optimizing soft constraints (time preferences, gap minimization, friend satisfaction, workload balance, lunch breaks).

## What This Does

- Creates schedules for 5 students with different requirements
- Each student takes exactly 15 credits from core and elective courses
- Each course has 3 sections taught at different times by different professors
- Uses GA to evolve better schedules over multiple generations
- Tracks population diversity to avoid getting stuck in local optima
- Outputs best schedule found with detailed fitness breakdown

## Files Structure

Q2_GA/
├── main.py # Main GA runner
├── chromosome.py # Chromosome encoding and population init
├── fitness.py # Fitness function with 5 components
├── operators.py # Crossover and mutation operators
├── selection.py # Tournament and roulette selection
├── utils.py # Data loading and helper functions
├── config.yaml # GA parameters
├── course_catalog.json # Course data (15 courses)
├── student_requirements.json # Student profiles
├── plots/ # Generated plots (convergence, diversity)
├── results/ # Saved results
└── README.md

## Data Files

### course_catalog.json

Contains 15 courses (8 core + 7 electives):

**Core Courses:** DS, ALG, OS, DB, CN, SE, CA, TC
**Elective Courses:** ML, CV, NLP, GD, MAD, CYB, CC

Each course has:

- Name, type, credits (3), difficulty (1=Easy, 2=Medium, 3=Hard)
- Prerequisites list (must be completed before taking)
- 3 sections with different professors and schedules

Example structure:

```json
{
  "DS": {
    "name": "Data Structures",
    "type": "core",
    "credits": 3,
    "difficulty": 2,
    "prerequisites": [],
    "sections": [
      {
        "section_id": 1,
        "professor": "Dr. Smith",
        "schedule": [{"day": "Monday", "time": 9}, ...]
      }
    ]
  }
}




plots/
├── convergence.png    # Fitness over generations (all runs)
└── diversity.png      # Population diversity over time

## Requirements
pip install pyyaml matplotlib



# Run with default settings (60 population, 10 runs)
python main.py

# The GA will run 10 times and show best schedule
```
````
