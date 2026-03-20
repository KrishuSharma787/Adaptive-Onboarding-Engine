import React from 'react';
import {
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  Radar, Legend, ResponsiveContainer, Tooltip,
} from 'recharts';

const PROFICIENCY_SCORES = {
  mentioned: 15, used: 35, applied: 55, demonstrated: 75, led: 95,
};

export default function SkillRadar({ resumeSkills, jdSkills, gaps, matched }) {
  // Build radar data: top skills (gaps + some matched)
  const radarSkills = [
    ...gaps.slice(0, 6).map(g => g.skill_name),
    ...matched.slice(0, Math.max(0, 8 - Math.min(gaps.length, 6))),
  ].slice(0, 8);

  const radarData = radarSkills.map(skillName => {
    const gap = gaps.find(g => g.skill_name === skillName);
    const resumeSkill = resumeSkills.find(
      s => s.skill_name.toLowerCase() === skillName.toLowerCase()
    );
    const jdSkill = jdSkills.find(
      s => s.skill_name.toLowerCase() === skillName.toLowerCase()
    );

    return {
      skill: skillName.length > 18 ? skillName.slice(0, 16) + '…' : skillName,
      fullName: skillName,
      candidate: Math.min(100, Math.max(0, gap ? gap.candidate_score : (resumeSkill ? PROFICIENCY_SCORES[resumeSkill.proficiency] || 50 : 50))),
      target: Math.min(100, Math.max(0, gap ? gap.target_score : (jdSkill ? PROFICIENCY_SCORES[jdSkill.required_level] || 75 : 75))),
    };
  });

  // Skill depth detail table
  const topSkills = resumeSkills.slice(0, 10);

  return (
    <div className="glass-card p-6">
      <h3 className="text-white font-semibold mb-1">Skill Depth Matrix</h3>
      <p className="text-xs text-gray-500 mb-4">Candidate proficiency vs. role requirements (0–100 scale)</p>

      {radarData.length > 0 ? (
        <ResponsiveContainer width="100%" height={280}>
          <RadarChart data={radarData} cx="50%" cy="50%" outerRadius="70%">
            <PolarGrid stroke="#1f2937" />
            <PolarAngleAxis
              dataKey="skill"
              tick={{ fill: '#9ca3af', fontSize: 10 }}
            />
            <PolarRadiusAxis
              angle={30}
              domain={[0, 100]}
              tick={{ fill: '#6b7280', fontSize: 9 }}
              tickCount={5}
              axisLine={false}
            />
            <Radar
              name="Target"
              dataKey="target"
              stroke="#38bdf8"
              fill="#38bdf8"
              fillOpacity={0.1}
              strokeWidth={2}
            />
            <Radar
              name="Candidate"
              dataKey="candidate"
              stroke="#06d6a0"
              fill="#06d6a0"
              fillOpacity={0.15}
              strokeWidth={2}
            />
            <Tooltip
              contentStyle={{
                background: '#1a2332',
                border: '1px solid #374151',
                borderRadius: '8px',
                fontSize: '12px',
              }}
              formatter={(value, name) => [`${value}/100`, name]}
            />
            <Legend
              wrapperStyle={{ fontSize: '11px', color: '#9ca3af' }}
            />
          </RadarChart>
        </ResponsiveContainer>
      ) : (
        <div className="h-[280px] flex items-center justify-center text-gray-500 text-sm">
          No skill data available for radar visualization
        </div>
      )}

      {/* Skill Detail Table */}
      <div className="mt-4 border-t border-gray-800 pt-4">
        <p className="text-xs text-gray-500 uppercase tracking-wider mb-3">Extracted Skills (Top 10)</p>
        <div className="space-y-2">
          {topSkills.map((skill, i) => (
            <div key={i} className="flex items-center gap-3">
              <div className="flex-1 min-w-0">
                <p className="text-sm text-gray-200 truncate">{skill.skill_name}</p>
              </div>
              <div className="flex items-center gap-2">
                <ProficiencyBadge level={skill.proficiency} />
                <div className="w-20 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${PROFICIENCY_SCORES[skill.proficiency] || 0}%`,
                      backgroundColor: getScoreColor(PROFICIENCY_SCORES[skill.proficiency] || 0),
                    }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ProficiencyBadge({ level }) {
  const colors = {
    mentioned: 'bg-gray-700 text-gray-400',
    used: 'bg-blue-900/40 text-blue-300',
    applied: 'bg-cyan-900/40 text-cyan-300',
    demonstrated: 'bg-accent/15 text-accent',
    led: 'bg-yellow-900/40 text-yellow-300',
  };
  return (
    <span className={`text-[10px] px-1.5 py-0.5 rounded ${colors[level] || 'bg-gray-700 text-gray-400'}`}>
      {level}
    </span>
  );
}

function getScoreColor(score) {
  if (score >= 75) return '#06d6a0';
  if (score >= 55) return '#38bdf8';
  if (score >= 35) return '#fbbf24';
  return '#ef4444';
}
