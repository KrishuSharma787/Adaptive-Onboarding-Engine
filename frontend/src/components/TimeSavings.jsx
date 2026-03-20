import React from 'react';

export default function TimeSavings({ gapAnalysis, pathway }) {
  const {
    generic_training_hours,
    skill_gaps,
    matched_skills,
  } = gapAnalysis;

  const personalizedHours = pathway.total_hours;
  const genericHours = generic_training_hours;
  const hoursDiff = genericHours - personalizedHours;
  const timeSavedPercent = genericHours > 0
    ? ((genericHours - personalizedHours) / genericHours) * 100
    : 0;
  const isSaving = timeSavedPercent > 0;
  const daysPersonalized = Math.ceil(personalizedHours / 2);
  const daysGeneric = Math.ceil(genericHours / 2);

  return (
    <div className={`glass-card p-5 mb-6 border ${isSaving ? 'border-accent/10' : 'border-warning/10'}`}>
      <div className="flex items-center gap-6 flex-wrap">
        {/* Main Metric */}
        <div className="flex items-center gap-3">
          <div className={`w-12 h-12 rounded-xl ${isSaving ? 'bg-accent/10' : 'bg-warning/10'} flex items-center justify-center`}>
            <span className="text-2xl">{isSaving ? '⚡' : '📋'}</span>
          </div>
          <div>
            {isSaving ? (
              <>
                <p className="text-2xl font-bold text-accent">{timeSavedPercent.toFixed(0)}%</p>
                <p className="text-xs text-gray-500">training time saved</p>
              </>
            ) : (
              <>
                <p className="text-2xl font-bold text-warning">Structured</p>
                <p className="text-xs text-gray-500">pathway optimized for skill gaps</p>
              </>
            )}
          </div>
        </div>

        <div className="w-px h-10 bg-gray-800 hidden sm:block" />

        {/* Stats */}
        <div className="flex gap-6 flex-wrap">
          <Stat
            label="Personalized Path"
            value={`${personalizedHours.toFixed(0)}h`}
            sub={`~${daysPersonalized} days at 2h/day · ${pathway.total_courses} courses`}
            highlight={isSaving}
          />
          <Stat
            label="Generic Onboarding"
            value={`${genericHours.toFixed(0)}h`}
            sub={`~${daysGeneric} days at 2h/day · all skills covered`}
            strikethrough={isSaving}
          />
          {isSaving ? (
            <Stat
              label="Hours Saved"
              value={`${hoursDiff.toFixed(0)}h`}
              sub={`${matched_skills.length} skills already met`}
            />
          ) : (
            <Stat
              label="Advantage"
              value="Better Fit"
              sub={`Right difficulty · correct order · ${matched_skills.length} skills skipped`}
            />
          )}
          <Stat
            label="Gaps to Bridge"
            value={skill_gaps.length.toString()}
            sub={`across ${pathway.phases.length} phases`}
          />
        </div>
      </div>

      {/* Explanation when no time saved */}
      {!isSaving && (
        <p className="text-xs text-gray-500 mt-3 pt-3 border-t border-gray-800">
          This candidate has significant skill gaps for the target role. The personalized pathway
          doesn't reduce total hours but ensures training starts at the right level, follows
          correct prerequisites, and skips the {matched_skills.length} skill{matched_skills.length !== 1 ? 's' : ''} already mastered.
        </p>
      )}
    </div>
  );
}

function Stat({ label, value, sub, highlight, strikethrough }) {
  return (
    <div>
      <p className="text-xs text-gray-500 mb-0.5">{label}</p>
      <p className={`text-lg font-bold ${
        highlight ? 'text-accent' : strikethrough ? 'text-gray-600 line-through' : 'text-white'
      }`}>
        {value}
      </p>
      <p className="text-[10px] text-gray-600">{sub}</p>
    </div>
  );
}
