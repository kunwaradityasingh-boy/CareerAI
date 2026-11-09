import { useEffect, useState, useRef } from "react";
import { useAuth } from "../context/useAuth";
import {
  analyzeResumeText,
  uploadResumeFile,
  getResumeHistory,
  deleteResumeAnalysis,
} from "../../services/resumeService";

const POPULAR_ROLES = [
  "Full Stack Developer",
  "Frontend Developer",
  "Backend Developer",
  "Data Scientist / AI Engineer",
  "DevOps / Cloud Engineer",
  "Mobile App Developer",
  "Cyber Security Analyst",
];

function ResumeAnalyzer() {
  const { token } = useAuth();

  // Mode: "upload" | "paste" | "history"
  const [inputMode, setInputMode] = useState("upload");
  const [targetRole, setTargetRole] = useState("Full Stack Developer");
  const [customRole, setCustomRole] = useState("");
  const [jobDescription, setJobDescription] = useState("");

  // File upload state
  const [selectedFile, setSelectedFile] = useState(null);
  const [pastedText, setPastedText] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef(null);

  // Analysis result & loading
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisStep, setAnalysisStep] = useState("");
  const [currentReport, setCurrentReport] = useState(null);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  // History state
  const [history, setHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  const activeRole = targetRole === "Other" ? customRole.trim() || "Software Engineer" : targetRole;

  async function loadHistory() {
    if (!token) return;
    try {
      setLoadingHistory(true);
      const data = await getResumeHistory(token);
      setHistory(data);
    } catch {
      // Silently handle history load failure
    } finally {
      setLoadingHistory(false);
    }
  }

  useEffect(() => {
    let ignore = false;
    async function fetchInitial() {
      try {
        const data = await getResumeHistory(token);
        if (!ignore) {
          setHistory(data);
        }
      } catch {
        // Silently handle
      }
    }

    if (token) {
      fetchInitial();
    }

    return () => {
      ignore = true;
    };
  }, [token]);

  function handleFileDrop(e) {
    e.preventDefault();
    setDragOver(false);
    const files = e.dataTransfer.files;
    if (files && files[0]) {
      validateAndSetFile(files[0]);
    }
  }

  function handleFileSelect(e) {
    const files = e.target.files;
    if (files && files[0]) {
      validateAndSetFile(files[0]);
    }
  }

  function validateAndSetFile(file) {
    setError("");
    const lowerName = file.name.toLowerCase();
    if (!lowerName.endsWith(".pdf") && !lowerName.endsWith(".txt")) {
      setError("Please select a PDF (.pdf) or text (.txt) resume file.");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setError("File size must be under 5MB.");
      return;
    }
    setSelectedFile(file);
  }

  async function handleAnalyze(e) {
    e.preventDefault();
    setError("");
    setSuccessMsg("");

    if (inputMode === "upload") {
      if (!selectedFile) {
        setError("Please choose a resume file (PDF or TXT) to analyze.");
        return;
      }
    } else {
      if (!pastedText.trim() || pastedText.trim().length < 50) {
        setError("Please paste your resume text (at least 50 characters).");
        return;
      }
    }

    setAnalyzing(true);
    setAnalysisStep("Uploading document...");

    try {
      let report;
      if (inputMode === "upload") {
        setAnalysisStep("Parsing document & formatting...");
        const formData = new FormData();
        formData.append("file", selectedFile);
        formData.append("target_role", activeRole);
        if (jobDescription.trim()) {
          formData.append("job_description", jobDescription.trim());
        }
        report = await uploadResumeFile(formData, token);
      } else {
        setAnalysisStep("Analyzing ATS keywords & structure...");
        report = await analyzeResumeText(
          {
            resume_text: pastedText.trim(),
            target_role: activeRole,
            file_name: "Pasted Resume",
            job_description: jobDescription.trim() || undefined,
          },
          token,
        );
      }

      setAnalysisStep("Computing impact & scoring...");
      setCurrentReport(report);
      setSuccessMsg("Resume analyzed successfully!");
      loadHistory();
    } catch (err) {
      const msg = err.response?.data?.detail || "Failed to analyze resume. Please try again.";
      setError(typeof msg === "string" ? msg : JSON.stringify(msg));
    } finally {
      setAnalyzing(false);
      setAnalysisStep("");
    }
  }

  async function handleDeleteHistoryItem(id, e) {
    e.stopPropagation();
    try {
      await deleteResumeAnalysis(id, token);
      setHistory((prev) => prev.filter((item) => item.id !== id));
      if (currentReport?.id === id) {
        setCurrentReport(null);
      }
    } catch {
      setError("Could not delete report.");
    }
  }

  function getScoreColor(score) {
    if (score >= 80) return "score-high";
    if (score >= 65) return "score-medium";
    return "score-low";
  }

  function getScoreBadge(score) {
    if (score >= 85) return { text: "Top Tier (Interview Ready)", class: "badge-green" };
    if (score >= 70) return { text: "Competitive (Minor Tweaks Needed)", class: "badge-blue" };
    return { text: "Needs Optimization", class: "badge-amber" };
  }

  return (
    <div className="resume-analyzer-shell">
      {/* Page Header */}
      <div className="page-header">
        <div className="page-header-text">
          <span className="section-kicker">AI RESUME INTELLIGENCE</span>
          <h1>Resume Analyzer & ATS Optimizer</h1>
          <p>
            Scan your resume against ATS algorithms, discover critical missing keywords,
            and get actionable improvements tailored to your target job role.
          </p>
        </div>

        {currentReport && (
          <button
            type="button"
            className="secondary-btn"
            onClick={() => setCurrentReport(null)}
          >
            ← Upload Another Resume
          </button>
        )}
      </div>

      {error && (
        <div className="alert-box alert-error" role="alert">
          <span>⚠️</span>
          <div>{error}</div>
        </div>
      )}

      {successMsg && (
        <div className="alert-box alert-success" role="status">
          <span>✓</span>
          <div>{successMsg}</div>
        </div>
      )}

      {/* Main View: Either Form or Detailed Report */}
      {!currentReport ? (
        <div className="analyzer-grid">
          {/* Left Column: Form */}
          <div className="analyzer-card">
            {/* Input Mode Selector */}
            <div className="card-tabs">
              <button
                type="button"
                className={`card-tab ${inputMode === "upload" ? "active" : ""}`}
                onClick={() => setInputMode("upload")}
              >
                📄 Upload Resume (PDF / TXT)
              </button>
              <button
                type="button"
                className={`card-tab ${inputMode === "paste" ? "active" : ""}`}
                onClick={() => setInputMode("paste")}
              >
                📝 Paste Resume Text
              </button>
            </div>

            <form onSubmit={handleAnalyze} className="analyzer-form">
              {/* Target Role Selection */}
              <div className="form-group">
                <label htmlFor="target_role">
                  Target Job Role <span className="req">*</span>
                </label>
                <div className="role-chips">
                  {POPULAR_ROLES.map((role) => (
                    <button
                      key={role}
                      type="button"
                      className={`chip ${targetRole === role ? "active" : ""}`}
                      onClick={() => setTargetRole(role)}
                    >
                      {role}
                    </button>
                  ))}
                  <button
                    type="button"
                    className={`chip ${targetRole === "Other" ? "active" : ""}`}
                    onClick={() => setTargetRole("Other")}
                  >
                    Custom Role...
                  </button>
                </div>

                {targetRole === "Other" && (
                  <input
                    type="text"
                    id="custom_role"
                    className="form-input mt-2"
                    placeholder="e.g. Solutions Architect, Product Manager"
                    value={customRole}
                    onChange={(e) => setCustomRole(e.target.value)}
                    required
                  />
                )}
              </div>

              {/* Upload Zone */}
              {inputMode === "upload" ? (
                <div className="form-group">
                  <label>Resume File (PDF or TXT)</label>
                  <div
                    className={`dropzone ${dragOver ? "dragover" : ""} ${selectedFile ? "has-file" : ""}`}
                    onDragOver={(e) => {
                      e.preventDefault();
                      setDragOver(true);
                    }}
                    onDragLeave={() => setDragOver(false)}
                    onDrop={handleFileDrop}
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".pdf,.txt"
                      className="hidden-file-input"
                      onChange={handleFileSelect}
                    />
                    <div className="dropzone-icon">📥</div>
                    {selectedFile ? (
                      <div className="file-info">
                        <strong>{selectedFile.name}</strong>
                        <span>({(selectedFile.size / 1024).toFixed(1)} KB)</span>
                        <p className="click-replace">Click to choose a different file</p>
                      </div>
                    ) : (
                      <div className="dropzone-text">
                        <strong>Drop your resume PDF here, or browse</strong>
                        <span>Supports PDF & TXT up to 5MB</span>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="form-group">
                  <label htmlFor="pasted_text">
                    Resume Content <span className="req">*</span>
                  </label>
                  <textarea
                    id="pasted_text"
                    className="form-textarea"
                    rows={8}
                    placeholder="Paste the plain text of your resume here..."
                    value={pastedText}
                    onChange={(e) => setPastedText(e.target.value)}
                  />
                </div>
              )}

              {/* Optional Job Description */}
              <div className="form-group">
                <label htmlFor="job_description">
                  Target Job Description (Optional)
                  <span className="label-hint">Paste JD to evaluate job-specific keyword match</span>
                </label>
                <textarea
                  id="job_description"
                  className="form-textarea"
                  rows={3}
                  placeholder="Paste the job description or required qualifications..."
                  value={jobDescription}
                  onChange={(e) => setJobDescription(e.target.value)}
                />
              </div>

              <button
                type="submit"
                className="submit-btn"
                disabled={analyzing}
              >
                {analyzing ? (
                  <span>⏳ {analysisStep || "Analyzing Resume..."}</span>
                ) : (
                  <span>⚡ Scan & Analyze Resume →</span>
                )}
              </button>
            </form>
          </div>

          {/* Right Column: History & Tips */}
          <div className="side-column">
            {/* Quick Tips Card */}
            <div className="info-card">
              <h3>💡 ATS Resume Best Practices</h3>
              <ul className="tips-list">
                <li>
                  <strong>Clean Standard Formatting:</strong> Use clear headings like "Experience", "Skills", and "Education".
                </li>
                <li>
                  <strong>Impact & Metrics:</strong> Quantify your achievements (e.g. "Reduced query latency by 35%").
                </li>
                <li>
                  <strong>Keyword Matching:</strong> Ensure the exact technical skills mentioned in the job description appear naturally.
                </li>
                <li>
                  <strong>Action Verbs:</strong> Begin bullet points with strong verbs (Architected, Engineered, Optimized).
                </li>
              </ul>
            </div>

            {/* Past Analyses */}
            <div className="info-card history-card">
              <div className="card-header-row">
                <h3>🕒 Past Analyses ({history.length})</h3>
                {loadingHistory && <span className="loading-spinner">...</span>}
              </div>

              {history.length === 0 ? (
                <p className="empty-text">No previous resume scans yet. Upload your resume to start!</p>
              ) : (
                <div className="history-list">
                  {history.map((item) => (
                    <div
                      key={item.id}
                      className="history-item"
                      onClick={async () => {
                        try {
                          const full = await getResumeAnalysis(item.id, token);
                          setCurrentReport(full);
                        } catch {
                          setError("Failed to open report.");
                        }
                      }}
                    >
                      <div className="history-item-top">
                        <strong className="truncate">{item.file_name}</strong>
                        <span className={`history-score ${getScoreColor(item.overall_score)}`}>
                          {item.overall_score}/100
                        </span>
                      </div>
                      <div className="history-item-sub">
                        <span>{item.target_role}</span>
                        <span className="history-date">
                          {new Date(item.created_at).toLocaleDateString()}
                        </span>
                      </div>
                      <button
                        type="button"
                        className="delete-history-btn"
                        onClick={(e) => handleDeleteHistoryItem(item.id, e)}
                        title="Delete this analysis"
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      ) : (
        /* Detailed Analysis Report */
        <div className="report-shell">
          {/* Top Score Banner */}
          <div className="report-banner">
            <div className="score-gauge-wrap">
              <div className={`score-circle ${getScoreColor(currentReport.overall_score)}`}>
                <span className="score-number">{currentReport.overall_score}</span>
                <span className="score-max">/ 100</span>
              </div>
            </div>

            <div className="report-summary-text">
              <div className="report-badge-row">
                <span className={`score-badge ${getScoreBadge(currentReport.overall_score).class}`}>
                  {getScoreBadge(currentReport.overall_score).text}
                </span>
                <span className="role-tag">Role: {currentReport.target_role}</span>
              </div>
              <h2>Resume Evaluation Summary</h2>
              <p>
                File: <strong>{currentReport.file_name}</strong> · Evaluated on{" "}
                {new Date(currentReport.created_at).toLocaleString()}
              </p>
            </div>
          </div>

          {/* 4 Core Pillars Breakdown */}
          <div className="pillars-grid">
            <div className="pillar-card">
              <div className="pillar-header">
                <span>ATS Compatibility</span>
                <strong>{currentReport.ats_compatibility}%</strong>
              </div>
              <div className="progress-track">
                <div
                  className="progress-fill"
                  style={{ width: `${currentReport.ats_compatibility}%` }}
                />
              </div>
              <p className="pillar-desc">Layout cleanliness, standard contact details & readability.</p>
            </div>

            <div className="pillar-card">
              <div className="pillar-header">
                <span>Skills Alignment</span>
                <strong>{currentReport.skills_score}%</strong>
              </div>
              <div className="progress-track">
                <div
                  className="progress-fill"
                  style={{ width: `${currentReport.skills_score}%` }}
                />
              </div>
              <p className="pillar-desc">Coverage of core & advanced skills for {currentReport.target_role}.</p>
            </div>

            <div className="pillar-card">
              <div className="pillar-header">
                <span>Impact & Metrics</span>
                <strong>{currentReport.impact_score}%</strong>
              </div>
              <div className="progress-track">
                <div
                  className="progress-fill"
                  style={{ width: `${currentReport.impact_score}%` }}
                />
              </div>
              <p className="pillar-desc">Quantified achievements, numbers, and action verbs.</p>
            </div>

            <div className="pillar-card">
              <div className="pillar-header">
                <span>Structure & Sections</span>
                <strong>{currentReport.structure_score}%</strong>
              </div>
              <div className="progress-track">
                <div
                  className="progress-fill"
                  style={{ width: `${currentReport.structure_score}%` }}
                />
              </div>
              <p className="pillar-desc">Presence of essential sections (Experience, Skills, Education).</p>
            </div>
          </div>

          {/* Keywords Breakdown */}
          <div className="keywords-section">
            <div className="keyword-card">
              <h3>
                <span className="icon-green">✓</span> Identified Skills ({currentReport.found_keywords?.length || 0})
              </h3>
              <div className="chips-wrap">
                {currentReport.found_keywords?.length > 0 ? (
                  currentReport.found_keywords.map((kw) => (
                    <span key={kw} className="skill-chip found">
                      ✓ {kw}
                    </span>
                  ))
                ) : (
                  <p className="text-muted">No explicit role-matching keywords detected.</p>
                )}
              </div>
            </div>

            <div className="keyword-card">
              <h3>
                <span className="icon-amber">⚡</span> Recommended Skills to Add ({currentReport.missing_keywords?.length || 0})
              </h3>
              <div className="chips-wrap">
                {currentReport.missing_keywords?.length > 0 ? (
                  currentReport.missing_keywords.map((kw) => (
                    <span key={kw} className="skill-chip missing" title="Recommended to add to your resume">
                      + {kw}
                    </span>
                  ))
                ) : (
                  <p className="text-muted">Excellent! All core skills are present in your resume.</p>
                )}
              </div>
            </div>
          </div>

          {/* Strengths & Actionable Recommendations */}
          <div className="feedback-grid">
            <div className="feedback-card strengths-card">
              <h3>🌟 Key Strengths</h3>
              <ul>
                {currentReport.strengths?.map((str, idx) => (
                  <li key={idx}>
                    <span className="bullet-check">✓</span>
                    <span>{str}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="feedback-card recommendations-card">
              <h3>🚀 Actionable AI Recommendations</h3>
              <ul>
                {currentReport.recommendations?.map((rec, idx) => (
                  <li key={idx}>
                    <span className="bullet-rec">→</span>
                    <span>{rec}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Section by Section Feedback */}
          {currentReport.section_feedback && (
            <div className="section-feedback-card">
              <h3>📋 Section-by-Section Review</h3>
              <div className="section-feedback-grid">
                <div className="sec-box">
                  <strong>Professional Summary</strong>
                  <p>{currentReport.section_feedback.summary || "Looks good."}</p>
                </div>
                <div className="sec-box">
                  <strong>Technical Skills</strong>
                  <p>{currentReport.section_feedback.skills || "Looks good."}</p>
                </div>
                <div className="sec-box">
                  <strong>Work Experience & Projects</strong>
                  <p>{currentReport.section_feedback.experience_projects || "Looks good."}</p>
                </div>
                <div className="sec-box">
                  <strong>Education & Credentials</strong>
                  <p>{currentReport.section_feedback.education || "Looks good."}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default ResumeAnalyzer;
