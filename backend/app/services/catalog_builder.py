"""
Course Catalog Builder
Extracts skill taxonomy from the resume dataset and generates
a structured course catalog mapped to skill gaps.
"""

import json
import csv
import re
import hashlib
from typing import List, Dict, Set
from collections import Counter, defaultdict
from app.models.schemas import Course


# Difficulty tiers mapped to proficiency progression
DIFFICULTY_MAP = {
    "beginner": {"target_proficiency": "used", "hours_range": (2, 6)},
    "intermediate": {"target_proficiency": "applied", "hours_range": (4, 10)},
    "advanced": {"target_proficiency": "demonstrated", "hours_range": (8, 16)},
}


def extract_skills_from_dataset(csv_path: str) -> Dict[str, Dict]:
    """
    Extract skill frequencies and domain mappings from the Kaggle resume dataset.

    Returns:
        Dict mapping skill_name -> { "count": int, "domains": Set[str] }
    """
    skill_data = defaultdict(lambda: {"count": 0, "domains": set()})

    with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for row in reader:
            category = row.get("Category", "UNKNOWN")
            resume_text = row.get("Resume_str", "")

            # Extract skills section if present
            skills = _extract_skills_section(resume_text)
            for skill in skills:
                clean = skill.strip().lower()
                if len(clean) > 2 and len(clean) < 60:
                    skill_data[clean]["count"] += 1
                    skill_data[clean]["domains"].add(category)

    return dict(skill_data)


def _extract_skills_section(text: str) -> List[str]:
    """Extract skills from a resume text using pattern matching."""
    skills = []

    # Pattern 1: Look for explicit "Skills" section
    skills_match = re.search(
        r'(?:Skills|Technical Skills|Core Skills|Key Skills|Competencies)[:\s]*\n?(.*?)(?:\n\n|\nExperience|\nEducation|\nWork History|\nCertifications|$)',
        text, re.IGNORECASE | re.DOTALL
    )
    if skills_match:
        section = skills_match.group(1)
        # Split by common delimiters
        parts = re.split(r'[,;•\n|/]+', section)
        skills.extend([p.strip() for p in parts if p.strip()])

    # Pattern 2: Look for skills listed with bullet points
    bullet_skills = re.findall(r'[â—\-\*]\s*(.+?)(?:\n|$)', text)
    skills.extend([s.strip() for s in bullet_skills if len(s.strip()) > 2])

    return skills


def generate_course_catalog(
    skill_data: Dict[str, Dict],
    min_frequency: int = 3,
) -> List[Course]:
    """
    Generate a structured course catalog from extracted skill data.

    For each high-frequency skill, creates beginner/intermediate/advanced courses.
    """
    courses = []
    course_counter = 0

    # Filter to skills that appear frequently enough
    frequent_skills = {
        name: data for name, data in skill_data.items()
        if data["count"] >= min_frequency
    }

    # Sort by frequency (most common skills first)
    sorted_skills = sorted(
        frequent_skills.items(),
        key=lambda x: x[1]["count"],
        reverse=True
    )

    # Take top 200 skills to keep catalog manageable
    for skill_name, data in sorted_skills[:200]:
        domains = list(data["domains"])
        primary_domain = domains[0] if domains else "General"

        # Determine prerequisites based on common sense ordering
        prerequisites_map = _get_prerequisite_chain(skill_name)

        for difficulty, config in DIFFICULTY_MAP.items():
            course_counter += 1
            course_id = f"CRS-{course_counter:04d}"

            hours = (config["hours_range"][0] + config["hours_range"][1]) / 2

            # Build prerequisite list
            prereqs = []
            if difficulty == "intermediate":
                prereqs = [f"Fundamentals of {skill_name.title()}"]
            elif difficulty == "advanced":
                prereqs = [f"{skill_name.title()} in Practice"]

            title = _generate_course_title(skill_name, difficulty)
            description = _generate_course_description(skill_name, difficulty)

            courses.append(Course(
                course_id=course_id,
                title=title,
                description=description,
                skills_covered=[skill_name],
                prerequisites=prereqs,
                difficulty=difficulty,
                duration_hours=hours,
                domain=primary_domain,
            ))

    return courses


def _generate_course_title(skill_name: str, difficulty: str) -> str:
    """Generate a realistic course title."""
    templates = {
        "beginner": [
            f"Fundamentals of {skill_name.title()}",
            f"Introduction to {skill_name.title()}",
            f"{skill_name.title()} Essentials",
        ],
        "intermediate": [
            f"{skill_name.title()} in Practice",
            f"Applied {skill_name.title()}",
            f"Working with {skill_name.title()}",
        ],
        "advanced": [
            f"Advanced {skill_name.title()}",
            f"Mastering {skill_name.title()}",
            f"{skill_name.title()} Architecture & Leadership",
        ],
    }
    # Deterministic selection based on skill name hash
    idx = int(hashlib.md5(skill_name.encode()).hexdigest(), 16) % 3
    return templates[difficulty][idx]


def _generate_course_description(skill_name: str, difficulty: str) -> str:
    """Generate a realistic course description."""
    descriptions = {
        "beginner": (
            f"Build a solid foundation in {skill_name}. This course covers core concepts, "
            f"terminology, and basic applications. Ideal for professionals new to {skill_name} "
            f"or those looking to formalize informal knowledge."
        ),
        "intermediate": (
            f"Deepen your {skill_name} expertise through hands-on projects and real-world scenarios. "
            f"Apply {skill_name} concepts across multiple contexts, develop troubleshooting skills, "
            f"and build a portfolio of practical experience."
        ),
        "advanced": (
            f"Master {skill_name} at an expert level. Design systems, lead teams, and make "
            f"strategic decisions using advanced {skill_name} principles. Includes case studies, "
            f"architecture patterns, and leadership applications."
        ),
    }
    return descriptions[difficulty]


def _get_prerequisite_chain(skill_name: str) -> List[str]:
    """Return common prerequisite skills for a given skill."""
    # Simplified prerequisite mapping
    prereq_map = {
        "machine learning": ["python", "statistics", "data analysis"],
        "deep learning": ["machine learning", "python", "linear algebra"],
        "kubernetes": ["docker", "linux", "networking"],
        "docker": ["linux", "command line"],
        "react": ["javascript", "html", "css"],
        "angular": ["javascript", "typescript", "html"],
        "django": ["python", "databases", "html"],
        "flask": ["python", "databases"],
        "data analysis": ["excel", "statistics"],
        "financial analysis": ["accounting", "excel", "financial reporting"],
        "system design": ["software development", "databases", "networking"],
        "cloud computing": ["networking", "linux", "virtualization"],
        "cybersecurity": ["networking", "linux", "programming"],
    }
    return prereq_map.get(skill_name.lower(), [])


def build_catalog_from_csv(csv_path: str, output_path: str) -> List[Course]:
    """
    End-to-end: extract skills from dataset, generate catalog, save to JSON.
    """
    print(f"Extracting skills from {csv_path}...")
    skill_data = extract_skills_from_dataset(csv_path)
    print(f"Found {len(skill_data)} unique skills")

    print("Generating course catalog...")
    courses = generate_course_catalog(skill_data)
    print(f"Generated {len(courses)} courses")

    # Save to JSON
    catalog_json = [course.model_dump() for course in courses]
    with open(output_path, "w") as f:
        json.dump(catalog_json, f, indent=2)
    print(f"Saved catalog to {output_path}")

    return courses
