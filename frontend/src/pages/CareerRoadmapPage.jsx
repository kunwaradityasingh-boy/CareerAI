import { useState } from "react";
import { useNavigate } from "react-router-dom";

const ROADMAP_STEPS = [
  {
    phase: "Phase 1",
    title: "Core CS & Algorithmic Foundations",
    duration: "Months 1 - 2",
    summary: "Build strong problem-solving ability and master version control.",
    items: [
      "Master Data Structures (Arrays, Linked Lists, Trees, Graphs, Hash Maps)",
      "Practice 50+ medium-level coding questions on platforms like LeetCode",
      "Understand Object-Oriented Programming (OOP) and Clean Code principles",
      "Master Git, branching workflows, pull requests, and GitHub",
    ],
  },
  {
    phase: "Phase 2",
    title: "Specialized Stack & Production Engineering",
    duration: "Months 3 - 4",
    summary: "Build scalable web applications and interact with production databases.",
    items: [
      "Build deep competence in your chosen language (Python / JavaScript / Java)",
      "Master modern frontend or backend frameworks (React, FastAPI, Node.js)",
      "Design normalized relational databases (PostgreSQL) and write complex queries",
      "Implement secure authentication (JWT, Password Hashing, Role-Based Access)",
    ],
  },
  {
    phase: "Phase 3",
    title: "Full-Stack Portfolio Projects & System Design",
    duration: "Months 5 - 6",
    summary: "Containerize apps, deploy to cloud infrastructure, and demonstrate architecture.",
    items: [
      "Build 2 end-to-end full-stack projects that solve realistic real-world problems",
      "Containerize your applications with Docker and Docker Compose",
      "Set up automated CI/CD pipelines (GitHub Actions) with automated testing",
      "Deploy to cloud environments (AWS / Render / Neon) with custom domains",
    ],
  },
  {
    phase: "Phase 4",
    title: "ATS Resume Optimization & Placement Sprint",
    duration: "Months 7+",
    summary: "Maximize interview conversion with ATS-tuned resumes and mock interview prep.",
    items: [
      "Scan and optimize your resume using the CareerAI Resume Analyzer (Aim for 85+ ATS score)",
      "Highlight measurable project impact (metrics, user counts, latency reductions)",
      "Prepare for behavioral interview questions using the STAR framework",
      "Conduct mock technical interviews and live coding rounds",
    ],
  },
];

function CareerRoadmapPage() {
  const navigate = useNavigate();
  const [completedItems, setCompletedItems] = useState(() => {
    try {
      const saved = localStorage.getItem("careerai_roadmap_completed");
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  function toggleItem(itemText) {
    setCompletedItems((prev) => {
      const next = prev.includes(itemText)
        ? prev.filter((i) => i !== itemText)
        : [...prev, itemText];
      try {
        localStorage.setItem("careerai_roadmap_completed", JSON.stringify(next));
      } catch {
        // Ignore storage errors
      }
      return next;
    });
  }

  const totalItems = ROADMAP_STEPS.reduce((acc, step) => acc + step.items.length, 0);
  const progressPercent = Math.round((completedItems.length / totalItems) * 100);

  return (
    <div className="roadmap-shell">
      <div className="page-header">
        <div className="page-header-text">
          <span className="section-kicker">STEP-BY-STEP PROGRESSION</span>
          <h1>Career & Placement Roadmap</h1>
          <p>
            Follow this structured, milestone-driven pathway designed to take you from foundational
            knowledge to placement-ready engineer.
          </p>
        </div>

        <button
          type="button"
          className="primary-btn"
          onClick={() => navigate("/resume-analyzer")}
        >
          ⚡ Scan Resume on CareerAI
        </button>
      </div>

      {/* Progress Overview Card */}
      <div className="roadmap-progress-card">
        <div className="roadmap-progress-top">
          <div>
            <h2>Your Roadmap Completion</h2>
            <p>{completedItems.length} of {totalItems} milestones completed</p>
          </div>
          <span className="progress-badge">{progressPercent}% Ready</span>
        </div>

        <div className="progress-track big-track">
          <div
            className="progress-fill"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>

      {/* Roadmap Timeline */}
      <div className="timeline-container">
        {ROADMAP_STEPS.map((step, idx) => (
          <div key={step.phase} className="timeline-phase-card">
            <div className="phase-marker">
              <span className="phase-number">{idx + 1}</span>
              <div className="phase-line" />
            </div>

            <div className="phase-content">
              <div className="phase-header">
                <div>
                  <span className="phase-tag">{step.phase} · {step.duration}</span>
                  <h3>{step.title}</h3>
                </div>
              </div>
              <p className="phase-summary">{step.summary}</p>

              <div className="phase-checklist">
                {step.items.map((item) => {
                  const isDone = completedItems.includes(item);
                  return (
                    <label
                      key={item}
                      className={`checklist-item ${isDone ? "completed" : ""}`}
                    >
                      <input
                        type="checkbox"
                        checked={isDone}
                        onChange={() => toggleItem(item)}
                      />
                      <span>{item}</span>
                    </label>
                  );
                })}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default CareerRoadmapPage;
