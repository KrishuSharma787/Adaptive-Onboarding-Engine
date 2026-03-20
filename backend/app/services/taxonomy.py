"""
Taxonomic Grounding Service
Maps extracted skills to O*NET standardized taxonomy nodes
using semantic similarity via sentence embeddings.
"""

import json
import os
import numpy as np
from typing import Dict, List, Tuple, Optional
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from app.config import EMBEDDING_MODEL

# O*NET Skills Taxonomy (35 core skills + common technical extensions)
# Each entry: { "id": O*NET code, "name": canonical name, "description": definition, "category": grouping }
ONET_SKILLS_TAXONOMY = [
    # --- Basic Skills ---
    {"id": "2.A.1.a", "name": "Reading Comprehension", "description": "Understanding written sentences and paragraphs in work-related documents", "category": "Basic Skills"},
    {"id": "2.A.1.b", "name": "Active Listening", "description": "Giving full attention to what other people are saying and understanding the points being made", "category": "Basic Skills"},
    {"id": "2.A.1.c", "name": "Writing", "description": "Communicating effectively in writing as appropriate for the needs of the audience", "category": "Basic Skills"},
    {"id": "2.A.1.d", "name": "Speaking", "description": "Talking to others to convey information effectively", "category": "Basic Skills"},
    {"id": "2.A.1.e", "name": "Mathematics", "description": "Using mathematics to solve problems", "category": "Basic Skills"},
    {"id": "2.A.1.f", "name": "Science", "description": "Using scientific rules and methods to solve problems", "category": "Basic Skills"},
    # --- Social Skills ---
    {"id": "2.B.1.a", "name": "Critical Thinking", "description": "Using logic and reasoning to identify strengths and weaknesses of alternative solutions", "category": "Social Skills"},
    {"id": "2.B.1.b", "name": "Active Learning", "description": "Understanding the implications of new information for both current and future problem-solving", "category": "Social Skills"},
    {"id": "2.B.1.c", "name": "Learning Strategies", "description": "Selecting and using training methods and procedures appropriate for the situation", "category": "Social Skills"},
    {"id": "2.B.1.d", "name": "Monitoring", "description": "Monitoring and assessing performance of yourself, other individuals, or organizations to make improvements", "category": "Social Skills"},
    # --- Complex Problem Solving ---
    {"id": "2.B.2.i", "name": "Complex Problem Solving", "description": "Identifying complex problems and reviewing related information to develop and evaluate options", "category": "Problem Solving"},
    # --- Technical Skills ---
    {"id": "2.B.3.a", "name": "Operations Analysis", "description": "Analyzing needs and product requirements to create a design", "category": "Technical Skills"},
    {"id": "2.B.3.b", "name": "Technology Design", "description": "Generating or adapting equipment and technology to serve user needs", "category": "Technical Skills"},
    {"id": "2.B.3.c", "name": "Equipment Selection", "description": "Determining the kind of tools and equipment needed to do a job", "category": "Technical Skills"},
    {"id": "2.B.3.d", "name": "Installation", "description": "Installing equipment, machines, wiring, or programs to meet specifications", "category": "Technical Skills"},
    {"id": "2.B.3.e", "name": "Programming", "description": "Writing computer programs for various purposes", "category": "Technical Skills"},
    {"id": "2.B.3.g", "name": "Quality Control Analysis", "description": "Conducting tests and inspections of products, services, or processes to evaluate quality", "category": "Technical Skills"},
    {"id": "2.B.3.h", "name": "Operations Monitoring", "description": "Watching gauges, dials, or other indicators to make sure a machine is working properly", "category": "Technical Skills"},
    {"id": "2.B.3.j", "name": "Troubleshooting", "description": "Determining causes of operating errors and deciding what to do about it", "category": "Technical Skills"},
    {"id": "2.B.3.k", "name": "Repairing", "description": "Repairing machines or systems using the needed tools", "category": "Technical Skills"},
    # --- Systems Skills ---
    {"id": "2.B.4.e", "name": "Judgment and Decision Making", "description": "Considering the relative costs and benefits of potential actions to choose the most appropriate one", "category": "Systems Skills"},
    {"id": "2.B.4.g", "name": "Systems Analysis", "description": "Determining how a system should work and how changes in conditions will affect outcomes", "category": "Systems Skills"},
    {"id": "2.B.4.h", "name": "Systems Evaluation", "description": "Identifying measures or indicators of system performance and the actions needed to improve", "category": "Systems Skills"},
    # --- Resource Management ---
    {"id": "2.B.5.a", "name": "Time Management", "description": "Managing one's own time and the time of others", "category": "Resource Management"},
    {"id": "2.B.5.b", "name": "Management of Financial Resources", "description": "Determining how money will be spent and accounting for these expenditures", "category": "Resource Management"},
    {"id": "2.B.5.c", "name": "Management of Material Resources", "description": "Obtaining and seeing to the appropriate use of equipment, facilities, and materials", "category": "Resource Management"},
    {"id": "2.B.5.d", "name": "Management of Personnel Resources", "description": "Motivating, developing, and directing people as they work, identifying the best people for the job", "category": "Resource Management"},
    # --- Social/Interpersonal ---
    {"id": "2.B.1.e", "name": "Social Perceptiveness", "description": "Being aware of others' reactions and understanding why they react as they do", "category": "Social Skills"},
    {"id": "2.B.1.f", "name": "Coordination", "description": "Adjusting actions in relation to others' actions", "category": "Social Skills"},
    {"id": "2.B.1.g", "name": "Persuasion", "description": "Persuading others to change their minds or behavior", "category": "Social Skills"},
    {"id": "2.B.1.h", "name": "Negotiation", "description": "Bringing others together and trying to reconcile differences", "category": "Social Skills"},
    {"id": "2.B.1.i", "name": "Instructing", "description": "Teaching others how to do something", "category": "Social Skills"},
    {"id": "2.B.1.j", "name": "Service Orientation", "description": "Actively looking for ways to help people", "category": "Social Skills"},
    # --- Extended Technical Skills (common in resumes but not core O*NET) ---
    {"id": "EXT.001", "name": "Data Analysis", "description": "Collecting, processing, and performing statistical analysis on large datasets", "category": "Technical Skills"},
    {"id": "EXT.002", "name": "Project Management", "description": "Planning, executing, and closing projects including scope, time, cost, and quality management", "category": "Management Skills"},
    {"id": "EXT.003", "name": "Financial Analysis", "description": "Evaluating financial data, budgets, forecasts, and investment decisions", "category": "Financial Skills"},
    {"id": "EXT.004", "name": "Accounting", "description": "Recording, classifying, and summarizing financial transactions and preparing financial statements", "category": "Financial Skills"},
    {"id": "EXT.005", "name": "Software Development", "description": "Designing, coding, testing, and maintaining software applications", "category": "Technical Skills"},
    {"id": "EXT.006", "name": "Database Management", "description": "Designing, implementing, and maintaining database systems for data storage and retrieval", "category": "Technical Skills"},
    {"id": "EXT.007", "name": "Cloud Computing", "description": "Deploying and managing applications and services on cloud platforms like AWS, Azure, or GCP", "category": "Technical Skills"},
    {"id": "EXT.008", "name": "Machine Learning", "description": "Designing and implementing algorithms that learn from and make predictions on data", "category": "Technical Skills"},
    {"id": "EXT.009", "name": "Customer Relationship Management", "description": "Managing interactions with customers, analyzing data, and improving business relationships", "category": "Business Skills"},
    {"id": "EXT.010", "name": "Digital Marketing", "description": "Promoting products or services through digital channels including SEO, social media, and email", "category": "Business Skills"},
    {"id": "EXT.011", "name": "Supply Chain Management", "description": "Managing the flow of goods and services from raw materials to final delivery", "category": "Operations"},
    {"id": "EXT.012", "name": "Human Resources Management", "description": "Recruiting, training, compensating, and managing employee relations and compliance", "category": "Management Skills"},
    {"id": "EXT.013", "name": "Sales", "description": "Identifying prospects, presenting products, negotiating terms, and closing deals", "category": "Business Skills"},
    {"id": "EXT.014", "name": "Compliance and Regulatory", "description": "Ensuring organizational adherence to laws, regulations, and internal policies", "category": "Legal/Compliance"},
    {"id": "EXT.015", "name": "Healthcare Operations", "description": "Managing clinical workflows, patient care coordination, and health system administration", "category": "Healthcare"},
    {"id": "EXT.016", "name": "Cybersecurity", "description": "Protecting systems, networks, and data from cyber threats and unauthorized access", "category": "Technical Skills"},
    {"id": "EXT.017", "name": "UI/UX Design", "description": "Designing user interfaces and experiences for digital products through research, prototyping, and testing", "category": "Design"},
    {"id": "EXT.018", "name": "Technical Writing", "description": "Creating clear documentation, manuals, and technical content for complex systems", "category": "Communication"},
    {"id": "EXT.019", "name": "Budgeting and Forecasting", "description": "Planning financial budgets and predicting future financial performance", "category": "Financial Skills"},
    {"id": "EXT.020", "name": "Tax Preparation", "description": "Preparing and filing tax returns, ensuring compliance with tax laws and regulations", "category": "Financial Skills"},
]


class TaxonomyMapper:
    """Maps extracted skills to O*NET taxonomy nodes using semantic similarity."""

    def __init__(self):
        self.model = SentenceTransformer(EMBEDDING_MODEL)
        self.taxonomy = ONET_SKILLS_TAXONOMY
        self._taxonomy_embeddings = None
        self._taxonomy_texts = None

    def _get_taxonomy_embeddings(self) -> np.ndarray:
        """Lazy-load and cache taxonomy embeddings."""
        if self._taxonomy_embeddings is None:
            self._taxonomy_texts = [
                f"{node['name']}: {node['description']}" for node in self.taxonomy
            ]
            self._taxonomy_embeddings = self.model.encode(self._taxonomy_texts)
        return self._taxonomy_embeddings

    def map_skill_to_onet(self, skill_text: str, threshold: float = 0.35) -> Optional[Dict]:
        """
        Map a raw skill string to the closest O*NET taxonomy node.
        
        Args:
            skill_text: The raw skill name/phrase from resume parsing
            threshold: Minimum cosine similarity to accept a match
            
        Returns:
            Dict with matched O*NET node info and similarity score, or None
        """
        taxonomy_embeddings = self._get_taxonomy_embeddings()
        skill_embedding = self.model.encode([skill_text])

        similarities = cosine_similarity(skill_embedding, taxonomy_embeddings)[0]
        best_idx = np.argmax(similarities)
        best_score = similarities[best_idx]

        if best_score >= threshold:
            node = self.taxonomy[best_idx]
            return {
                "onet_id": node["id"],
                "onet_name": node["name"],
                "onet_category": node["category"],
                "similarity_score": float(best_score),
            }
        return None

    def map_all_skills(self, skill_names: List[str]) -> Dict[str, Optional[Dict]]:
        """Map a list of skill names to O*NET nodes in batch."""
        taxonomy_embeddings = self._get_taxonomy_embeddings()
        skill_embeddings = self.model.encode(skill_names)

        similarities = cosine_similarity(skill_embeddings, taxonomy_embeddings)

        results = {}
        for i, skill_name in enumerate(skill_names):
            best_idx = np.argmax(similarities[i])
            best_score = similarities[i][best_idx]

            if best_score >= 0.35:
                node = self.taxonomy[best_idx]
                results[skill_name] = {
                    "onet_id": node["id"],
                    "onet_name": node["name"],
                    "onet_category": node["category"],
                    "similarity_score": float(best_score),
                }
            else:
                results[skill_name] = None

        return results


def standardize_score(original: float, low: float, high: float) -> float:
    """
    O*NET standardization formula: S = ((O - L) / (H - L)) * 100
    Converts any scale to 0-100.
    """
    if high == low:
        return 0.0
    return ((original - low) / (high - low)) * 100.0
