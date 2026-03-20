"""
LLM-Powered Course Catalog Generator

Uses the LLM to generate realistic, helpful course titles, descriptions,
and learning objectives based on domain skill profiles mined from 2,484 resumes.

Run this script once to build the catalog:
    python -m app.services.generate_courses
"""

import json
import os
import time
import hashlib
from typing import List, Dict
from openai import OpenAI
from app.config import GEMINI_API_KEY, LLM_MODEL

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

# Connect to LLM (Gemini via OpenAI-compatible endpoint, or Groq)
BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")


def generate_courses_for_domain(
    client: OpenAI,
    domain: str,
    skills: List[Dict],
    prerequisites: List[Dict],
) -> List[Dict]:
    """Use LLM to generate realistic courses for a domain."""

    skill_list = ", ".join([f"{s['skill']} ({s['frequency']:.0%})" for s in skills[:12]])
    prereq_context = ""
    if prerequisites:
        prereq_lines = [f"- {p['prerequisite']} → {p['advanced_skill']}" for p in prerequisites[:10]]
        prereq_context = "\nKnown prerequisite relationships:\n" + "\n".join(prereq_lines)

    prompt = f"""You are a corporate training curriculum designer. Generate realistic training courses for the "{domain}" profession.

These are the most common skills found in {domain} resumes (with frequency):
{skill_list}
{prereq_context}

Generate 8-12 courses covering these skills across 3 difficulty levels:
- beginner (4h): Foundational knowledge for new hires
- intermediate (6-8h): Hands-on practice for working professionals  
- advanced (10-14h): Expert-level mastery and leadership

CRITICAL: Make these sound like REAL corporate training courses, not generic "Introduction to X" templates.
Include specific, practical learning outcomes.

Return ONLY valid JSON array (no markdown, no backticks):
[
  {{
    "title": "Realistic Course Title",
    "description": "2-3 sentence description with specific learning outcomes",
    "skills_covered": ["skill1", "skill2"],
    "prerequisites": ["prereq course title if any"],
    "difficulty": "beginner|intermediate|advanced",
    "duration_hours": 4.0
  }}
]"""

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            max_tokens=3000,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.choices[0].message.content.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        courses = json.loads(text)
        return courses
    except Exception as e:
        print(f"  Error generating courses for {domain}: {e}")
        return []


def build_llm_catalog():
    """Generate full course catalog using LLM for all domains."""

    # Load trained data
    with open(os.path.join(DATA_DIR, "domain_profiles.json")) as f:
        domain_profiles = json.load(f)
    with open(os.path.join(DATA_DIR, "skill_prerequisites.json")) as f:
        all_prereqs = json.load(f)

    client = OpenAI(api_key=GEMINI_API_KEY, base_url=BASE_URL)

    all_courses = []
    course_counter = 0

    for domain, skills in domain_profiles.items():
        print(f"\nGenerating courses for {domain}...")

        # Get prerequisites relevant to this domain's skills
        domain_skill_names = {s["skill"] for s in skills[:15]}
        domain_prereqs = [
            p for p in all_prereqs
            if p["advanced_skill"] in domain_skill_names or p["prerequisite"] in domain_skill_names
        ][:15]

        courses = generate_courses_for_domain(client, domain, skills, domain_prereqs)

        for course in courses:
            course_counter += 1
            course["course_id"] = f"CRS-{course_counter:04d}"
            course["domain"] = domain

            # Ensure required fields
            course.setdefault("skills_covered", [])
            course.setdefault("prerequisites", [])
            course.setdefault("difficulty", "intermediate")
            course.setdefault("duration_hours", 6.0)

            all_courses.append(course)

        print(f"  Generated {len(courses)} courses for {domain}")

        # Rate limit (Groq: 30 req/min, Gemini: 15 req/min)
        time.sleep(3)

    # Save
    output_path = os.path.join(DATA_DIR, "course_catalog.json")
    with open(output_path, "w") as f:
        json.dump(all_courses, f, indent=2)

    print(f"\n✅ Generated {len(all_courses)} LLM-powered courses across {len(domain_profiles)} domains")
    print(f"   Saved to {output_path}")

    return all_courses


if __name__ == "__main__":
    build_llm_catalog()
