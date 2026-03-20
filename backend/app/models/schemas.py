"""
Pydantic schemas for constrained LLM generation.
These schemas enforce deterministic, structured output from the LLM,
eliminating conversational wrappers and hallucinated fields.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


# ============================================================
# Skill Depth Scoring - Evidence-based proficiency levels
# ============================================================

class ProficiencyLevel(str, Enum):
    """
    1-5 depth scale based on resume evidence type.
    Maps to O*NET standardized scores (0-100).
    """
    MENTIONED = "mentioned"          # Level 1: Listed in skills section only
    USED = "used"                    # Level 2: Mentioned in one job description
    APPLIED = "applied"              # Level 3: Appears across multiple roles
    DEMONSTRATED = "demonstrated"    # Level 4: Projects with measurable outcomes
    LED = "led"                      # Level 5: Taught/led/architected

PROFICIENCY_TO_SCORE = {
    ProficiencyLevel.MENTIONED: 15,
    ProficiencyLevel.USED: 35,
    ProficiencyLevel.APPLIED: 55,
    ProficiencyLevel.DEMONSTRATED: 75,
    ProficiencyLevel.LED: 95,
}


# ============================================================
# Resume Parsing Schemas (Constrained Generation)
# ============================================================

class ExtractedSkill(BaseModel):
    """A single skill extracted from a resume with depth evidence."""
    skill_name: str = Field(
        ..., description="The canonical name of the identified skill (e.g., 'Python', 'Financial Reporting')"
    )
    proficiency: ProficiencyLevel = Field(
        ..., description="The expertise level inferred from contextual evidence in the resume"
    )
    evidence: str = Field(
        ..., description="The exact text snippet or summary from the resume proving this skill and level"
    )
    years_experience: Optional[float] = Field(
        None, description="Estimated years of experience with this skill, if inferable"
    )


class ParsedResume(BaseModel):
    """Structured output from resume parsing via constrained generation."""
    candidate_name: str = Field(..., description="Full name of the candidate")
    current_role: Optional[str] = Field(None, description="Most recent job title")
    total_experience_years: Optional[float] = Field(None, description="Total years of professional experience")
    education_level: Optional[str] = Field(None, description="Highest education level (e.g., 'Bachelor', 'Master', 'PhD')")
    domain: Optional[str] = Field(None, description="Primary professional domain (e.g., 'Software Engineering', 'Finance')")
    extracted_skills: List[ExtractedSkill] = Field(
        ..., description="All skills identified with proficiency levels and evidence"
    )


# ============================================================
# Job Description Parsing Schemas
# ============================================================

class RequiredSkill(BaseModel):
    """A single skill required by a job description."""
    skill_name: str = Field(
        ..., description="The canonical name of the required skill"
    )
    importance: str = Field(
        ..., description="How critical this skill is: 'essential', 'preferred', or 'nice_to_have'"
    )
    required_level: ProficiencyLevel = Field(
        ..., description="The minimum proficiency level expected for this role"
    )


class ParsedJobDescription(BaseModel):
    """Structured output from JD parsing via constrained generation."""
    job_title: str = Field(..., description="The title of the role")
    department: Optional[str] = Field(None, description="Department or team")
    domain: Optional[str] = Field(None, description="Professional domain of this role")
    required_skills: List[RequiredSkill] = Field(
        ..., description="All skills required by the job description with importance levels"
    )
    responsibilities: List[str] = Field(
        default_factory=list, description="Key responsibilities of the role"
    )


# ============================================================
# Skill Gap Analysis Output
# ============================================================

class SkillGap(BaseModel):
    """A single identified gap between candidate and role requirements."""
    skill_name: str
    onet_node: Optional[str] = Field(None, description="Mapped O*NET taxonomy node")
    candidate_score: float = Field(..., description="Candidate's standardized score (0-100)")
    target_score: float = Field(..., description="Role's required standardized score (0-100)")
    gap_score: float = Field(..., description="Weighted gap penalty (target - candidate) * weight")
    importance_weight: float = Field(..., description="Weight based on skill importance (1.0, 0.7, 0.4)")
    reasoning: str = Field(..., description="Explanation of why this gap exists")


class SkillGapAnalysis(BaseModel):
    """Complete gap analysis between a candidate and a role."""
    candidate_name: str
    job_title: str
    overall_readiness_score: float = Field(..., description="0-100, how ready the candidate is")
    total_gap_penalty: float = Field(..., description="Sum of all weighted gap scores")
    skill_gaps: List[SkillGap] = Field(..., description="Ordered list of skill gaps (largest first)")
    matched_skills: List[str] = Field(default_factory=list, description="Skills where candidate meets/exceeds requirements")
    estimated_training_hours: float = Field(0, description="Estimated total hours to close all gaps")
    generic_training_hours: float = Field(0, description="Hours a generic onboarding would take")
    time_saved_percent: float = Field(0, description="Percentage reduction vs generic onboarding")
    peer_comparison: Optional[dict] = Field(None, description="Comparison against peer cohort from trained data")


# ============================================================
# Course Catalog & Learning Pathway
# ============================================================

class Course(BaseModel):
    """A single course in the catalog."""
    course_id: str
    title: str
    description: str
    skills_covered: List[str]
    prerequisites: List[str] = Field(default_factory=list)
    difficulty: str = Field(..., description="'beginner', 'intermediate', or 'advanced'")
    duration_hours: float
    domain: str


class PathwayNode(BaseModel):
    """A single node in the learning pathway graph."""
    course_id: str
    course_title: str
    target_skill: str
    phase: int = Field(..., description="Learning phase (1=Foundation, 2=Core, 3=Advanced)")
    duration_hours: float
    prerequisites: List[str] = Field(default_factory=list)
    reasoning: str = Field(..., description="Why this course was recommended")
    confidence: float = Field(..., description="System confidence in this recommendation (0-1)")
    source_catalog_id: str = Field(..., description="Citation ID from course catalog for audit trail")


class LearningPathway(BaseModel):
    """The complete generated learning pathway."""
    candidate_name: str
    job_title: str
    total_courses: int
    total_hours: float
    phases: List[dict] = Field(..., description="Phases with their courses grouped")
    pathway_nodes: List[PathwayNode]
    reasoning_trace: List[str] = Field(..., description="Step-by-step reasoning log")


# ============================================================
# Diagnostic Assessment
# ============================================================

class DiagnosticQuestion(BaseModel):
    """A single diagnostic question to verify skill depth."""
    question_id: str
    skill_being_tested: str
    question_text: str
    options: List[str] = Field(..., min_length=4, max_length=4)
    correct_answer_index: int = Field(..., ge=0, le=3)
    difficulty: str
    explanation: str = Field(..., description="Why the correct answer is correct")


class DiagnosticAssessment(BaseModel):
    """A generated diagnostic quiz for skill verification."""
    target_skills: List[str]
    questions: List[DiagnosticQuestion]
    estimated_duration_minutes: int


class DiagnosticResult(BaseModel):
    """Result after a candidate completes the diagnostic."""
    skill_name: str
    questions_asked: int
    correct_answers: int
    estimated_mastery_probability: float = Field(..., description="BKT-estimated mastery (0-1)")
    adjusted_proficiency: ProficiencyLevel
    pathway_adjustment: str = Field(..., description="How the pathway should change based on this result")


# ============================================================
# API Request/Response Models
# ============================================================

class AnalyzeRequest(BaseModel):
    """API request to analyze a resume against a job description."""
    resume_text: str
    job_description_text: str


class DiagnosticSubmission(BaseModel):
    """API request to submit diagnostic quiz answers."""
    question_id: str
    selected_answer_index: int


class FullAnalysisResponse(BaseModel):
    """Complete API response with all analysis results."""
    parsed_resume: ParsedResume
    parsed_jd: ParsedJobDescription
    gap_analysis: SkillGapAnalysis
    learning_pathway: LearningPathway
    diagnostic_assessment: Optional[DiagnosticAssessment] = None
