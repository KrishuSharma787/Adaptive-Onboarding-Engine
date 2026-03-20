"""
AI-Adaptive Onboarding Engine - FastAPI Backend
Main application with streaming analysis via Server-Sent Events.
"""

import json
import os
import asyncio
from contextlib import asynccontextmanager
from typing import Optional, AsyncGenerator

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from app.models.schemas import (
    ParsedResume, ParsedJobDescription, SkillGapAnalysis,
    LearningPathway, DiagnosticAssessment, DiagnosticResult,
    FullAnalysisResponse, AnalyzeRequest, DiagnosticSubmission,
    Course,
)
from app.services.parser import parse_resume, parse_job_description
from app.services.gap_analyzer import GapAnalyzer
from app.services.rag_engine import RAGEngine
from app.services.pathfinder import AdaptivePathfinder
from app.services.diagnostic import DiagnosticGenerator
from app.services.catalog_builder import build_catalog_from_csv
from app.utils.pdf_utils import extract_text_from_pdf


# ============================================================
# Global service instances
# ============================================================
gap_analyzer = GapAnalyzer()
rag_engine = RAGEngine()
pathfinder = None
diagnostic_gen = DiagnosticGenerator()

diagnostic_sessions = {}


# ============================================================
# Application Lifecycle
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    global pathfinder

    catalog_path = os.path.join(os.path.dirname(__file__), "data", "course_catalog.json")
    csv_path = os.getenv("RESUME_CSV_PATH", "data/Resume.csv")

    if os.path.exists(catalog_path):
        print(f"Loading existing course catalog from {catalog_path}")
        with open(catalog_path, "r") as f:
            catalog_data = json.load(f)
        courses = [Course(**c) for c in catalog_data]
    elif os.path.exists(csv_path):
        print(f"Building course catalog from {csv_path}")
        os.makedirs(os.path.dirname(catalog_path), exist_ok=True)
        courses = build_catalog_from_csv(csv_path, catalog_path)
    else:
        print("WARNING: No resume CSV found. Using minimal fallback catalog.")
        courses = _get_fallback_catalog()
        os.makedirs(os.path.dirname(catalog_path), exist_ok=True)
        with open(catalog_path, "w") as f:
            json.dump([c.model_dump() for c in courses], f, indent=2)

    rag_engine.initialize(courses)
    pathfinder = AdaptivePathfinder(rag_engine)

    print(f"Engine ready. {len(courses)} courses loaded.")
    yield
    print("Shutting down...")


app = FastAPI(
    title="AI-Adaptive Onboarding Engine",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Helper: SSE event formatter
# ============================================================

def sse_event(event: str, data: dict) -> str:
    """Format a Server-Sent Event."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


# ============================================================
# Streaming Analysis Endpoint
# ============================================================

@app.post("/api/analyze/stream")
async def analyze_stream(request: Request):
    """
    Streaming analysis via Server-Sent Events.
    Each step sends a status update + partial results as they complete.
    """
    body = await request.json()
    resume_text = body.get("resume_text", "")
    jd_text = body.get("job_description_text", "")

    if not resume_text.strip() or not jd_text.strip():
        raise HTTPException(400, "Both resume_text and job_description_text are required")

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            # Step 1: Parse Resume
            yield sse_event("status", {
                "step": 1, "total_steps": 5,
                "message": "Parsing resume with constrained LLM generation...",
                "detail": "Extracting skills with evidence-based depth scoring"
            })

            parsed_resume = await asyncio.to_thread(parse_resume, resume_text)

            yield sse_event("resume_parsed", {
                "candidate_name": parsed_resume.candidate_name,
                "skills_count": len(parsed_resume.extracted_skills),
                "domain": parsed_resume.domain,
                "top_skills": [
                    {"name": s.skill_name, "level": s.proficiency.value}
                    for s in parsed_resume.extracted_skills[:8]
                ]
            })

            # Step 2: Parse JD
            yield sse_event("status", {
                "step": 2, "total_steps": 5,
                "message": "Analyzing job description requirements...",
                "detail": "Mapping required skills to O*NET taxonomy"
            })

            parsed_jd = await asyncio.to_thread(parse_job_description, jd_text)

            yield sse_event("jd_parsed", {
                "job_title": parsed_jd.job_title,
                "required_skills_count": len(parsed_jd.required_skills),
                "essential_count": sum(1 for s in parsed_jd.required_skills if s.importance == "essential"),
            })

            # Step 3: Gap Analysis
            yield sse_event("status", {
                "step": 3, "total_steps": 5,
                "message": "Computing skill gaps with O*NET standardized scoring...",
                "detail": "Calibrating proficiency using data from 2,484 resumes"
            })

            gap_analysis = await asyncio.to_thread(gap_analyzer.analyze, parsed_resume, parsed_jd)

            yield sse_event("gap_computed", {
                "readiness_score": gap_analysis.overall_readiness_score,
                "gaps_count": len(gap_analysis.skill_gaps),
                "matched_count": len(gap_analysis.matched_skills),
                "top_gaps": [
                    {"skill": g.skill_name, "gap": g.gap_score}
                    for g in gap_analysis.skill_gaps[:5]
                ],
                "peer_domain": gap_analysis.peer_comparison.get("domain") if gap_analysis.peer_comparison else None,
                "peer_percentile": gap_analysis.peer_comparison.get("percentile") if gap_analysis.peer_comparison else None,
            })

            # Step 4: Generate Pathway
            yield sse_event("status", {
                "step": 4, "total_steps": 5,
                "message": "Generating adaptive learning pathway...",
                "detail": "Building DAG, retrieving courses via RAG, topological sorting"
            })

            pathway = await asyncio.to_thread(pathfinder.generate_pathway, gap_analysis)

            yield sse_event("pathway_ready", {
                "total_courses": pathway.total_courses,
                "total_hours": pathway.total_hours,
                "phases_count": len(pathway.phases),
            })

            # Step 5: Diagnostic Assessment
            yield sse_event("status", {
                "step": 5, "total_steps": 5,
                "message": "Generating diagnostic assessment...",
                "detail": "Creating targeted questions for top skill gaps"
            })

            diagnostic = None
            if gap_analysis.skill_gaps:
                diagnostic = await asyncio.to_thread(
                    diagnostic_gen.generate_assessment, gap_analysis.skill_gaps
                )
                diagnostic_sessions["latest"] = {
                    "assessment": diagnostic,
                    "gaps": gap_analysis.skill_gaps,
                }

            # Final: Send complete results
            yield sse_event("complete", {
                "parsed_resume": parsed_resume.model_dump(),
                "parsed_jd": parsed_jd.model_dump(),
                "gap_analysis": gap_analysis.model_dump(),
                "learning_pathway": pathway.model_dump(),
                "diagnostic_assessment": diagnostic.model_dump() if diagnostic else None,
            })

        except Exception as e:
            yield sse_event("error", {"message": str(e)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


# ============================================================
# Non-streaming endpoints (kept for file uploads)
# ============================================================

@app.get("/")
async def root():
    return {"message": "AI-Adaptive Onboarding Engine API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "rag_initialized": rag_engine._initialized,
        "courses_loaded": len(rag_engine.courses) if rag_engine._initialized else 0,
    }


@app.post("/api/analyze", response_model=FullAnalysisResponse)
async def analyze_full(
    resume: UploadFile = File(...),
    job_description: UploadFile = File(...),
):
    try:
        resume_text = await _extract_upload_text(resume)
        jd_text = await _extract_upload_text(job_description)

        if not resume_text.strip():
            raise HTTPException(400, "Could not extract text from resume")
        if not jd_text.strip():
            raise HTTPException(400, "Could not extract text from job description")

        parsed_resume = parse_resume(resume_text)
        parsed_jd = parse_job_description(jd_text)
        gap_analysis = gap_analyzer.analyze(parsed_resume, parsed_jd)
        pathway = pathfinder.generate_pathway(gap_analysis)

        diagnostic = None
        if gap_analysis.skill_gaps:
            diagnostic = diagnostic_gen.generate_assessment(gap_analysis.skill_gaps)
            diagnostic_sessions["latest"] = {
                "assessment": diagnostic,
                "gaps": gap_analysis.skill_gaps,
            }

        return FullAnalysisResponse(
            parsed_resume=parsed_resume,
            parsed_jd=parsed_jd,
            gap_analysis=gap_analysis,
            learning_pathway=pathway,
            diagnostic_assessment=diagnostic,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Analysis failed: {str(e)}")


@app.post("/api/analyze/text", response_model=FullAnalysisResponse)
async def analyze_text(request: AnalyzeRequest):
    try:
        parsed_resume = parse_resume(request.resume_text)
        parsed_jd = parse_job_description(request.job_description_text)
        gap_analysis = gap_analyzer.analyze(parsed_resume, parsed_jd)
        pathway = pathfinder.generate_pathway(gap_analysis)

        diagnostic = None
        if gap_analysis.skill_gaps:
            diagnostic = diagnostic_gen.generate_assessment(gap_analysis.skill_gaps)
            diagnostic_sessions["latest"] = {
                "assessment": diagnostic,
                "gaps": gap_analysis.skill_gaps,
            }

        return FullAnalysisResponse(
            parsed_resume=parsed_resume,
            parsed_jd=parsed_jd,
            gap_analysis=gap_analysis,
            learning_pathway=pathway,
            diagnostic_assessment=diagnostic,
        )
    except Exception as e:
        raise HTTPException(500, f"Analysis failed: {str(e)}")


@app.post("/api/diagnostic/submit")
async def submit_diagnostic(answers: list[DiagnosticSubmission]):
    session = diagnostic_sessions.get("latest")
    if not session:
        raise HTTPException(400, "No active diagnostic session")

    assessment = session["assessment"]
    gaps = session["gaps"]

    skill_answers = {}
    for answer in answers:
        for q in assessment.questions:
            if q.question_id == answer.question_id:
                skill = q.skill_being_tested
                if skill not in skill_answers:
                    skill_answers[skill] = {"questions": [], "answers": []}
                skill_answers[skill]["questions"].append(q)
                skill_answers[skill]["answers"].append(answer.selected_answer_index)
                break

    results = []
    for skill_name, data in skill_answers.items():
        gap = next((g for g in gaps if g.skill_name == skill_name), None)
        if gap:
            result = diagnostic_gen.evaluate_responses(
                data["questions"], data["answers"], gap
            )
            results.append(result.model_dump())

    return {"results": results}


@app.get("/api/catalog")
async def get_catalog():
    if not rag_engine._initialized:
        raise HTTPException(503, "Catalog not loaded")
    return {
        "total_courses": len(rag_engine.courses),
        "courses": [c.model_dump() for c in rag_engine.courses[:50]],
    }


@app.get("/api/catalog/search")
async def search_catalog(q: str, top_k: int = 5):
    if not rag_engine._initialized:
        raise HTTPException(503, "Catalog not loaded")
    results = rag_engine.retrieve(q, top_k=top_k)
    return {"query": q, "results": results}


# ============================================================
# Helpers
# ============================================================

async def _extract_upload_text(upload: UploadFile) -> str:
    content = await upload.read()
    if upload.filename and upload.filename.lower().endswith(".pdf"):
        return extract_text_from_pdf(content)
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("latin-1")


def _get_fallback_catalog() -> list[Course]:
    return [
        Course(course_id="FALL-001", title="Business Communication Essentials",
               description="Build effective written and verbal communication skills.",
               skills_covered=["communication", "writing", "speaking"],
               prerequisites=[], difficulty="beginner", duration_hours=4.0, domain="General"),
        Course(course_id="FALL-002", title="Microsoft Office Proficiency",
               description="Master Excel, Word, PowerPoint for business productivity.",
               skills_covered=["excel", "microsoft office", "powerpoint", "word"],
               prerequisites=[], difficulty="beginner", duration_hours=6.0, domain="General"),
        Course(course_id="FALL-003", title="Project Management Fundamentals",
               description="Learn planning, execution, and closing of projects.",
               skills_covered=["project management", "time management", "planning"],
               prerequisites=[], difficulty="intermediate", duration_hours=8.0, domain="Management"),
    ]
