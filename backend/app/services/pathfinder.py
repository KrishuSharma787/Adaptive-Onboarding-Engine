"""
Adaptive Pathfinder Service
Builds a Directed Acyclic Graph of courses with prerequisite edges,
then generates an optimized learning pathway using topological sorting
and weighted gap-priority ordering.
"""

import networkx as nx
from typing import List, Dict, Optional
from app.models.schemas import (
    SkillGapAnalysis, SkillGap, LearningPathway, PathwayNode, Course,
)
from app.services.rag_engine import RAGEngine


class AdaptivePathfinder:
    """
    Generates optimized learning pathways using DAG-based traversal.

    Algorithm:
    1. For each skill gap, retrieve best-matching courses from RAG engine
    2. Build a DAG with courses as nodes and prerequisites as edges
    3. Assign phases based on topological order and difficulty
    4. Weight edges by gap severity to prioritize critical skills
    5. Generate a reasoning trace for each recommendation
    """

    def __init__(self, rag_engine: RAGEngine):
        self.rag = rag_engine

    def generate_pathway(
        self, gap_analysis: SkillGapAnalysis
    ) -> LearningPathway:
        """
        Generate a complete learning pathway from a skill gap analysis.
        """
        reasoning_trace = []
        reasoning_trace.append(
            f"[INIT] Starting pathway generation for {gap_analysis.candidate_name} "
            f"targeting role: {gap_analysis.job_title}"
        )
        reasoning_trace.append(
            f"[ANALYSIS] Overall readiness score: {gap_analysis.overall_readiness_score}%. "
            f"Identified {len(gap_analysis.skill_gaps)} skill gaps, "
            f"{len(gap_analysis.matched_skills)} skills already met."
        )

        # Step 1: Retrieve courses for each gap
        all_recommendations: List[Dict] = []
        seen_course_ids = set()

        for gap in gap_analysis.skill_gaps:
            reasoning_trace.append(
                f"[GAP] Processing: {gap.skill_name} "
                f"(candidate: {gap.candidate_score}, target: {gap.target_score}, "
                f"gap: {gap.gap_score:.1f})"
            )

            # Determine difficulty level needed based on gap size
            difficulty = self._gap_to_difficulty(gap)

            # Retrieve from RAG engine (grounded in catalog) — 1 best course per gap
            retrieved = self.rag.retrieve(
                skill_gap=gap.skill_name,
                difficulty_filter=difficulty,
                top_k=1,
            )

            if not retrieved:
                # Try without difficulty filter
                retrieved = self.rag.retrieve(
                    skill_gap=gap.skill_name,
                    top_k=1,
                )

            if retrieved:
                course = retrieved[0]  # Best match only
                if course["course_id"] not in seen_course_ids:
                    course["target_gap"] = gap
                    all_recommendations.append(course)
                    seen_course_ids.add(course["course_id"])
                    reasoning_trace.append(
                        f"[RETRIEVE] Found course: '{course['title']}' "
                        f"{course['source_citation']} "
                        f"(relevance: {course['relevance_score']:.3f}, "
                        f"difficulty: {course['difficulty']})"
                    )
            else:
                reasoning_trace.append(
                    f"[WARNING] No course found in catalog for skill: {gap.skill_name}. "
                    f"Manual review recommended."
                )

        # Step 2: Build DAG
        reasoning_trace.append(
            f"[GRAPH] Building prerequisite DAG with {len(all_recommendations)} courses"
        )
        graph, node_data = self._build_dag(all_recommendations)

        # Step 3: Topological sort for phase assignment
        try:
            topo_order = list(nx.topological_sort(graph))
        except nx.NetworkXUnfeasible:
            # If cycle detected, remove back edges and retry
            reasoning_trace.append("[GRAPH] Cycle detected in prerequisites, removing back edges")
            graph = self._remove_cycles(graph)
            topo_order = list(nx.topological_sort(graph))

        # Step 4: Assign phases and build pathway nodes
        pathway_nodes = []
        phase_assignments = self._assign_phases(graph, topo_order, node_data)

        for course_id in topo_order:
            if course_id not in node_data:
                continue

            data = node_data[course_id]
            gap: SkillGap = data.get("target_gap")
            phase = phase_assignments.get(course_id, 1)

            # Scale hours using same 8h baseline as generic onboarding
            # This guarantees personalized ≤ generic mathematically:
            # Generic = ALL skills × 8h, Personalized = only GAP skills × (proportion × 8h)
            HOURS_PER_SKILL = 8.0
            if gap and gap.target_score > 0:
                gap_proportion = (gap.target_score - gap.candidate_score) / gap.target_score
                scaled_hours = round(HOURS_PER_SKILL * gap_proportion, 1)
                scaled_hours = max(1.0, scaled_hours)
            else:
                gap_proportion = 1.0
                scaled_hours = HOURS_PER_SKILL

            node = PathwayNode(
                course_id=course_id,
                course_title=data["title"],
                target_skill=gap.skill_name if gap else "General",
                phase=phase,
                duration_hours=scaled_hours,
                prerequisites=list(graph.predecessors(course_id)),
                reasoning=(
                    f"Recommended to bridge the '{gap.skill_name}' gap. "
                    f"Candidate scores {gap.candidate_score}/100, "
                    f"target is {gap.target_score}/100. "
                    f"Training time: {scaled_hours}h ({gap_proportion:.0%} of full 8h module). "
                    f"This {data['difficulty']}-level course addresses the "
                    f"{gap.gap_score:.1f}-point weighted deficit."
                ) if gap else "Prerequisite course",
                confidence=min(data.get("relevance_score", 0.5) + 0.3, 1.0),
                source_catalog_id=data.get("source_citation", f"[Catalog:{course_id}]"),
            )
            pathway_nodes.append(node)

        # Step 5: Group into phases
        phases = self._group_phases(pathway_nodes)

        total_hours = sum(n.duration_hours for n in pathway_nodes)

        # Honest savings calculation — no fake cap
        generic_hours = gap_analysis.generic_training_hours
        if generic_hours > 0:
            actual_savings = ((generic_hours - total_hours) / generic_hours) * 100
        else:
            actual_savings = 0

        reasoning_trace.append(
            f"[COMPLETE] Generated pathway: {len(pathway_nodes)} courses, "
            f"{len(phases)} phases, {total_hours:.1f} total hours"
        )
        reasoning_trace.append(
            f"[SAVINGS] Personalized: {total_hours:.1f}h vs "
            f"Generic: {generic_hours:.1f}h "
            f"({actual_savings:.1f}% {'saved' if actual_savings > 0 else 'more — candidate has significant gaps'})"
        )

        return LearningPathway(
            candidate_name=gap_analysis.candidate_name,
            job_title=gap_analysis.job_title,
            total_courses=len(pathway_nodes),
            total_hours=round(total_hours, 1),
            phases=phases,
            pathway_nodes=pathway_nodes,
            reasoning_trace=reasoning_trace,
        )

    def _gap_to_difficulty(self, gap: SkillGap) -> Optional[str]:
        """Map gap size to appropriate course difficulty."""
        if gap.candidate_score == 0:
            return "beginner"
        elif gap.gap_score > 40:
            return "intermediate"
        elif gap.gap_score > 20:
            return "intermediate"
        else:
            return "advanced"

    def _build_dag(
        self, recommendations: List[Dict]
    ) -> tuple[nx.DiGraph, Dict]:
        """
        Build a DAG from course recommendations.
        Nodes = courses, Edges = prerequisite relationships.
        """
        G = nx.DiGraph()
        node_data = {}

        # Index courses by title for prerequisite linking
        title_to_id = {}
        for rec in recommendations:
            cid = rec["course_id"]
            G.add_node(cid)
            node_data[cid] = rec
            title_to_id[rec["title"].lower()] = cid

        # Add prerequisite edges
        for rec in recommendations:
            cid = rec["course_id"]
            for prereq_title in rec.get("prerequisites", []):
                prereq_lower = prereq_title.lower()
                if prereq_lower in title_to_id:
                    prereq_id = title_to_id[prereq_lower]
                    G.add_edge(prereq_id, cid)  # prereq -> course

        return G, node_data

    def _assign_phases(
        self,
        graph: nx.DiGraph,
        topo_order: List[str],
        node_data: Dict,
    ) -> Dict[str, int]:
        """
        Assign phase numbers based on difficulty and topological depth.
        Phase 1 = Foundations (beginner), Phase 2 = Core (intermediate),
        Phase 3 = Advanced (advanced).
        """
        difficulty_to_phase = {
            "beginner": 1,
            "intermediate": 2,
            "advanced": 3,
        }

        phases = {}
        for course_id in topo_order:
            data = node_data.get(course_id, {})
            difficulty = data.get("difficulty", "intermediate")
            base_phase = difficulty_to_phase.get(difficulty, 2)

            # Adjust phase based on graph depth
            depth = self._get_depth(graph, course_id)
            adjusted_phase = max(base_phase, min(depth + 1, 3))

            phases[course_id] = adjusted_phase

        return phases

    def _get_depth(self, graph: nx.DiGraph, node: str) -> int:
        """Get the longest path length to a node (its depth in the DAG)."""
        predecessors = list(graph.predecessors(node))
        if not predecessors:
            return 0
        return max(self._get_depth(graph, p) for p in predecessors) + 1

    def _remove_cycles(self, graph: nx.DiGraph) -> nx.DiGraph:
        """Remove cycles by removing back edges."""
        while not nx.is_directed_acyclic_graph(graph):
            try:
                cycle = nx.find_cycle(graph)
                if cycle:
                    graph.remove_edge(*cycle[-1][:2])
            except nx.NetworkXNoCycle:
                break
        return graph

    def _group_phases(self, nodes: List[PathwayNode]) -> List[Dict]:
        """Group pathway nodes into phase objects."""
        phase_map = {}
        phase_names = {1: "Foundations", 2: "Core Skills", 3: "Advanced Mastery"}

        for node in nodes:
            phase = node.phase
            if phase not in phase_map:
                phase_map[phase] = {
                    "phase_number": phase,
                    "phase_name": phase_names.get(phase, f"Phase {phase}"),
                    "courses": [],
                    "total_hours": 0,
                }
            phase_map[phase]["courses"].append({
                "course_id": node.course_id,
                "title": node.course_title,
                "skill": node.target_skill,
                "hours": node.duration_hours,
                "confidence": node.confidence,
            })
            phase_map[phase]["total_hours"] += node.duration_hours

        # Sort by phase number and round hours
        phases = sorted(phase_map.values(), key=lambda p: p["phase_number"])
        for p in phases:
            p["total_hours"] = round(p["total_hours"], 1)

        return phases
