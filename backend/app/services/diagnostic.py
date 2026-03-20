"""
Diagnostic Assessment Service
Generates targeted diagnostic quizzes using Groq (Llama 3.3 70B),
then uses Bayesian Knowledge Tracing (BKT) to estimate mastery
and adjust the learning pathway accordingly.
"""

import json
import uuid
import math
from typing import List, Dict, Optional
from openai import OpenAI
from app.config import GROQ_API_KEY, LLM_MODEL, MASTERY_THRESHOLD
from app.models.schemas import (
    DiagnosticAssessment, DiagnosticQuestion, DiagnosticResult,
    SkillGap, ProficiencyLevel, PROFICIENCY_TO_SCORE,
)


BKT_DEFAULTS = {
    "p_init": 0.3,
    "p_learn": 0.1,
    "p_guess": 0.2,
    "p_slip": 0.1,
}


class BayesianKnowledgeTracer:
    """
    Bayesian Knowledge Tracing for mastery estimation.
    
    Updates P(mastery) after each learner response using:
    P(L_n | correct) = P(L_n) * (1 - P(S)) / P(correct)
    P(L_n | incorrect) = P(L_n) * P(S) / P(incorrect)
    """

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or BKT_DEFAULTS.copy()

    def estimate_mastery(self, responses: List[bool]) -> float:
        p_know = self.params["p_init"]
        p_learn = self.params["p_learn"]
        p_guess = self.params["p_guess"]
        p_slip = self.params["p_slip"]

        for response in responses:
            p_correct = p_know * (1 - p_slip) + (1 - p_know) * p_guess

            if response:
                p_know_given_obs = (p_know * (1 - p_slip)) / p_correct
            else:
                p_incorrect = 1 - p_correct
                if p_incorrect > 0:
                    p_know_given_obs = (p_know * p_slip) / p_incorrect
                else:
                    p_know_given_obs = p_know

            p_know = p_know_given_obs + (1 - p_know_given_obs) * p_learn

        return min(max(p_know, 0.0), 1.0)

    def mastery_reached(self, responses: List[bool]) -> bool:
        return self.estimate_mastery(responses) >= MASTERY_THRESHOLD


class DiagnosticGenerator:
    """Generates targeted diagnostic quizzes using Groq/Llama 3.3."""

    def __init__(self):
        self.client = OpenAI(
            api_key=GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1"
        )
        self.bkt = BayesianKnowledgeTracer()

    def generate_assessment(
        self, skill_gaps: List[SkillGap], questions_per_skill: int = 2
    ) -> DiagnosticAssessment:
        target_skills = [gap.skill_name for gap in skill_gaps[:5]]

        all_questions = []
        for skill_name in target_skills:
            gap = next(g for g in skill_gaps if g.skill_name == skill_name)
            questions = self._generate_questions_for_skill(
                skill_name, gap, questions_per_skill
            )
            all_questions.extend(questions)

        return DiagnosticAssessment(
            target_skills=target_skills,
            questions=all_questions,
            estimated_duration_minutes=len(all_questions) * 2,
        )

    def _generate_questions_for_skill(
        self, skill_name: str, gap: SkillGap, count: int
    ) -> List[DiagnosticQuestion]:
        if gap.candidate_score >= 55:
            difficulty = "intermediate"
        elif gap.candidate_score >= 35:
            difficulty = "basic"
        else:
            difficulty = "fundamental"

        prompt = f"""Generate exactly {count} multiple-choice diagnostic questions to test proficiency in "{skill_name}".

Difficulty level: {difficulty}
Candidate claims: {gap.candidate_score}/100 proficiency

Requirements:
- Each question must have EXACTLY 4 options (A, B, C, D)
- Only ONE correct answer per question
- Questions should verify REAL understanding, not trivia
- Include practical/applied questions, not just definitions
- The correct answer should require genuine knowledge

Return ONLY valid JSON in this exact format (no markdown, no extra text):
[
  {{
    "question_text": "The question text here",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct_answer_index": 0,
    "difficulty": "{difficulty}",
    "explanation": "Why the correct answer is correct"
  }}
]"""

        try:
            response = self.client.chat.completions.create(
                model=LLM_MODEL,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = response.choices[0].message.content.strip()
            response_text = response_text.replace("```json", "").replace("```", "").strip()
            questions_data = json.loads(response_text)

            questions = []
            for i, q_data in enumerate(questions_data[:count]):
                q = DiagnosticQuestion(
                    question_id=f"DQ-{uuid.uuid4().hex[:8]}",
                    skill_being_tested=skill_name,
                    question_text=q_data["question_text"],
                    options=q_data["options"][:4],
                    correct_answer_index=q_data["correct_answer_index"],
                    difficulty=q_data.get("difficulty", difficulty),
                    explanation=q_data.get("explanation", ""),
                )
                questions.append(q)

            return questions

        except Exception as e:
            print(f"Error generating questions for {skill_name}: {e}")
            return [DiagnosticQuestion(
                question_id=f"DQ-{uuid.uuid4().hex[:8]}",
                skill_being_tested=skill_name,
                question_text=f"How would you rate your practical experience with {skill_name}?",
                options=[
                    "I have no experience",
                    "I have basic awareness",
                    "I use it regularly in my work",
                    "I can teach others and architect solutions",
                ],
                correct_answer_index=2,
                difficulty=difficulty,
                explanation="Self-assessment question for skill verification",
            )]

    def evaluate_responses(
        self,
        questions: List[DiagnosticQuestion],
        answers: List[int],
        original_gap: SkillGap,
    ) -> DiagnosticResult:
        responses = [
            answers[i] == questions[i].correct_answer_index
            for i in range(min(len(questions), len(answers)))
        ]

        correct_count = sum(responses)
        total_count = len(responses)
        mastery_prob = self.bkt.estimate_mastery(responses)

        if mastery_prob >= 0.85:
            adjusted_prof = ProficiencyLevel.DEMONSTRATED
        elif mastery_prob >= 0.65:
            adjusted_prof = ProficiencyLevel.APPLIED
        elif mastery_prob >= 0.45:
            adjusted_prof = ProficiencyLevel.USED
        else:
            adjusted_prof = ProficiencyLevel.MENTIONED

        adjusted_score = PROFICIENCY_TO_SCORE[adjusted_prof]
        if adjusted_score > original_gap.candidate_score:
            adjustment = (
                f"Diagnostic reveals higher proficiency than resume indicated. "
                f"Adjusted from {original_gap.candidate_score} to {adjusted_score}. "
                f"Removing beginner modules for {original_gap.skill_name}."
            )
        elif adjusted_score < original_gap.candidate_score:
            adjustment = (
                f"Diagnostic reveals lower proficiency than resume claimed. "
                f"Adjusted from {original_gap.candidate_score} to {adjusted_score}. "
                f"Adding foundational modules for {original_gap.skill_name}."
            )
        else:
            adjustment = (
                f"Diagnostic confirms resume-indicated proficiency level. "
                f"No pathway adjustment needed for {original_gap.skill_name}."
            )

        return DiagnosticResult(
            skill_name=original_gap.skill_name,
            questions_asked=total_count,
            correct_answers=correct_count,
            estimated_mastery_probability=round(mastery_prob, 3),
            adjusted_proficiency=adjusted_prof,
            pathway_adjustment=adjustment,
        )
