import React from 'react';

export default function PeerComparison({ peerData }) {
  if (!peerData || !peerData.domain || peerData.domain === 'Unknown') {
    return null;
  }

  const {
    domain,
    total_resumes_analyzed,
    skills_checked,
    skills_matched,
    percentile,
    skill_coverage,
    common_gaps,
    strengths,
  } = peerData;

  return (
    <div className="glass-card p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-white font-semibold">Peer Cohort Comparison</h3>
          <p className="text-xs text-gray-500 mt-0.5">
            Benchmarked against {total_resumes_analyzed.toLocaleString()} resumes
            · Domain: {domain}
          </p>
        </div>
        {percentile !== null && (
          <div className="text-center">
            <p className={`text-2xl font-bold ${
              percentile >= 70 ? 'text-accent' :
              percentile >= 40 ? 'text-warning' : 'text-danger'
            }`}>
              {percentile}%
            </p>
            <p className="text-[10px] text-gray-500">percentile</p>
          </div>
        )}
      </div>

      {/* Skill Coverage Bars */}
      <div className="mb-5">
        <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">
          Domain Skill Coverage ({skills_matched}/{skills_checked} matched)
        </p>
        <div className="space-y-1.5 max-h-[220px] overflow-y-auto pr-1">
          {skill_coverage && skill_coverage.map((s, i) => (
            <div key={i} className="flex items-center gap-2">
              <span className={`w-3 h-3 rounded-sm flex items-center justify-center text-[8px] flex-shrink-0 ${
                s.candidate_has
                  ? 'bg-accent/20 text-accent'
                  : 'bg-gray-800 text-gray-600'
              }`}>
                {s.candidate_has ? '✓' : '✗'}
              </span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-0.5">
                  <span className={`text-xs truncate ${
                    s.candidate_has ? 'text-gray-200' : 'text-gray-500'
                  }`}>
                    {s.skill}
                  </span>
                  <span className="text-[10px] text-gray-600 ml-2 flex-shrink-0">
                    {s.domain_frequency}%
                  </span>
                </div>
                <div className="h-1 bg-gray-800 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${
                      s.candidate_has ? 'bg-accent/60' : 'bg-gray-700'
                    }`}
                    style={{ width: `${s.domain_frequency}%` }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Strengths */}
      {strengths && strengths.length > 0 && (
        <div className="mb-4">
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">
            🏆 Standout Skills (rare in this domain)
          </p>
          <div className="space-y-1.5">
            {strengths.map((s, i) => (
              <div key={i} className="flex items-center gap-2 bg-accent/5 rounded-lg px-3 py-1.5">
                <span className="text-accent text-xs font-medium">{s.skill}</span>
                <span className="text-[10px] text-gray-500">— {s.insight}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Common Gaps */}
      {common_gaps && common_gaps.length > 0 && (
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">
            ⚠️ Common Skills You're Missing
          </p>
          <div className="space-y-1.5">
            {common_gaps.map((s, i) => (
              <div key={i} className="flex items-center gap-2 bg-danger/5 rounded-lg px-3 py-1.5">
                <span className="text-danger text-xs font-medium">{s.skill}</span>
                <span className="text-[10px] text-gray-500">— {s.insight}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Data Source Footer */}
      <div className="mt-4 pt-3 border-t border-gray-800">
        <p className="text-[10px] text-gray-600 font-mono">
          Data source: Skill co-occurrence analysis of {total_resumes_analyzed.toLocaleString()} professional resumes
          across 24 job categories (Kaggle Resume Dataset)
        </p>
      </div>
    </div>
  );
}
