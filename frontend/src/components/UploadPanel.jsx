import React, { useState, useRef } from 'react';

export default function UploadPanel({ onAnalyze }) {
  const [resumeFile, setResumeFile] = useState(null);
  const [jdFile, setJdFile] = useState(null);
  const resumeRef = useRef(null);
  const jdRef = useRef(null);

  const handleSubmit = () => {
    if (resumeFile && jdFile) {
      onAnalyze(resumeFile, jdFile);
    }
  };

  return (
    <div className="glass-card p-8">
      <div className="text-center mb-8">
        <h2 className="text-2xl font-semibold text-white mb-2">
          Upload Documents
        </h2>
        <p className="text-gray-400 text-sm max-w-lg mx-auto">
          Upload a resume and a target job description. The engine will parse both,
          identify skill gaps, and generate a personalized training pathway.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        {/* Resume Upload */}
        <div
          className={`upload-zone ${resumeFile ? 'has-file' : ''}`}
          onClick={() => resumeRef.current?.click()}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            const file = e.dataTransfer.files[0];
            if (file) setResumeFile(file);
          }}
        >
          <input
            ref={resumeRef}
            type="file"
            accept=".pdf,.txt,.doc,.docx"
            className="hidden"
            onChange={(e) => setResumeFile(e.target.files[0])}
          />
          <div className="mb-3">
            <svg className="w-10 h-10 mx-auto text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
            </svg>
          </div>
          {resumeFile ? (
            <>
              <p className="text-accent font-medium text-sm">{resumeFile.name}</p>
              <p className="text-xs text-gray-500 mt-1">
                {(resumeFile.size / 1024).toFixed(1)} KB — Click to change
              </p>
            </>
          ) : (
            <>
              <p className="text-gray-300 font-medium text-sm">Resume</p>
              <p className="text-xs text-gray-500 mt-1">Drop PDF or TXT, or click to browse</p>
            </>
          )}
        </div>

        {/* JD Upload */}
        <div
          className={`upload-zone ${jdFile ? 'has-file' : ''}`}
          onClick={() => jdRef.current?.click()}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            const file = e.dataTransfer.files[0];
            if (file) setJdFile(file);
          }}
        >
          <input
            ref={jdRef}
            type="file"
            accept=".pdf,.txt,.doc,.docx"
            className="hidden"
            onChange={(e) => setJdFile(e.target.files[0])}
          />
          <div className="mb-3">
            <svg className="w-10 h-10 mx-auto text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20.25 14.15v4.25c0 1.094-.787 2.036-1.872 2.18-2.087.277-4.216.42-6.378.42s-4.291-.143-6.378-.42c-1.085-.144-1.872-1.086-1.872-2.18v-4.25m16.5 0a2.18 2.18 0 00.75-1.661V8.706c0-1.081-.768-2.015-1.837-2.175a48.114 48.114 0 00-3.413-.387m4.5 8.006c-.194.165-.42.295-.673.38A23.978 23.978 0 0112 15.75c-2.648 0-5.195-.429-7.577-1.22a2.016 2.016 0 01-.673-.38m0 0A2.18 2.18 0 013 12.489V8.706c0-1.081.768-2.015 1.837-2.175a48.111 48.111 0 013.413-.387m7.5 0V5.25A2.25 2.25 0 0013.5 3h-3a2.25 2.25 0 00-2.25 2.25v.894m7.5 0a48.667 48.667 0 00-7.5 0" />
            </svg>
          </div>
          {jdFile ? (
            <>
              <p className="text-accent font-medium text-sm">{jdFile.name}</p>
              <p className="text-xs text-gray-500 mt-1">
                {(jdFile.size / 1024).toFixed(1)} KB — Click to change
              </p>
            </>
          ) : (
            <>
              <p className="text-gray-300 font-medium text-sm">Job Description</p>
              <p className="text-xs text-gray-500 mt-1">Drop PDF or TXT, or click to browse</p>
            </>
          )}
        </div>
      </div>

      <div className="text-center">
        <button
          onClick={handleSubmit}
          disabled={!resumeFile || !jdFile}
          className={`px-8 py-3 rounded-lg font-medium text-sm transition-all ${
            resumeFile && jdFile
              ? 'bg-accent text-midnight hover:shadow-lg hover:shadow-accent/20 hover:-translate-y-0.5'
              : 'bg-gray-700 text-gray-500 cursor-not-allowed'
          }`}
        >
          Analyze & Generate Pathway
        </button>
      </div>
    </div>
  );
}
