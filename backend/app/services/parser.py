"""
Intelligent Parsing Service
Uses Groq (Llama 3.3 70B) via OpenAI-compatible endpoint with Instructor
for constrained generation. Includes post-processing validation to
remove any hallucinated skills not found in the original text.
"""

import re
import instructor
from openai import OpenAI
from app.config import GROQ_API_KEY, LLM_MODEL
from app.models.schemas import ParsedResume, ParsedJobDescription


def get_instructor_client():
    """Initialize Groq client via OpenAI-compatible endpoint wrapped with Instructor."""
    client = OpenAI(
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1"
    )
    return instructor.from_openai(client)


RESUME_SYSTEM_PROMPT = """You are an expert HR analyst and skill extraction engine. 
Your task is to parse a resume and extract ALL identifiable skills with evidence-based proficiency levels.

PROFICIENCY LEVEL RULES (you MUST follow these strictly):
- "mentioned": Skill appears only in a skills list with no supporting evidence in experience sections
- "used": Skill is referenced in exactly ONE job/role description
- "applied": Skill appears across MULTIPLE roles or projects, showing consistent usage
- "demonstrated": Skill is backed by measurable outcomes, metrics, or significant project work (e.g., "reduced costs by 40%", "built a system serving 10k users")
- "led": Candidate taught, architected, led teams, or made strategic decisions using this skill

CRITICAL RULES:
- Extract EVERY identifiable skill, both explicit (listed) and implicit (inferred from experience)
- For implicit skills, explain the inference in the evidence field
- "Led a team of 5 engineers" implies: team_management(led), leadership(demonstrated)
- Estimate years_experience ONLY when clearly inferable from dates
- Be thorough: technical skills, soft skills, tools, methodologies, domain knowledge
- Do NOT hallucinate skills not supported by the resume text
- CRITICAL: Only extract skills that are EXPLICITLY written in the resume text. If a word does not appear in the resume, do NOT infer it as a skill. For example, do NOT add "Recruitment" unless the resume literally mentions recruiting or recruitment."""


JD_SYSTEM_PROMPT = """You are an expert job description analyst.
Your task is to parse a job description and extract ALL required skills with their importance levels.

IMPORTANCE RULES:
- "essential": Skills explicitly marked as required, must-have, or core to the role
- "preferred": Skills marked as preferred, strongly desired, or significant advantage
- "nice_to_have": Skills mentioned as bonus, plus, or helpful but not critical

REQUIRED LEVEL RULES:
- "mentioned": Entry-level awareness sufficient
- "used": Basic working knowledge needed  
- "applied": Solid hands-on experience required
- "demonstrated": Deep expertise with proven track record needed
- "led": Expert/leadership level expected

Extract ALL skills including technical, soft skills, tools, certifications, and domain knowledge.
Also extract key responsibilities of the role."""


def _validate_skills(parsed: ParsedResume, original_text: str) -> ParsedResume:
    """
    Post-processing validation: remove any skill the LLM hallucinated.
    A skill is valid ONLY if its name (or a significant word from it)
    appears in the original resume text.
    """
    text_lower = original_text.lower()
    text_words = set(re.findall(r'[a-z]+', text_lower))

    # Known abbreviations that expand to phrases in resumes
    abbreviation_map = {
        "gaap": ["generally accepted accounting", "gaap"],
        "ifrs": ["international financial reporting", "ifrs"],
        "erp": ["enterprise resource planning", "sap", "oracle", "erp"],
        "crm": ["customer relationship", "salesforce", "crm"],
        "nlp": ["natural language processing", "nlp", "vader", "sentiment"],
        "ml": ["machine learning", "ml", "scikit"],
        "ci/cd": ["continuous integration", "continuous deployment", "jenkins", "github actions", "ci/cd"],
        "aws": ["amazon web services", "aws"],
        "gcp": ["google cloud", "gcp"],
        "sql": ["database", "mysql", "postgresql", "queries", "sql"],
        "html/css": ["html", "css"],
        "html/css/js": ["html", "css", "javascript", "js"],
    }

    validated = []
    for skill in parsed.extracted_skills:
        skill_lower = skill.skill_name.lower().strip()

        # Check 1: Exact substring match in resume text
        if skill_lower in text_lower:
            validated.append(skill)
            continue

        # Check 2: All significant words from skill name appear in resume
        skill_words = set(re.findall(r'[a-z]+', skill_lower))
        stop = {"and", "or", "the", "a", "an", "of", "in", "for", "to", "with", "on", "at", "by"}
        meaningful_words = skill_words - stop
        if meaningful_words and meaningful_words.issubset(text_words):
            validated.append(skill)
            continue

        # Check 3: Known abbreviation expands to something in text
        expansions = abbreviation_map.get(skill_lower, [])
        if any(exp in text_lower for exp in expansions):
            validated.append(skill)
            continue

        # Check 4: Skill evidence text appears in resume (LLM quoted the resume)
        if skill.evidence and len(skill.evidence) > 10:
            evidence_words = set(re.findall(r'[a-z]+', skill.evidence.lower()))
            evidence_meaningful = evidence_words - stop
            if len(evidence_meaningful) > 3:
                overlap = evidence_meaningful & text_words
                if len(overlap) / len(evidence_meaningful) > 0.6:
                    validated.append(skill)
                    continue

        # Skill not found in resume — hallucinated, drop it
        print(f"  [VALIDATION] Removed hallucinated skill: '{skill.skill_name}'")

    parsed.extracted_skills = validated
    return parsed


def parse_resume(resume_text: str) -> ParsedResume:
    """Parse a resume using constrained generation via Groq/Llama 3.3."""
    client = get_instructor_client()

    parsed = client.chat.completions.create(
        model=LLM_MODEL,
        max_tokens=4096,
        messages=[
            {"role": "system", "content": RESUME_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Parse the following resume and extract all skills with proficiency levels:\n\n{resume_text}"
            }
        ],
        response_model=ParsedResume,
    )

    return _validate_skills(parsed, resume_text)


def parse_job_description(jd_text: str) -> ParsedJobDescription:
    """Parse a job description using constrained generation via Groq/Llama 3.3."""
    client = get_instructor_client()

    parsed = client.chat.completions.create(
        model=LLM_MODEL,
        max_tokens=4096,
        messages=[
            {"role": "system", "content": JD_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Parse the following job description and extract all required skills:\n\n{jd_text}"
            }
        ],
        response_model=ParsedJobDescription,
    )

    return parsed
