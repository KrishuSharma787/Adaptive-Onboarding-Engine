import React, { useState } from 'react';

const TAG_MAP = {
  '[INIT]': 'init',
  '[ANALYSIS]': 'analysis',
  '[GAP]': 'gap',
  '[RETRIEVE]': 'retrieve',
  '[GRAPH]': 'analysis',
  '[WARNING]': 'warning',
  '[COMPLETE]': 'complete',
  '[SAVINGS]': 'savings',
};

function getTraceClass(line) {
  for (const [tag, cls] of Object.entries(TAG_MAP)) {
    if (line.includes(tag)) return cls;
  }
  return 'init';
}

function getTraceIcon(line) {
  if (line.includes('[INIT]')) return '▶';
  if (line.includes('[ANALYSIS]')) return '📊';
  if (line.includes('[GAP]')) return '⚠️';
  if (line.includes('[RETRIEVE]')) return '🔍';
  if (line.includes('[GRAPH]')) return '🔗';
  if (line.includes('[WARNING]')) return '⚡';
  if (line.includes('[COMPLETE]')) return '✅';
  if (line.includes('[SAVINGS]')) return '💰';
  return '•';
}

export default function ReasoningTrace({ trace, gaps }) {
  const [filter, setFilter] = useState('all');

  const filters = [
    { id: 'all', label: 'All Steps' },
    { id: 'gap', label: 'Gap Detection' },
    { id: 'retrieve', label: 'Course Retrieval' },
    { id: 'warning', label: 'Warnings' },
  ];

  const filteredTrace = filter === 'all'
    ? trace
    : trace.filter(line => getTraceClass(line) === filter);

  return (
    <div className="space-y-6">
      {/* Explanation Card */}
      <div className="glass-card p-6">
        <h3 className="text-white font-semibold mb-2">AI Reasoning Trace</h3>
        <p className="text-sm text-gray-400">
          Every recommendation is backed by an auditable reasoning chain.
          Each step shows exactly <em>why</em> a course was selected, which skill gap it targets,
          and its source citation in the course catalog.
        </p>
      </div>

      {/* Filter Bar */}
      <div className="flex gap-1 bg-surface rounded-lg p-1 w-fit">
        {filters.map(f => (
          <button
            key={f.id}
            onClick={() => setFilter(f.id)}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              filter === f.id
                ? 'bg-surface-3 text-white'
                : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Trace Log */}
      <div className="glass-card p-4">
        <div className="space-y-1.5 max-h-[600px] overflow-y-auto pr-2">
          {filteredTrace.map((line, i) => (
            <div
              key={i}
              className={`trace-line ${getTraceClass(line)} flex items-start gap-2`}
            >
              <span className="flex-shrink-0 mt-0.5 text-xs">{getTraceIcon(line)}</span>
              <span className="flex-1 break-words">{line}</span>
            </div>
          ))}
        </div>

        <div className="mt-4 pt-3 border-t border-gray-800 flex items-center justify-between">
          <span className="text-xs text-gray-600">
            {filteredTrace.length} of {trace.length} trace entries
          </span>
          <span className="text-[10px] text-gray-700 font-mono">
            All recommendations grounded in verified course catalog
          </span>
        </div>
      </div>

      {/* Gap Evidence Cards */}
      {gaps.length > 0 && (
        <div className="glass-card p-6">
          <h4 className="text-white font-semibold mb-3 text-sm">Gap Evidence Detail</h4>
          <div className="space-y-3 max-h-[400px] overflow-y-auto">
            {gaps.slice(0, 8).map((gap, i) => (
              <div key={i} className="bg-surface-2 rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-200 font-medium">{gap.skill_name}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono text-danger">
                      -{(gap.target_score - gap.candidate_score).toFixed(0)}pts
                    </span>
                    {gap.onet_node && (
                      <span className="text-[10px] px-1.5 py-0.5 bg-gray-800 rounded text-gray-500">
                        {gap.onet_node}
                      </span>
                    )}
                  </div>
                </div>
                <p className="text-xs text-gray-400 leading-relaxed">{gap.reasoning}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
