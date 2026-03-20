import React, { useState, useCallback } from 'react';
import UploadPanel from './components/UploadPanel';
import StatusBar from './components/StatusBar';
import SkillRadar from './components/SkillRadar';
import GapAnalysis from './components/GapAnalysis';
import PathwayTimeline from './components/PathwayTimeline';
import ReasoningTrace from './components/ReasoningTrace';
import DiagnosticQuiz from './components/DiagnosticQuiz';
import TimeSavings from './components/TimeSavings';
import PeerComparison from './components/PeerComparison';
import { analyzeStreaming, analyzeDocuments } from './utils/api';

const TABS = [
  { id: 'overview', label: 'Gap Analysis' },
  { id: 'pathway', label: 'Learning Pathway' },
  { id: 'reasoning', label: 'Reasoning Trace' },
  { id: 'diagnostic', label: 'Diagnostic Quiz' },
];

export default function App() {
  const [status, setStatus] = useState('idle');
  const [statusMessage, setStatusMessage] = useState('');
  const [statusDetail, setStatusDetail] = useState('');
  const [currentStep, setCurrentStep] = useState(0);
  const [totalSteps, setTotalSteps] = useState(5);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');

  // Partial streaming data (shown progressively before full results)
  const [streamData, setStreamData] = useState({
    resumeParsed: null,
    jdParsed: null,
    gapComputed: null,
    pathwayReady: null,
  });

  const handleStreamEvent = useCallback((event, data) => {
    switch (event) {
      case 'status':
        setStatusMessage(data.message);
        setStatusDetail(data.detail || '');
        setCurrentStep(data.step);
        setTotalSteps(data.total_steps);
        break;

      case 'resume_parsed':
        setStreamData(prev => ({ ...prev, resumeParsed: data }));
        break;

      case 'jd_parsed':
        setStreamData(prev => ({ ...prev, jdParsed: data }));
        break;

      case 'gap_computed':
        setStreamData(prev => ({ ...prev, gapComputed: data }));
        break;

      case 'pathway_ready':
        setStreamData(prev => ({ ...prev, pathwayReady: data }));
        break;

      case 'complete':
        setResult(data);
        setStatus('done');
        setActiveTab('overview');
        break;

      case 'error':
        setError(data.message);
        setStatus('error');
        break;
    }
  }, []);

  const handleAnalyze = useCallback(async (resumeInput, jdInput) => {
    setStatus('analyzing');
    setError(null);
    setResult(null);
    setStreamData({ resumeParsed: null, jdParsed: null, gapComputed: null, pathwayReady: null });
    setCurrentStep(0);

    try {
      if (resumeInput instanceof File && jdInput instanceof File) {
        // File uploads use non-streaming endpoint
        setStatusMessage('Uploading and analyzing documents...');
        setStatusDetail('Processing PDF files');
        const data = await analyzeDocuments(resumeInput, jdInput);
        setResult(data);
        setStatus('done');
        setActiveTab('overview');
      } else {
        // Text input uses streaming endpoint
        await analyzeStreaming(resumeInput, jdInput, handleStreamEvent);
      }
    } catch (err) {
      console.error('Analysis failed:', err);
      setError(err.response?.data?.detail || err.message || 'Analysis failed');
      setStatus('error');
    }
  }, [handleStreamEvent]);

  const handleDemoMode = useCallback(async () => {
    const demoResume = `SENIOR ACCOUNTANT
Summary: Senior Accounting Professional with 8 years of experience in financial reporting, general ledger accounting, and budget management. CPA certified.

Experience:
Senior Accountant, ABC Corp (2019 - Present)
- Prepare quarterly and annual financial statements for 12 business units
- Reconcile balance sheet accounts including cash, fixed assets, and equity
- Coordinate external audit process with Deloitte
- Managed $50M budget and construction loan activity
- Led implementation of new ERP system (SAP) for the accounting department
- Trained 4 junior accountants on GAAP compliance procedures

Staff Accountant, XYZ Inc (2016 - 2019)
- Performed monthly closing cycle and financial statement preparation
- Managed accounts payable and receivable processing
- Prepared sales tax returns and assisted with year-end audit
- Used QuickBooks and Excel for financial reporting

Education: Bachelor of Business Administration: Accounting, State University, 2016

Skills: Financial Reporting, GAAP, General Ledger, Account Reconciliation, Budgeting, Excel, QuickBooks, SAP, Tax Preparation, Audit Support, Team Leadership`;

    const demoJD = `FINANCE MANAGER

Department: Corporate Finance
Reports to: VP of Finance

Role Overview:
We are seeking an experienced Finance Manager to oversee financial planning, analysis, and reporting for our growing organization. The ideal candidate will lead a team of accountants and drive strategic financial decisions.

Required Skills and Qualifications:
- Essential: Advanced Financial Analysis and Modeling (expert level)
- Essential: Financial Planning and Forecasting (demonstrated experience)
- Essential: Team Leadership and Management (managing 5+ direct reports)
- Essential: ERP Systems (SAP or Oracle, advanced proficiency)
- Essential: GAAP/IFRS Compliance (deep expertise)
- Preferred: Strategic Planning and Business Development
- Preferred: Data Analytics and Visualization (Tableau, Power BI)
- Preferred: Risk Management and Internal Controls
- Nice to have: Python or SQL for financial automation
- Nice to have: M&A Due Diligence experience

Responsibilities:
- Lead financial planning, budgeting, and forecasting processes
- Prepare executive-level financial reports and board presentations
- Manage and develop a team of 6 accounting professionals
- Drive process improvements and automation initiatives
- Ensure regulatory compliance and internal controls
- Partner with business units on strategic financial decisions`;

    await handleAnalyze(demoResume, demoJD);
  }, [handleAnalyze]);

  return (
    <div className="min-h-screen bg-midnight">
      {/* Header */}
      <header className="border-b border-gray-800 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center">
              <span className="text-midnight font-bold text-sm">AO</span>
            </div>
            <div>
              <h1 className="text-lg font-semibold text-white tracking-tight">
                Adaptive Onboarding Engine
              </h1>
              <p className="text-xs text-gray-500">AI-Driven Personalized Training Pathways</p>
            </div>
          </div>
          {status === 'idle' && (
            <button
              onClick={handleDemoMode}
              className="text-xs px-3 py-1.5 rounded-md bg-surface-2 text-gray-400 hover:text-accent hover:bg-surface-3 transition-all border border-gray-700 hover:border-accent/30"
            >
              Run Demo
            </button>
          )}
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6">
        {/* Upload / Status Phase */}
        {status !== 'done' && (
          <div className="mb-8">
            {status === 'idle' && <UploadPanel onAnalyze={handleAnalyze} />}
            {status === 'analyzing' && (
              <StatusBar
                message={statusMessage}
                detail={statusDetail}
                currentStep={currentStep}
                totalSteps={totalSteps}
                streamData={streamData}
              />
            )}
            {status === 'error' && (
              <div className="glass-card p-6 text-center">
                <p className="text-danger font-medium mb-2">Analysis Failed</p>
                <p className="text-sm text-gray-400 mb-4">{error}</p>
                <button
                  onClick={() => setStatus('idle')}
                  className="px-4 py-2 bg-surface-3 rounded-lg text-sm hover:bg-gray-600 transition"
                >
                  Try Again
                </button>
              </div>
            )}
          </div>
        )}

        {/* Results */}
        {status === 'done' && result && (
          <>
            {/* Top Summary Bar */}
            <div className="glass-card p-4 mb-6 flex items-center justify-between flex-wrap gap-4">
              <div className="flex items-center gap-6">
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wider">Candidate</p>
                  <p className="text-white font-medium">{result.parsed_resume.candidate_name}</p>
                </div>
                <div className="w-px h-8 bg-gray-700" />
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wider">Target Role</p>
                  <p className="text-white font-medium">{result.parsed_jd.job_title}</p>
                </div>
                <div className="w-px h-8 bg-gray-700" />
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wider">Readiness</p>
                  <p className={`font-bold text-lg ${
                    result.gap_analysis.overall_readiness_score >= 70 ? 'text-accent' :
                    result.gap_analysis.overall_readiness_score >= 40 ? 'text-warning' : 'text-danger'
                  }`}>
                    {result.gap_analysis.overall_readiness_score}%
                  </p>
                </div>
              </div>
              <button
                onClick={() => { setStatus('idle'); setResult(null); }}
                className="text-xs px-3 py-1.5 rounded-md bg-surface-3 text-gray-400 hover:text-white transition border border-gray-700"
              >
                New Analysis
              </button>
            </div>

            <TimeSavings gapAnalysis={result.gap_analysis} pathway={result.learning_pathway} />

            {/* Tab Navigation */}
            <div className="flex gap-1 mb-6 bg-surface rounded-lg p-1 w-fit">
              {TABS.map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
                    activeTab === tab.id
                      ? 'bg-surface-3 text-accent shadow-sm'
                      : 'text-gray-400 hover:text-gray-200'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Tab Content */}
            <div className="min-h-[500px]">
              {activeTab === 'overview' && (
                <div className="space-y-6">
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <SkillRadar
                      resumeSkills={result.parsed_resume.extracted_skills}
                      jdSkills={result.parsed_jd.required_skills}
                      gaps={result.gap_analysis.skill_gaps}
                      matched={result.gap_analysis.matched_skills}
                    />
                    <GapAnalysis gapAnalysis={result.gap_analysis} />
                  </div>
                  {result.gap_analysis.peer_comparison && (
                    <PeerComparison peerData={result.gap_analysis.peer_comparison} />
                  )}
                </div>
              )}
              {activeTab === 'pathway' && (
                <PathwayTimeline pathway={result.learning_pathway} />
              )}
              {activeTab === 'reasoning' && (
                <ReasoningTrace
                  trace={result.learning_pathway.reasoning_trace}
                  gaps={result.gap_analysis.skill_gaps}
                />
              )}
              {activeTab === 'diagnostic' && (
                <DiagnosticQuiz
                  assessment={result.diagnostic_assessment}
                  gaps={result.gap_analysis.skill_gaps}
                />
              )}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
