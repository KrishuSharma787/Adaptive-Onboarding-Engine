#  AI-Adaptive Onboarding Engine

An AI-driven adaptive learning engine that parses a new hire's capabilities (via resume) and dynamically maps an optimized, personalized training pathway to achieve role-specific competency.

**Built for the ARTPARK CodeForge Hackathon**

---

##  Problem Statement

Corporate onboarding uses static "one-size-fits-all" curricula. Experienced hires waste time on known concepts while beginners are overwhelmed by advanced modules. This engine eliminates that inefficiency using AI to create personalized learning pathways.

---

##  Key Features

### 1. Intelligent Parsing (Constrained LLM Generation)
- Parses resumes and job descriptions using **Llama 3.3 70B** (via Groq) with **Pydantic-enforced schemas** via **Instructor**
- Extracts skills with **evidence-based depth scoring** (5-level proficiency: mentioned → used → applied → demonstrated → led)
- Deterministic, structured JSON output — no conversational wrappers or hallucinated fields

### 2. Data-Driven Skill Analysis (Trained on 2,484 Resumes)
- **Domain Skill Profiles**: Skill frequency distributions for all 24 job categories
- **Skill Co-occurrence Mining**: 4,811 prerequisite relationships discovered from resume data
- **Skill Rarity Calibration**: 2,301 skills scored by rarity for proficiency adjustment
- **Peer Cohort Benchmarking**: Candidates compared against real workforce distributions

### 3. O*NET Taxonomic Grounding
- Maps all extracted skills to **O*NET standardized taxonomy nodes** using semantic similarity (Sentence-BERT embeddings + cosine similarity)
- Standardized 0-100 scoring using the O*NET formula: `S = ((O - L) / (H - L)) × 100`
- Mathematical skill gap calculation: `G = Σ max(0, Tᵢ - Cᵢ) × Wᵢ`

### 4. Adaptive Learning Pathway (DAG-Based)
- Builds a **Directed Acyclic Graph** of courses with prerequisite edges using **NetworkX**
- **Topological sorting** ensures learners never encounter advanced content before prerequisites
- Prerequisites mined from real resume co-occurrence data, not hardcoded
- Courses retrieved via **hybrid RAG engine** with zero hallucinations

### 5. Grounding & Reliability (Hybrid RAG)
- **Sentence-BERT vector search** + **BM25 sparse search** with **Reciprocal Rank Fusion**
- Every recommendation cites its source in the course catalog (`[Catalog:CRS-XXXX]`)
- If no course exists for a skill gap, the system explicitly states "No internal course available"
- Citation-based audit trail prevents any fabricated recommendations

### 6. Skill Depth Scoring Matrix
- Radar chart visualization comparing candidate proficiency vs. role requirements
- Evidence-based scoring calibrated using skill rarity data from 2,484 resumes
- Color-coded proficiency badges with gap bars showing exact deficit

### 7. Estimated Time-to-Competency
- Personalized training hours vs. generic onboarding comparison
- Matched skills = 0 hours (already known, skipped entirely)
- Gap skills proportional to deficit size — personalized always less than generic

### 8. Diagnostic Assessment Generator
- LLM-generated targeted quiz (2 questions per top skill gap)
- **Bayesian Knowledge Tracing (BKT)** evaluates responses to estimate true mastery probability
- Adjusts pathway based on diagnostic results (adds/removes modules)
- BKT parameters: P(L₀), P(T), P(G), P(S) for principled mastery estimation

### 9. Reasoning Trace
- Full step-by-step AI reasoning log for every recommendation
- Color-coded trace entries: INIT → ANALYSIS → GAP → RETRIEVE → COMPLETE
- Each course recommendation links to its source evidence and catalog citation
- Expandable "Why was this recommended?" on every pathway node

### 10. Streaming Analysis (Server-Sent Events)
- Progressive results via SSE — no blank spinner for 60 seconds
- Each step streams partial results as they complete (skills found → gaps computed → pathway built)
- Real-time progress bar synced to actual backend processing steps

---

##  Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      React Frontend                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────┐  │
│  │  Upload   │ │  Skill   │ │ Pathway  │ │  Diagnostic    │  │
│  │  Panel    │ │  Radar   │ │ Timeline │ │  Quiz          │  │
│  └──────────┘ └──────────┘ └──────────┘ └────────────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────────────────┐  │
│  │   Gap    │ │  Time    │ │    Reasoning Trace Panel     │  │
│  │ Analysis │ │ Savings  │ │    (Streaming SSE)           │  │
│  └──────────┘ └──────────┘ └──────────────────────────────┘  │
└──────────────────────┬───────────────────────────────────────┘
                       │ REST API + SSE Stream
┌──────────────────────┴───────────────────────────────────────┐
│                    FastAPI Backend                            │
│                                                              │
│  ┌─────────────┐    ┌──────────────┐    ┌────────────────┐   │
│  │   Parser    │───▶│  Gap         │───▶│  Pathfinder    │   │
│  │ (Instructor │    │  Analyzer    │    │  (NetworkX     │   │
│  │ + Llama 3.3)│    │  (Data-      │    │   DAG)         │   │
│  └─────────────┘    │   Driven)    │    └───────┬────────┘   │
│                     └──────────────┘            │            │
│  ┌─────────────┐    ┌──────────────┐    ┌───────▼────────┐   │
│  │ Diagnostic  │    │  Taxonomy    │    │  RAG Engine    │   │
│  │ Generator   │    │  Mapper      │    │ (VectorStore   │   │
│  │ (BKT)       │    │ (SentBERT)   │    │  + BM25 + RRF) │   │
│  └─────────────┘    └──────────────┘    └────────────────┘   │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐   │
│  │         Trained Data (from 2,484 Resume Dataset)       │   │
│  │  domain_profiles.json  │  skill_prerequisites.json     │   │
│  │  skill_rarity.json     │  course_catalog.json (1,002)  │   │
│  └───────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

---

##  Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **LLM** | Llama 3.3 70B (via Groq API) | Skill extraction, diagnostic generation |
| **Constrained Gen** | Instructor + Pydantic | Deterministic JSON schema enforcement |
| **Embeddings** | Sentence-Transformers (all-MiniLM-L6-v2) | Semantic skill matching, taxonomy mapping |
| **Vector Search** | Custom (NumPy + scikit-learn) | Course catalog embedding search |
| **Sparse Search** | BM25 (custom implementation) | Exact keyword matching for course codes |
| **Graph Engine** | NetworkX | DAG construction, topological sorting |
| **Knowledge Tracing** | Bayesian Knowledge Tracing (custom) | Mastery estimation from diagnostic responses |
| **Backend** | FastAPI (Python) | REST API + SSE streaming |
| **Frontend** | React + Vite + Tailwind CSS | Interactive UI with progressive loading |
| **Visualization** | Recharts | Radar charts, skill heatmaps |
| **Containerization** | Docker + Docker Compose | Reproducible deployment |

---

##  Datasets

| Dataset | Source | Usage |
|---------|--------|-------|
| **Kaggle Resume Dataset** | [snehaanbhawal/resume-dataset](https://www.kaggle.com/datasets/snehaanbhawal/resume-dataset/data) | 2,484 resumes across 24 categories — trained domain profiles, skill co-occurrence, rarity scores, and course catalog |
| **O*NET Database** | [onetcenter.org](https://www.onetcenter.org/db_releases.html) | 50+ standardized skill constructs — canonical taxonomy for skill normalization |

### Trained Data Artifacts

| Artifact | Size | Description |
|----------|------|-------------|
| `domain_profiles.json` | 61KB | Top 30 skills per job category with frequency scores |
| `skill_prerequisites.json` | 570KB | 4,811 prerequisite relationships from co-occurrence mining |
| `skill_rarity.json` | 224KB | Rarity scores for 2,301 skills for proficiency calibration |
| `course_catalog.json` | 437KB | 1,002 domain-specific courses from real skill distributions |

---

##  Setup & Installation

### Prerequisites
- Python 3.11+
- Node.js 18+
- A Groq API key (free at [console.groq.com](https://console.groq.com))

### Option 1: Docker (Recommended)

```bash
git clone https://github.com/your-team/adaptive-onboarding-engine.git
cd adaptive-onboarding-engine

cp .env.example .env
# Edit .env and add your GROQ_API_KEY

docker-compose up --build
```

Open `http://localhost:3000`.

### Option 2: Manual Setup

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install --force
npm run dev
```

Open `http://localhost:3000`.

### Configuration

Open `backend/app/config.py` and paste your Groq API key:
```python
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "gsk_your_key_here")
```

---

##  Algorithms & Original Adaptive Logic

### Skill Depth Scoring (Original)
Evidence-based proficiency scoring calibrated by skill rarity data:

| Level | Base Score | Evidence Type | Rarity Bonus |
|-------|-----------|---------------|--------------|
| Mentioned | 15 | Listed in skills section only | -5 if common |
| Used | 35 | Referenced in one job/role | None |
| Applied | 55 | Appears across multiple roles | None |
| Demonstrated | 75 | Backed by measurable outcomes | +10 if rare |
| Led | 95 | Taught/architected/led | +10 if rare |

### Weighted Gap Penalty Formula
```
G = Σ max(0, Tᵢ - Cᵢ) × Wᵢ

Where:
  Tᵢ = Target standardized score for skill i (0-100)
  Cᵢ = Candidate's calibrated score for skill i (0-100)  
  Wᵢ = Importance weight (essential=1.0, preferred=0.7, nice_to_have=0.4)
```

### Data-Mined Prerequisite Detection
From 2,484 resumes, we compute:
```
P(skill_A | skill_B) = co-occurrence(A,B) / count(B)
```
If P(A|B) > 0.5 but P(B|A) < 0.3, then A is a prerequisite for B.
4,811 such relationships discovered and used in DAG construction.

### Bayesian Knowledge Tracing
Standard BKT model with 4 parameters:
- **P(L₀)=0.3**: Prior mastery probability
- **P(T)=0.1**: Learning rate per opportunity
- **P(G)=0.2**: Guess rate
- **P(S)=0.1**: Slip rate

### Time-to-Competency Formula
```
Generic hours    = total_required_skills × 8h
Personalized hrs = Σ (gap_proportion × 8h) for gap skills only
                   where gap_proportion = (target - candidate) / target
Matched skills   = 0 hours (skipped)
Time saved %     = (generic - personalized) / generic × 100
```

---

##  Internal Metrics

| Metric | Description |
|--------|-------------|
| **Readiness Score** | 0-100% indicating how ready the candidate is for the role |
| **Training Time Reduction** | % reduction vs. generic onboarding |
| **Pathway Coverage** | % of JD skills addressed by recommended courses |
| **Recommendation Confidence** | Per-course confidence score based on RAG relevance |
| **BKT Mastery Estimate** | Per-skill mastery probability from diagnostic quiz |
| **Peer Cohort Benchmark** | Candidate skill rarity vs. domain average from 2,484 resumes |

---

##  Cross-Domain Scalability

The engine scales across all 24 job categories in the dataset:
Accountant, Advocate, Agriculture, Apparel, Arts, Automobile, Aviation, Banking, BPO, Business Development, Chef, Construction, Consultant, Designer, Digital Media, Engineering, Finance, Fitness, Healthcare, HR, Information Technology, Public Relations, Sales, Teacher.

Achieved through:
- **O*NET taxonomy**: Universal skill vocabulary across domains
- **Data-driven catalog**: 1,002 courses generated from real skill distributions, not hardcoded
- **Semantic matching**: Domain-specific terminology handled via embeddings
- **Same math, different data**: Gap formula and DAG logic are domain-agnostic
- **Trained prerequisites**: Co-occurrence rules adapt per domain automatically

---

##  Project Structure

```
adaptive-onboarding-engine/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI + SSE streaming endpoints
│   │   ├── config.py            # Configuration (Groq API key)
│   │   ├── models/
│   │   │   └── schemas.py       # Pydantic schemas (constrained generation)
│   │   ├── services/
│   │   │   ├── parser.py        # Resume/JD parsing (Groq + Instructor)
│   │   │   ├── taxonomy.py      # O*NET mapping & standardization
│   │   │   ├── gap_analyzer.py  # Data-driven skill gap computation
│   │   │   ├── rag_engine.py    # Vector + BM25 hybrid retrieval
│   │   │   ├── pathfinder.py    # DAG-based adaptive pathway generation
│   │   │   ├── catalog_builder.py # Course catalog from resume dataset
│   │   │   └── diagnostic.py    # Quiz generation & BKT evaluation
│   │   ├── data/
│   │   │   ├── course_catalog.json      # 1,002 courses (trained)
│   │   │   ├── domain_profiles.json     # 24 domain skill profiles (trained)
│   │   │   ├── skill_prerequisites.json # 4,811 prerequisite rules (trained)
│   │   │   └── skill_rarity.json        # 2,301 skill rarity scores (trained)
│   │   └── utils/
│   │       └── pdf_utils.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Main app with SSE streaming
│   │   ├── components/
│   │   │   ├── UploadPanel.jsx
│   │   │   ├── StatusBar.jsx    # Progressive streaming display
│   │   │   ├── SkillRadar.jsx
│   │   │   ├── GapAnalysis.jsx
│   │   │   ├── PathwayTimeline.jsx
│   │   │   ├── ReasoningTrace.jsx
│   │   │   ├── DiagnosticQuiz.jsx
│   │   │   └── TimeSavings.jsx
│   │   └── utils/
│   │       └── api.js           # SSE + REST API client
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
├── setup.sh
└── README.md
```

---

##  License

MIT
