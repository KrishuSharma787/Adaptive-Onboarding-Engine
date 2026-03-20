import React, { useState } from 'react';

const PHASE_COLORS = {
  1: { bg: 'bg-accent/10', border: 'border-accent/30', text: 'text-accent', dot: 'bg-accent' },
  2: { bg: 'bg-info/10', border: 'border-info/30', text: 'text-info', dot: 'bg-info' },
  3: { bg: 'bg-warning/10', border: 'border-warning/30', text: 'text-warning', dot: 'bg-warning' },
};

const PHASE_ICONS = {
  1: '🏗️',
  2: '⚡',
  3: '🎯',
};

export default function PathwayTimeline({ pathway }) {
  const [expandedPhase, setExpandedPhase] = useState(1);
  const [expandedCourse, setExpandedCourse] = useState(null);

  return (
    <div className="space-y-6">
      {/* Pathway Header */}
      <div className="glass-card p-6">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <h3 className="text-white font-semibold text-lg">Personalized Learning Pathway</h3>
            <p className="text-sm text-gray-400 mt-1">
              {pathway.total_courses} courses across {pathway.phases.length} phases · {pathway.total_hours}h total
            </p>
          </div>
          <div className="flex gap-4">
            {pathway.phases.map(phase => (
              <div key={phase.phase_number} className="text-center">
                <p className="text-xs text-gray-500">{phase.phase_name}</p>
                <p className={`text-lg font-bold ${PHASE_COLORS[phase.phase_number]?.text || 'text-white'}`}>
                  {phase.total_hours}h
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Phase Timeline */}
      <div className="relative">
        {/* Vertical connector line */}
        <div className="absolute left-6 top-0 bottom-0 w-px bg-gray-800" />

        {pathway.phases.map((phase, phaseIdx) => {
          const colors = PHASE_COLORS[phase.phase_number] || PHASE_COLORS[1];
          const isExpanded = expandedPhase === phase.phase_number;

          return (
            <div key={phase.phase_number} className="relative mb-6 last:mb-0">
              {/* Phase Header */}
              <div
                className={`ml-12 glass-card p-4 cursor-pointer transition-all hover:border-gray-600 ${
                  isExpanded ? 'border-l-2 ' + colors.border : ''
                }`}
                onClick={() => setExpandedPhase(isExpanded ? null : phase.phase_number)}
              >
                {/* Dot on timeline */}
                <div className={`absolute left-4 top-6 w-5 h-5 rounded-full ${colors.dot} flex items-center justify-center`}>
                  <span className="text-[10px]">{phase.phase_number}</span>
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-xl">{PHASE_ICONS[phase.phase_number] || '📘'}</span>
                    <div>
                      <h4 className={`font-semibold ${colors.text}`}>
                        Phase {phase.phase_number}: {phase.phase_name}
                      </h4>
                      <p className="text-xs text-gray-500">
                        {phase.courses.length} courses · {phase.total_hours}h
                      </p>
                    </div>
                  </div>
                  <svg
                    className={`w-4 h-4 text-gray-500 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                    fill="none" viewBox="0 0 24 24" stroke="currentColor"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </div>

              {/* Expanded Course List */}
              {isExpanded && (
                <div className="ml-12 mt-2 space-y-2">
                  {phase.courses.map((course, courseIdx) => {
                    const node = pathway.pathway_nodes.find(n => n.course_id === course.course_id);
                    const isNodeExpanded = expandedCourse === course.course_id;

                    return (
                      <div
                        key={course.course_id}
                        className={`bg-surface-2 rounded-lg p-4 border transition-all cursor-pointer ${
                          isNodeExpanded ? 'border-gray-600' : 'border-transparent hover:border-gray-700'
                        }`}
                        onClick={() => setExpandedCourse(isNodeExpanded ? null : course.course_id)}
                      >
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex items-start gap-3 flex-1 min-w-0">
                            <span className="text-xs text-gray-600 font-mono mt-0.5 flex-shrink-0">
                              {course.course_id}
                            </span>
                            <div className="min-w-0">
                              <p className="text-sm text-gray-200 font-medium">{course.title}</p>
                              <p className="text-xs text-gray-500 mt-0.5">
                                Targets: <span className={colors.text}>{course.skill}</span>
                              </p>
                            </div>
                          </div>
                          <div className="flex items-center gap-3 flex-shrink-0">
                            <span className="text-xs text-gray-400">{course.hours}h</span>
                            {course.confidence && (
                              <ConfidenceDot confidence={course.confidence} />
                            )}
                          </div>
                        </div>

                        {/* Expanded: Reasoning */}
                        {isNodeExpanded && node && (
                          <div className="mt-3 pt-3 border-t border-gray-700">
                            <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">
                              Why this was recommended
                            </p>
                            <p className="text-xs text-gray-400 leading-relaxed">{node.reasoning}</p>
                            <div className="mt-2 flex items-center gap-2">
                              <span className="text-[10px] font-mono text-gray-600">
                                Source: {node.source_catalog_id}
                              </span>
                              {node.prerequisites.length > 0 && (
                                <span className="text-[10px] text-gray-600">
                                  · Prereqs: {node.prerequisites.join(', ')}
                                </span>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ConfidenceDot({ confidence }) {
  const color = confidence >= 0.8 ? '#06d6a0' : confidence >= 0.5 ? '#fbbf24' : '#ef4444';
  return (
    <div className="flex items-center gap-1" title={`Confidence: ${(confidence * 100).toFixed(0)}%`}>
      <div className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
      <span className="text-[10px] text-gray-500">{(confidence * 100).toFixed(0)}%</span>
    </div>
  );
}
