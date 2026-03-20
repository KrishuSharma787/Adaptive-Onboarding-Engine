import axios from 'axios';

const API_BASE = '/api';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 120000,
});

/**
 * Streaming analysis via Server-Sent Events.
 * Calls onEvent for each step, allowing progressive UI updates.
 * 
 * Events emitted:
 *   status         - { step, total_steps, message, detail }
 *   resume_parsed  - { candidate_name, skills_count, top_skills }
 *   jd_parsed      - { job_title, required_skills_count }
 *   gap_computed   - { readiness_score, gaps_count, matched_count, top_gaps }
 *   pathway_ready  - { total_courses, total_hours, phases_count }
 *   complete       - Full FullAnalysisResponse object
 *   error          - { message }
 */
export async function analyzeStreaming(resumeText, jdText, onEvent) {
  const response = await fetch('/api/analyze/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      resume_text: resumeText,
      job_description_text: jdText,
    }),
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // Parse SSE events from buffer
    const lines = buffer.split('\n');
    buffer = lines.pop() || ''; // Keep incomplete last line

    let currentEvent = null;
    for (const line of lines) {
      if (line.startsWith('event: ')) {
        currentEvent = line.slice(7).trim();
      } else if (line.startsWith('data: ') && currentEvent) {
        try {
          const data = JSON.parse(line.slice(6));
          onEvent(currentEvent, data);
        } catch (e) {
          console.warn('Failed to parse SSE data:', line);
        }
        currentEvent = null;
      }
    }
  }
}

/**
 * Non-streaming file upload analysis (for PDF uploads).
 */
export async function analyzeDocuments(resumeFile, jdFile) {
  const formData = new FormData();
  formData.append('resume', resumeFile);
  formData.append('job_description', jdFile);

  const response = await api.post('/analyze', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}

/**
 * Non-streaming text analysis (fallback).
 */
export async function analyzeText(resumeText, jdText) {
  const response = await api.post('/analyze/text', {
    resume_text: resumeText,
    job_description_text: jdText,
  });
  return response.data;
}

export async function submitDiagnostic(answers) {
  const response = await api.post('/diagnostic/submit', answers);
  return response.data;
}

export async function searchCatalog(query, topK = 5) {
  const response = await api.get('/catalog/search', {
    params: { q: query, top_k: topK },
  });
  return response.data;
}

export async function healthCheck() {
  const response = await api.get('/health');
  return response.data;
}

export default api;
