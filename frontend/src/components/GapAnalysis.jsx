import React, { useState } from 'react';

export default function GapAnalysis({ gapAnalysis }) {
  const { skill_gaps, matched_skills } = gapAnalysis;
  const [expandedGap, setExpandedGap] = useState(null);

  return (
    <div className="glass-card p-6">
      <h3 className="text-white font-semibold mb-1">Skill Gap Breakdown</h3>
      <p className="text-xs text-gray-500 mb-4">
        {skill_gaps.length} gaps identified · {matched_skills.length} skills met/exceeded
      </p>

      {/* Gap List */}
      <div className="space-y-2 mb-6 max-h-[320px] overflow-y-auto pr-1">
        {skill_gaps.map((gap, i) => (
          <div
            key={i}
            className="bg-surface-2 rounded-lg p-3 cursor-pointer hover:bg-surface-3 transition"
            onClick={() => setExpandedGap(expandedGap === i ? null : i)}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${
                  gap.importance_weight >= 0.9 ? 'bg-danger' :
                  gap.importance_weight >= 0.6 ? 'bg-warning' : 'bg-info'
                }`} />
                <span className="text-sm text-gray-200">{gap.skill_name}</span>
              </div>
              <span className="text-xs font-mono text-gray-400">
                {gap.candidate_score} → {gap.target_score}
              </span>
            </div>

            {/* Gap bar */}
            <div className="relative h-2 bg-gray-800 rounded-full overflow-hidden">
              <div
                className="absolute left-0 top-0 h-full rounded-full bg-accent/40"
                style={{ width: `${gap.candidate_score}%` }}
              />
              <div
                className="absolute top-0 h-full rounded-full"
                style={{
                  left: `${gap.candidate_score}%`,
                  width: `${gap.target_score - gap.candidate_score}%`,
                  background: 'repeating-linear-gradient(90deg, rgba(239,68,68,0.3), rgba(239,68,68,0.3) 4px, transparent 4px, transparent 8px)',
                }}
              />
              <div
                className="absolute top-0 h-full w-0.5 bg-info"
                style={{ left: `${gap.target_score}%` }}
              />
            </div>

            <div className="flex justify-between mt-1">
              <span className="text-[10px] text-gray-500">
                Weight: {gap.importance_weight}x · Gap: {gap.gap_score.toFixed(1)}
              </span>
              {gap.onet_node && (
                <span className="text-[10px] text-gray-600">
                  O*NET: {gap.onet_node}
                </span>
              )}
            </div>

            {/* Expanded reasoning */}
            {expandedGap === i && (
              <div className="mt-3 pt-3 border-t border-gray-700">
                <p className="text-xs text-gray-400 leading-relaxed">{gap.reasoning}</p>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Matched Skills */}
      {matched_skills.length > 0 && (
        <div className="border-t border-gray-800 pt-4">
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">
            ✓ Skills Already Met ({matched_skills.length})
          </p>
          <div className="flex flex-wrap gap-1.5">
            {matched_skills.map((skill, i) => (
              <span
                key={i}
                className="text-[11px] px-2 py-0.5 rounded-full bg-accent/10 text-accent border border-accent/20"
              >
                {skill}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
