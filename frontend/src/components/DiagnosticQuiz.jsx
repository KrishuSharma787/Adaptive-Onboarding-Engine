import React, { useState } from 'react';
import { submitDiagnostic } from '../utils/api';

export default function DiagnosticQuiz({ assessment, gaps }) {
  const [currentQ, setCurrentQ] = useState(0);
  const [answers, setAnswers] = useState({});
  const [submitted, setSubmitted] = useState(false);
  const [results, setResults] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  if (!assessment || !assessment.questions || assessment.questions.length === 0) {
    return (
      <div className="glass-card p-8 text-center">
        <p className="text-gray-400">No diagnostic assessment available.</p>
        <p className="text-xs text-gray-600 mt-2">Diagnostics are generated when skill gaps are identified.</p>
      </div>
    );
  }

  const questions = assessment.questions;
  const question = questions[currentQ];
  const totalQuestions = questions.length;
  const answeredCount = Object.keys(answers).length;

  const handleSelect = (optionIdx) => {
    setAnswers(prev => ({ ...prev, [question.question_id]: optionIdx }));
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      const payload = Object.entries(answers).map(([qid, idx]) => ({
        question_id: qid,
        selected_answer_index: idx,
      }));
      const res = await submitDiagnostic(payload);
      setResults(res.results);
      setSubmitted(true);
    } catch (err) {
      // Compute results locally as fallback
      const localResults = computeLocalResults(questions, answers, gaps);
      setResults(localResults);
      setSubmitted(true);
    }
    setSubmitting(false);
  };

  if (submitted && results) {
    return <DiagnosticResults results={results} questions={questions} answers={answers} />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="glass-card p-6">
        <h3 className="text-white font-semibold mb-1">Diagnostic Assessment</h3>
        <p className="text-sm text-gray-400">
          {totalQuestions} questions targeting your top skill gaps.
          Results are evaluated using Bayesian Knowledge Tracing to estimate true mastery.
        </p>
        <div className="mt-3 flex items-center gap-2">
          <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-accent rounded-full transition-all"
              style={{ width: `${(answeredCount / totalQuestions) * 100}%` }}
            />
          </div>
          <span className="text-xs text-gray-500">{answeredCount}/{totalQuestions}</span>
        </div>
      </div>

      {/* Question Card */}
      <div className="glass-card p-6">
        <div className="flex items-center justify-between mb-4">
          <span className="text-xs px-2 py-1 rounded-full bg-info/10 text-info">
            {question.skill_being_tested}
          </span>
          <span className="text-xs text-gray-500">
            Question {currentQ + 1} of {totalQuestions}
          </span>
        </div>

        <p className="text-white font-medium mb-6 leading-relaxed">
          {question.question_text}
        </p>

        <div className="space-y-3">
          {question.options.map((option, idx) => {
            const isSelected = answers[question.question_id] === idx;
            return (
              <button
                key={idx}
                onClick={() => handleSelect(idx)}
                className={`w-full text-left p-4 rounded-lg border transition-all ${
                  isSelected
                    ? 'border-accent bg-accent/8 text-white'
                    : 'border-gray-700 bg-surface-2 text-gray-300 hover:border-gray-500'
                }`}
              >
                <div className="flex items-start gap-3">
                  <span className={`w-6 h-6 rounded-full border-2 flex items-center justify-center flex-shrink-0 text-xs ${
                    isSelected ? 'border-accent bg-accent text-midnight' : 'border-gray-600'
                  }`}>
                    {String.fromCharCode(65 + idx)}
                  </span>
                  <span className="text-sm">{option}</span>
                </div>
              </button>
            );
          })}
        </div>

        {/* Navigation */}
        <div className="mt-6 flex items-center justify-between">
          <button
            onClick={() => setCurrentQ(Math.max(0, currentQ - 1))}
            disabled={currentQ === 0}
            className="px-4 py-2 text-sm text-gray-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition"
          >
            ← Previous
          </button>

          <div className="flex gap-1">
            {questions.map((_, i) => (
              <button
                key={i}
                onClick={() => setCurrentQ(i)}
                className={`w-2.5 h-2.5 rounded-full transition ${
                  i === currentQ ? 'bg-accent' :
                  answers[questions[i].question_id] !== undefined ? 'bg-gray-500' : 'bg-gray-700'
                }`}
              />
            ))}
          </div>

          {currentQ < totalQuestions - 1 ? (
            <button
              onClick={() => setCurrentQ(currentQ + 1)}
              className="px-4 py-2 text-sm text-accent hover:text-white transition"
            >
              Next →
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={answeredCount < totalQuestions || submitting}
              className={`px-6 py-2 rounded-lg text-sm font-medium transition-all ${
                answeredCount >= totalQuestions
                  ? 'bg-accent text-midnight hover:shadow-lg'
                  : 'bg-gray-700 text-gray-500 cursor-not-allowed'
              }`}
            >
              {submitting ? 'Evaluating...' : 'Submit Assessment'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function DiagnosticResults({ results, questions, answers }) {
  return (
    <div className="space-y-6">
      <div className="glass-card p-6">
        <h3 className="text-white font-semibold mb-1">Diagnostic Results</h3>
        <p className="text-sm text-gray-400">
          Mastery estimated via Bayesian Knowledge Tracing (BKT) model
        </p>
      </div>

      {/* Per-skill results */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {results.map((r, i) => (
          <div key={i} className="glass-card p-5">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-white font-medium text-sm">{r.skill_name}</h4>
              <span className={`text-sm font-bold ${
                r.estimated_mastery_probability >= 0.7 ? 'text-accent' :
                r.estimated_mastery_probability >= 0.4 ? 'text-warning' : 'text-danger'
              }`}>
                {(r.estimated_mastery_probability * 100).toFixed(0)}% mastery
              </span>
            </div>

            {/* Mastery bar */}
            <div className="h-2 bg-gray-800 rounded-full overflow-hidden mb-3">
              <div
                className="h-full rounded-full transition-all"
                style={{
                  width: `${r.estimated_mastery_probability * 100}%`,
                  backgroundColor: r.estimated_mastery_probability >= 0.7 ? '#06d6a0' :
                    r.estimated_mastery_probability >= 0.4 ? '#fbbf24' : '#ef4444',
                }}
              />
            </div>

            <div className="flex items-center justify-between text-xs text-gray-500 mb-3">
              <span>{r.correct_answers}/{r.questions_asked} correct</span>
              <span>Adjusted: {r.adjusted_proficiency}</span>
            </div>

            <p className="text-xs text-gray-400 leading-relaxed p-2 bg-surface-2 rounded">
              {r.pathway_adjustment}
            </p>
          </div>
        ))}
      </div>

      {/* Question Review */}
      <div className="glass-card p-6">
        <h4 className="text-white font-semibold mb-4 text-sm">Question Review</h4>
        <div className="space-y-3 max-h-[400px] overflow-y-auto">
          {questions.map((q, i) => {
            const selected = answers[q.question_id];
            const isCorrect = selected === q.correct_answer_index;
            return (
              <div key={i} className="bg-surface-2 rounded-lg p-3">
                <div className="flex items-start gap-2 mb-2">
                  <span className={`text-xs mt-0.5 ${isCorrect ? 'text-accent' : 'text-danger'}`}>
                    {isCorrect ? '✓' : '✗'}
                  </span>
                  <p className="text-sm text-gray-300">{q.question_text}</p>
                </div>
                {!isCorrect && (
                  <p className="text-xs text-gray-500 ml-5">
                    Correct: {q.options[q.correct_answer_index]} — {q.explanation}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function computeLocalResults(questions, answers, gaps) {
  // Group by skill
  const skillGroups = {};
  questions.forEach(q => {
    if (!skillGroups[q.skill_being_tested]) {
      skillGroups[q.skill_being_tested] = { questions: [], responses: [] };
    }
    skillGroups[q.skill_being_tested].questions.push(q);
    const selected = answers[q.question_id];
    skillGroups[q.skill_being_tested].responses.push(selected === q.correct_answer_index);
  });

  return Object.entries(skillGroups).map(([skill, data]) => {
    const correct = data.responses.filter(Boolean).length;
    const total = data.responses.length;

    // Simple BKT simulation
    let pKnow = 0.3;
    const pLearn = 0.1, pGuess = 0.2, pSlip = 0.1;
    for (const resp of data.responses) {
      const pCorrect = pKnow * (1 - pSlip) + (1 - pKnow) * pGuess;
      const pKnowGivenObs = resp
        ? (pKnow * (1 - pSlip)) / pCorrect
        : (pKnow * pSlip) / (1 - pCorrect);
      pKnow = pKnowGivenObs + (1 - pKnowGivenObs) * pLearn;
    }

    const proficiency = pKnow >= 0.85 ? 'demonstrated' :
      pKnow >= 0.65 ? 'applied' : pKnow >= 0.45 ? 'used' : 'mentioned';

    const gap = gaps.find(g => g.skill_name === skill);
    return {
      skill_name: skill,
      questions_asked: total,
      correct_answers: correct,
      estimated_mastery_probability: Math.round(pKnow * 1000) / 1000,
      adjusted_proficiency: proficiency,
      pathway_adjustment: pKnow >= 0.65
        ? `Diagnostic confirms competency in ${skill}. Consider skipping beginner modules.`
        : `Diagnostic suggests additional training needed in ${skill}. Foundational courses recommended.`,
    };
  });
}
