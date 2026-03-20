import React from 'react';

const STEPS = [
  { id: 1, label: 'Parsing resume', icon: '📄' },
  { id: 2, label: 'Analyzing job description', icon: '💼' },
  { id: 3, label: 'Computing skill gaps', icon: '📊' },
  { id: 4, label: 'Generating pathway', icon: '🗺️' },
  { id: 5, label: 'Creating diagnostic', icon: '✅' },
];

export default function StatusBar({ message, detail, currentStep, totalSteps, streamData }) {
  const progress = (currentStep / totalSteps) * 100;

  return (
    <div className="space-y-4">
      {/* Main status card */}
      <div className="glass-card p-6">
        <div className="flex items-center gap-4 mb-4">
          <div className="pulse-glow w-12 h-12 rounded-full bg-surface-2 border border-accent/30 flex items-center justify-center flex-shrink-0">
            <svg className="w-6 h-6 text-accent animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
          </div>
          <div className="flex-1">
            <p className="text-accent font-medium">{message || 'Processing...'}</p>
            {detail && <p className="text-xs text-gray-500 mt-0.5">{detail}</p>}
          </div>
          <span className="text-sm text-gray-500 font-mono">{currentStep}/{totalSteps}</span>
        </div>

        {/* Progress bar */}
        <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-accent rounded-full transition-all duration-700 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* Step indicators */}
        <div className="mt-4 flex justify-between">
          {STEPS.map(step => {
            const isDone = currentStep > step.id;
            const isActive = currentStep === step.id;
            return (
              <div key={step.id} className="flex flex-col items-center gap-1">
                <span className={`text-lg transition-all ${
                  isDone ? 'opacity-100 scale-110' :
                  isActive ? 'opacity-100 animate-bounce' : 'opacity-30'
                }`}>
                  {isDone ? '✓' : step.icon}
                </span>
                <span className={`text-[10px] ${
                  isActive ? 'text-accent' : isDone ? 'text-gray-400' : 'text-gray-600'
                }`}>
                  {step.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Progressive data cards — appear as each step completes */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {streamData.resumeParsed && (
          <div className="glass-card p-4 animate-fadeIn">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-sm">📄</span>
              <span className="text-xs text-gray-500 uppercase tracking-wider">Resume Parsed</span>
            </div>
            <p className="text-white font-medium text-sm">{streamData.resumeParsed.candidate_name}</p>
            <p className="text-xs text-gray-400 mt-1">
              {streamData.resumeParsed.skills_count} skills extracted
              {streamData.resumeParsed.domain && ` · ${streamData.resumeParsed.domain}`}
            </p>
            {streamData.resumeParsed.top_skills && (
              <div className="mt-2 flex flex-wrap gap-1">
                {streamData.resumeParsed.top_skills.map((s, i) => (
                  <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-accent/10 text-accent">
                    {s.name}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        {streamData.jdParsed && (
          <div className="glass-card p-4 animate-fadeIn">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-sm">💼</span>
              <span className="text-xs text-gray-500 uppercase tracking-wider">JD Analyzed</span>
            </div>
            <p className="text-white font-medium text-sm">{streamData.jdParsed.job_title}</p>
            <p className="text-xs text-gray-400 mt-1">
              {streamData.jdParsed.required_skills_count} required skills
              · {streamData.jdParsed.essential_count} essential
            </p>
          </div>
        )}

        {streamData.gapComputed && (
          <div className="glass-card p-4 animate-fadeIn">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-sm">📊</span>
              <span className="text-xs text-gray-500 uppercase tracking-wider">Gap Analysis</span>
            </div>
            <div className="flex items-center gap-3">
              <span className={`text-2xl font-bold ${
                streamData.gapComputed.readiness_score >= 70 ? 'text-accent' :
                streamData.gapComputed.readiness_score >= 40 ? 'text-warning' : 'text-danger'
              }`}>
                {streamData.gapComputed.readiness_score}%
              </span>
              <div className="text-xs text-gray-400">
                <p>{streamData.gapComputed.gaps_count} gaps · {streamData.gapComputed.matched_count} matched</p>
                {streamData.gapComputed.peer_domain && (
                  <p className="text-info">
                    {streamData.gapComputed.peer_percentile}th percentile in {streamData.gapComputed.peer_domain}
                  </p>
                )}
              </div>
            </div>
            {streamData.gapComputed.top_gaps && (
              <div className="mt-2 space-y-1">
                {streamData.gapComputed.top_gaps.slice(0, 3).map((g, i) => (
                  <div key={i} className="flex items-center justify-between text-xs">
                    <span className="text-gray-400">{g.skill}</span>
                    <span className="text-danger font-mono">-{g.gap.toFixed(0)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {streamData.pathwayReady && (
          <div className="glass-card p-4 animate-fadeIn">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-sm">🗺️</span>
              <span className="text-xs text-gray-500 uppercase tracking-wider">Pathway Built</span>
            </div>
            <p className="text-white font-medium text-sm">
              {streamData.pathwayReady.total_courses} courses
            </p>
            <p className="text-xs text-gray-400 mt-1">
              {streamData.pathwayReady.total_hours}h total
              · {streamData.pathwayReady.phases_count} phases
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
