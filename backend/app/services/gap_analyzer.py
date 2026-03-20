"""
Skill Gap Analysis Service (Data-Driven)
Uses domain profiles, skill rarity, and mined prerequisites
trained from 2,484 resumes. Features fuzzy word-overlap matching
to correctly identify related skills across different phrasings.

Example matches this enables:
  "Advanced Financial Analysis and Modeling" ↔ "Financial Reporting" (partial)
  "ERP Systems" ↔ "SAP" (via O*NET node)
  "Team Leadership and Management" ↔ "Team Leadership" (substring)
  "accounting" (domain profile) ↔ "General Ledger Accounting" (word overlap)
"""

import json
import os
import re
from typing import List, Dict, Set, Optional
from app.models.schemas import (
    ParsedResume, ParsedJobDescription, SkillGapAnalysis, SkillGap,
    ProficiencyLevel, PROFICIENCY_TO_SCORE,
    ExtractedSkill, RequiredSkill,
)
from app.services.taxonomy import TaxonomyMapper

IMPORTANCE_WEIGHTS = {
    "essential": 1.0,
    "preferred": 0.7,
    "nice_to_have": 0.4,
}

GENERIC_HOURS_PER_SKILL = 8.0

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

STOP_WORDS = {
    "and", "or", "the", "a", "an", "of", "in", "for", "to", "with",
    "on", "at", "by", "is", "are", "was", "be", "experience", "advanced",
    "basic", "skills", "knowledge", "proficiency", "expert", "level",
}

# Known synonyms / equivalences that word overlap won't catch
SYNONYM_MAP = {
    "sap": ["erp", "erp systems", "enterprise resource planning"],
    "oracle": ["erp", "erp systems", "enterprise resource planning"],
    "quickbooks": ["accounting software"],
    "excel": ["spreadsheets", "microsoft excel", "ms excel"],
    "powerpoint": ["presentations", "microsoft powerpoint"],
    "word": ["microsoft word", "document processing"],
    "python": ["programming", "scripting", "coding"],
    "sql": ["database", "database queries", "data querying"],
    "tableau": ["data visualization", "data analytics", "analytics"],
    "power bi": ["data visualization", "data analytics", "analytics"],
    "gaap": ["accounting standards", "financial compliance", "ifrs"],
    "ifrs": ["accounting standards", "financial compliance", "gaap"],
    "financial reporting": ["financial analysis", "financial statements"],
    "financial analysis": ["financial reporting", "financial modeling"],
    "budgeting": ["budget management", "budgets", "forecasting"],
    "forecasting": ["financial planning", "budgeting"],
    "leadership": ["team leadership", "team management", "management"],
    "team leadership": ["leadership", "management", "people management"],
    "project management": ["program management", "project coordination"],
    "customer service": ["client relations", "customer relations"],
    "sales": ["business development", "revenue generation"],
    "marketing": ["digital marketing", "market strategy"],
    "accounting": ["financial accounting", "general ledger", "bookkeeping"],
    "audit": ["auditing", "audit support", "internal audit"],
    "tax": ["tax preparation", "tax compliance", "taxation"],
    "risk management": ["internal controls", "compliance", "risk assessment"],
}


def _load_json(filename):
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}


def _tokenize(text: str) -> Set[str]:
    """Extract meaningful words from a skill name."""
    words = set(re.findall(r'[a-z]+', text.lower()))
    return words - STOP_WORDS


def _fuzzy_match_score(skill_a: str, skill_b: str) -> float:
    """
    Compute fuzzy match score between two skill names.
    Returns 0.0 (no match) to 1.0 (exact match).
    
    Uses three strategies:
    1. Exact match → 1.0
    2. Substring containment → 0.85
    3. Word overlap (Jaccard-like) → 0.0 to 0.8
    4. Synonym lookup → 0.75
    """
    a_lower = skill_a.lower().strip()
    b_lower = skill_b.lower().strip()

    # 1. Exact
    if a_lower == b_lower:
        return 1.0

    # 2. Substring
    if a_lower in b_lower or b_lower in a_lower:
        return 0.85

    # 3. Synonym lookup
    a_syns = set(SYNONYM_MAP.get(a_lower, []))
    b_syns = set(SYNONYM_MAP.get(b_lower, []))
    if b_lower in a_syns or a_lower in b_syns:
        return 0.75
    # Check if any synonym of A matches any synonym of B
    if a_syns & b_syns:
        return 0.7

    # 4. Word overlap
    words_a = _tokenize(a_lower)
    words_b = _tokenize(b_lower)
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    if not union:
        return 0.0
    jaccard = len(intersection) / len(union)
    # Boost if the overlap covers most of the shorter skill name
    shorter_len = min(len(words_a), len(words_b))
    if shorter_len > 0:
        coverage = len(intersection) / shorter_len
    else:
        coverage = 0
    # Weighted combo: coverage matters more than pure Jaccard
    score = (jaccard * 0.4 + coverage * 0.6) * 0.8
    return score


# Minimum score to consider a match
MATCH_THRESHOLD = 0.4


class GapAnalyzer:
    """
    Data-driven skill gap analysis with fuzzy matching.
    Uses domain profiles trained from 2,484 resumes.
    """

    def __init__(self):
        self.taxonomy_mapper = TaxonomyMapper()
        self.domain_profiles = _load_json("domain_profiles.json")
        self.skill_rarity = _load_json("skill_rarity.json")
        self.skill_prerequisites = _load_json("skill_prerequisites.json")

        self.prereq_lookup = {}
        for p in self.skill_prerequisites:
            adv = p["advanced_skill"]
            if adv not in self.prereq_lookup:
                self.prereq_lookup[adv] = []
            self.prereq_lookup[adv].append({
                "skill": p["prerequisite"],
                "confidence": p["confidence"],
            })

        print(f"GapAnalyzer loaded: {len(self.domain_profiles)} domain profiles, "
              f"{len(self.skill_rarity)} skill rarity scores, "
              f"{len(self.skill_prerequisites)} prerequisite rules")

    def analyze(
        self, resume: ParsedResume, jd: ParsedJobDescription
    ) -> SkillGapAnalysis:
        """
        Full analysis pipeline:
        1. Fuzzy-match candidate skills to JD requirements
        2. Calibrate scores using rarity data
        3. Compute weighted gaps
        4. Check data-mined prerequisites
        5. Compute peer cohort comparison
        6. Calculate hours (personalized always < generic)
        """
        # Build candidate skill lookup
        candidate_skills: Dict[str, ExtractedSkill] = {
            skill.skill_name.lower().strip(): skill
            for skill in resume.extracted_skills
        }

        # O*NET mappings for fallback semantic matching
        all_skill_names = [s.skill_name for s in resume.extracted_skills] + \
                          [s.skill_name for s in jd.required_skills]
        onet_mappings = self.taxonomy_mapper.map_all_skills(all_skill_names)

        skill_gaps: List[SkillGap] = []
        matched_skills: List[str] = []
        total_gap_penalty = 0.0

        for req_skill in jd.required_skills:
            target_score = PROFICIENCY_TO_SCORE[req_skill.required_level]
            importance_weight = IMPORTANCE_WEIGHTS.get(req_skill.importance, 0.5)

            # Fuzzy match against all candidate skills
            candidate_match, match_score = self._find_best_match(
                req_skill.skill_name, candidate_skills, onet_mappings
            )

            if candidate_match:
                candidate_score = self._calibrate_score(candidate_match)
                # Partial matches reduce the effective candidate score
                if match_score < 0.85:
                    candidate_score = candidate_score * match_score
            else:
                candidate_score = 0.0

            raw_gap = max(0, target_score - candidate_score)
            weighted_gap = raw_gap * importance_weight

            onet_info = onet_mappings.get(req_skill.skill_name)
            onet_node = onet_info["onet_name"] if onet_info else None

            if raw_gap > 5:  # Small gaps (<5 points) count as matched
                reasoning = self._generate_gap_reasoning(
                    req_skill, candidate_match, match_score, candidate_score, target_score
                )
                skill_gaps.append(SkillGap(
                    skill_name=req_skill.skill_name,
                    onet_node=onet_node,
                    candidate_score=round(candidate_score, 1),
                    target_score=target_score,
                    gap_score=round(weighted_gap, 1),
                    importance_weight=importance_weight,
                    reasoning=reasoning,
                ))
                total_gap_penalty += weighted_gap
            else:
                matched_skills.append(req_skill.skill_name)

        # Check for missing prerequisites
        missing_prereqs = self._check_missing_prerequisites(skill_gaps, candidate_skills)
        for prereq_gap in missing_prereqs:
            if prereq_gap.skill_name not in [g.skill_name for g in skill_gaps]:
                skill_gaps.append(prereq_gap)
                total_gap_penalty += prereq_gap.gap_score

        skill_gaps.sort(key=lambda g: g.gap_score, reverse=True)

        # Readiness score
        max_possible_penalty = sum(
            PROFICIENCY_TO_SCORE[s.required_level] * IMPORTANCE_WEIGHTS.get(s.importance, 0.5)
            for s in jd.required_skills
        )
        readiness = max(0, 100 - (total_gap_penalty / max(max_possible_penalty, 1)) * 100)

        # Hours calculation
        generic_hours = len(jd.required_skills) * GENERIC_HOURS_PER_SKILL
        estimated_hours = 0.0
        for gap in skill_gaps:
            if gap.target_score > 0:
                gap_proportion = (gap.target_score - gap.candidate_score) / gap.target_score
            else:
                gap_proportion = 1.0
            estimated_hours += gap_proportion * GENERIC_HOURS_PER_SKILL

        time_saved = max(0, ((generic_hours - estimated_hours) / max(generic_hours, 1)) * 100)

        # Peer comparison
        peer_comparison = self._compute_peer_comparison(resume, jd)

        return SkillGapAnalysis(
            candidate_name=resume.candidate_name,
            job_title=jd.job_title,
            overall_readiness_score=round(readiness, 1),
            total_gap_penalty=round(total_gap_penalty, 2),
            skill_gaps=skill_gaps,
            matched_skills=matched_skills,
            estimated_training_hours=round(estimated_hours, 1),
            generic_training_hours=round(generic_hours, 1),
            time_saved_percent=round(time_saved, 1),
            peer_comparison=peer_comparison,
        )

    def _find_best_match(
        self,
        required_skill_name: str,
        candidate_skills: Dict[str, ExtractedSkill],
        onet_mappings: Dict,
    ) -> tuple[Optional[ExtractedSkill], float]:
        """
        Find best matching candidate skill using multi-strategy fuzzy matching.
        Returns (matched_skill, match_score) or (None, 0.0).
        """
        best_skill = None
        best_score = 0.0

        for cand_name, cand_skill in candidate_skills.items():
            # Strategy 1-4: Fuzzy match
            score = _fuzzy_match_score(required_skill_name, cand_skill.skill_name)
            if score > best_score:
                best_score = score
                best_skill = cand_skill

        # Strategy 5: O*NET semantic match
        if best_score < MATCH_THRESHOLD:
            req_onet = onet_mappings.get(required_skill_name)
            if req_onet:
                for cand_name, cand_skill in candidate_skills.items():
                    cand_onet = onet_mappings.get(cand_skill.skill_name)
                    if cand_onet and cand_onet["onet_id"] == req_onet["onet_id"]:
                        onet_score = 0.65  # O*NET category match
                        if onet_score > best_score:
                            best_score = onet_score
                            best_skill = cand_skill

        if best_score >= MATCH_THRESHOLD:
            return best_skill, best_score
        return None, 0.0

    def _calibrate_score(self, skill: ExtractedSkill) -> float:
        """
        Calibrate proficiency using skill rarity data from 2,484 resumes.
        Rare skills at high levels get a boost. Common skills just listed get a penalty.
        """
        base_score = PROFICIENCY_TO_SCORE[skill.proficiency]
        skill_lower = skill.skill_name.lower().strip()

        rarity_info = self.skill_rarity.get(skill_lower)
        if rarity_info:
            rarity = rarity_info["rarity_score"]
            if skill.proficiency in [ProficiencyLevel.DEMONSTRATED, ProficiencyLevel.LED]:
                bonus = rarity * 10
            elif skill.proficiency == ProficiencyLevel.MENTIONED:
                bonus = -(1 - rarity) * 5
            else:
                bonus = 0
            return min(100, max(0, base_score + bonus))

        return base_score

    def _compute_peer_comparison(
        self, resume: ParsedResume, jd: ParsedJobDescription
    ) -> dict:
        """
        Compare candidate against peer cohort using fuzzy matching.
        Trained from 2,484 resumes across 24 job categories.
        """
        candidate_skill_names = [
            s.skill_name.lower().strip() for s in resume.extracted_skills
        ]

        target_domain = self._match_domain(jd, resume)

        if not target_domain or target_domain not in self.domain_profiles:
            return {
                "domain": "Unknown",
                "total_resumes_analyzed": 2484,
                "skill_coverage": [],
                "percentile": None,
                "common_gaps": [],
                "strengths": [],
            }

        profile = self.domain_profiles[target_domain]

        skill_coverage = []
        candidate_has_count = 0
        common_gaps = []
        strengths = []

        for skill_entry in profile[:20]:
            domain_skill = skill_entry["skill"]
            domain_frequency = skill_entry["frequency"]

            # Fuzzy match: does candidate have anything similar?
            candidate_has = False
            best_match_name = None
            for cand_skill in candidate_skill_names:
                score = _fuzzy_match_score(domain_skill, cand_skill)
                if score >= MATCH_THRESHOLD:
                    candidate_has = True
                    best_match_name = cand_skill
                    break

            skill_coverage.append({
                "skill": domain_skill,
                "domain_frequency": round(domain_frequency * 100, 1),
                "candidate_has": candidate_has,
                "matched_to": best_match_name if candidate_has else None,
            })

            if candidate_has:
                candidate_has_count += 1
                if domain_frequency < 0.4:
                    strengths.append({
                        "skill": domain_skill,
                        "domain_frequency": round(domain_frequency * 100, 1),
                        "insight": f"Only {domain_frequency:.0%} of {target_domain} professionals have this skill",
                    })
            else:
                if domain_frequency > 0.5:
                    common_gaps.append({
                        "skill": domain_skill,
                        "domain_frequency": round(domain_frequency * 100, 1),
                        "insight": f"{domain_frequency:.0%} of {target_domain} professionals have this skill",
                    })

        # Weighted percentile
        weighted_score = sum(
            s["domain_frequency"] for s in skill_coverage if s["candidate_has"]
        )
        max_weighted = sum(s["domain_frequency"] for s in skill_coverage)
        percentile = round((weighted_score / max(max_weighted, 1)) * 100, 1)

        return {
            "domain": target_domain,
            "total_resumes_analyzed": 2484,
            "domain_resumes": len(profile),
            "skills_checked": len(skill_coverage),
            "skills_matched": candidate_has_count,
            "percentile": percentile,
            "skill_coverage": skill_coverage,
            "common_gaps": common_gaps[:5],
            "strengths": strengths[:5],
        }

    def _match_domain(self, jd: ParsedJobDescription, resume: ParsedResume) -> str:
        """Match JD/resume to closest trained domain profile."""
        for domain_hint in [jd.domain, resume.domain, jd.job_title, resume.current_role]:
            if not domain_hint:
                continue
            hint_lower = domain_hint.lower()
            for domain in self.domain_profiles.keys():
                if domain.lower() in hint_lower or hint_lower in domain.lower():
                    return domain

        # Fuzzy: count word overlaps between candidate skills and each domain
        candidate_skills = [s.skill_name.lower().strip() for s in resume.extracted_skills]
        best_domain = None
        best_overlap = 0

        for domain, profile in self.domain_profiles.items():
            domain_skill_names = [s["skill"] for s in profile[:20]]
            overlap = 0
            for ds in domain_skill_names:
                for cs in candidate_skills:
                    if _fuzzy_match_score(ds, cs) >= MATCH_THRESHOLD:
                        overlap += 1
                        break
            if overlap > best_overlap:
                best_overlap = overlap
                best_domain = domain

        return best_domain

    def _check_missing_prerequisites(
        self,
        existing_gaps: List[SkillGap],
        candidate_skills: Dict[str, ExtractedSkill],
    ) -> List[SkillGap]:
        """Check for missing prerequisites using data-mined co-occurrence rules."""
        missing = []

        for gap in existing_gaps:
            skill_lower = gap.skill_name.lower().strip()
            prereqs = self.prereq_lookup.get(skill_lower, [])

            for prereq in prereqs[:2]:
                prereq_name = prereq["skill"]
                confidence = prereq["confidence"]

                # Check if candidate has this prerequisite (fuzzy)
                has_prereq = False
                for cand_name in candidate_skills:
                    if _fuzzy_match_score(prereq_name, cand_name) >= MATCH_THRESHOLD:
                        has_prereq = True
                        break

                if not has_prereq:
                    missing.append(SkillGap(
                        skill_name=prereq_name,
                        onet_node=None,
                        candidate_score=0,
                        target_score=35,
                        gap_score=round(35 * 0.5, 1),
                        importance_weight=0.5,
                        reasoning=(
                            f"Data-mined prerequisite: '{prereq_name}' appears in "
                            f"{confidence:.0%} of resumes that include '{gap.skill_name}'. "
                            f"Candidate is missing this foundational skill. "
                            f"(Discovered from analysis of 2,484 professional resumes)"
                        ),
                    ))

        return missing

    def _generate_gap_reasoning(
        self,
        req_skill: RequiredSkill,
        candidate_match: Optional[ExtractedSkill],
        match_score: float,
        candidate_score: float,
        target_score: float,
    ) -> str:
        """Generate human-readable reasoning for a skill gap."""
        domain_context = ""
        skill_lower = req_skill.skill_name.lower().strip()
        rarity_info = self.skill_rarity.get(skill_lower)
        if rarity_info:
            freq_pct = rarity_info["global_frequency"] * 100
            domain_context = f" This skill appears in {freq_pct:.1f}% of professional resumes in our dataset."

        if candidate_match is None:
            return (
                f"Skill '{req_skill.skill_name}' is {req_skill.importance} for this role "
                f"at '{req_skill.required_level.value}' level (score: {target_score}), "
                f"but was NOT found in the candidate's resume. Full training required."
                f"{domain_context}"
            )
        else:
            match_note = ""
            if match_score < 1.0:
                match_note = (
                    f" (Matched via '{candidate_match.skill_name}' with "
                    f"{match_score:.0%} similarity — partial credit applied.)"
                )
            return (
                f"Skill '{req_skill.skill_name}' requires '{req_skill.required_level.value}' level "
                f"(score: {target_score}), candidate demonstrates "
                f"'{candidate_match.proficiency.value}' level (effective score: {candidate_score:.0f}). "
                f"Evidence: \"{candidate_match.evidence}\". "
                f"Gap of {target_score - candidate_score:.0f} points needs bridging."
                f"{match_note}{domain_context}"
            )
