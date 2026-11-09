import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/useAuth";
import { getStudentProfile } from "../../services/studentProfileService";

const ROLE_SKILLS = {
  "Full Stack Developer": {
    core: ["JavaScript", "TypeScript", "React", "Node.js", "Python", "SQL", "Git", "REST APIs"],
    advanced: ["Docker", "PostgreSQL", "FastAPI", "MongoDB", "Redis", "Next.js", "Tailwind CSS", "CI/CD"],
    projectIdea: "Build a Full-Stack SaaS application with user authentication, PostgreSQL database, and automated CI/CD pipeline.",
  },
  "Frontend Developer": {
    core: ["JavaScript", "TypeScript", "React", "HTML5", "CSS3", "Tailwind CSS", "Git", "REST APIs"],
    advanced: ["Next.js", "Redux", "Jest", "GraphQL", "Accessibility", "Design Systems", "WebSockets"],
    projectIdea: "Build an interactive analytics dashboard with real-time charts, dark mode, and sub-second rendering.",
  },
  "Backend Developer": {
    core: ["Python", "Java", "SQL", "PostgreSQL", "FastAPI", "Django", "Git", "REST APIs"],
    advanced: ["Docker", "Kubernetes", "Redis", "Kafka", "Microservices", "AWS", "gRPC", "Query Optimization"],
    projectIdea: "Design a high-throughput event-driven microservice system with Redis caching and asynchronous queues.",
  },
  "Data Scientist / AI Engineer": {
    core: ["Python", "SQL", "Pandas", "NumPy", "Scikit-Learn", "Machine Learning", "Git"],
    advanced: ["PyTorch", "TensorFlow", "Deep Learning", "NLP", "LLMs", "Docker", "MLOps", "Hugging Face"],
    projectIdea: "Train and deploy a fine-tuned LLM or computer vision classifier with a FastAPI prediction endpoint.",
  },
  "DevOps / Cloud Engineer": {
    core: ["Linux", "Git", "Docker", "Kubernetes", "CI/CD", "AWS", "Bash", "Networking"],
    advanced: ["Terraform", "Ansible", "Prometheus", "Grafana", "GitHub Actions", "GCP", "Security"],
    projectIdea: "Provision cloud infrastructure using Terraform, deploy Kubernetes cluster, and configure Prometheus monitoring.",
  },
};

function SkillGapPage() {
  const { token } = useAuth();
  const navigate = useNavigate();

  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedRole, setSelectedRole] = useState("Full Stack Developer");

  useEffect(() => {
    let isMounted = true;
    async function loadData() {
      try {
        const data = await getStudentProfile(token);
        if (isMounted) {
          setProfile(data);
          if (data?.target_role && ROLE_SKILLS[data.target_role]) {
            setSelectedRole(data.target_role);
          }
        }
      } catch {
        // Handle 404 or missing profile
      } finally {
        if (isMounted) setLoading(false);
      }
    }
    if (token) loadData();
    return () => {
      isMounted = false;
    };
  }, [token]);

  const userSkills = (profile?.technical_skills || []).map((s) => s.toLowerCase());
  const roleData = ROLE_SKILLS[selectedRole] || ROLE_SKILLS["Full Stack Developer"];
  const allRequired = [...roleData.core, ...roleData.advanced];

  const matchedSkills = allRequired.filter((s) => userSkills.includes(s.toLowerCase()));
  const missingSkills = allRequired.filter((s) => !userSkills.includes(s.toLowerCase()));

  const matchPercent = Math.round((matchedSkills.length / allRequired.length) * 100);

  return (
    <div className="skill-gap-shell">
      <div className="page-header">
        <div className="page-header-text">
          <span className="section-kicker">CAREER INTELLIGENCE</span>
          <h1>Skill Gap Analysis</h1>
          <p>
            Evaluate your technical proficiencies against industry benchmarks for your dream role
            and identify the exact skills to learn next.
          </p>
        </div>

        <button
          type="button"
          className="secondary-btn"
          onClick={() => navigate("/profile")}
        >
          ✏️ Edit Profile Skills
        </button>
      </div>

      {/* Role Selection bar */}
      <div className="role-selection-card">
        <label htmlFor="role-select">Select Target Job Benchmark:</label>
        <div className="role-chips">
          {Object.keys(ROLE_SKILLS).map((role) => (
            <button
              key={role}
              type="button"
              className={`chip ${selectedRole === role ? "active" : ""}`}
              onClick={() => setSelectedRole(role)}
            >
              {role}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <p className="loading-text">Loading profile benchmark...</p>
      ) : (
        <div className="gap-analysis-grid">
          {/* Main Scorecard */}
          <div className="gap-scorecard">
            <div className="scorecard-top">
              <div>
                <h2>{selectedRole} Readiness</h2>
                <p>Based on your current student profile skills</p>
              </div>
              <div className="gauge-badge">
                <span className="gauge-number">{matchPercent}%</span>
                <span className="gauge-label">Match</span>
              </div>
            </div>

            <div className="progress-track big-track">
              <div
                className="progress-fill"
                style={{ width: `${matchPercent}%` }}
              />
            </div>

            <div className="stats-row">
              <div className="stat-item">
                <span>Acquired Skills</span>
                <strong>{matchedSkills.length} of {allRequired.length}</strong>
              </div>
              <div className="stat-item">
                <span>Skills to Learn</span>
                <strong className="text-amber">{missingSkills.length} gaps</strong>
              </div>
              <div className="stat-item">
                <span>Benchmark Role</span>
                <strong>{selectedRole}</strong>
              </div>
            </div>
          </div>

          {/* Breakdown: Acquired vs Missing */}
          <div className="skills-compare-grid">
            <div className="compare-card acquired-card">
              <h3>
                <span className="icon-green">✓</span> Skills You Already Have ({matchedSkills.length})
              </h3>
              <p className="subtext">These match the industry requirements for this role.</p>
              <div className="chips-wrap">
                {matchedSkills.length > 0 ? (
                  matchedSkills.map((s) => (
                    <span key={s} className="skill-chip found">
                      ✓ {s}
                    </span>
                  ))
                ) : (
                  <p className="empty-text">No matching skills found in your profile yet. Update your profile!</p>
                )}
              </div>
            </div>

            <div className="compare-card missing-card">
              <h3>
                <span className="icon-amber">⚡</span> Critical Skills You Need ({missingSkills.length})
              </h3>
              <p className="subtext">Prioritize learning these technologies to become placement ready.</p>
              <div className="chips-wrap">
                {missingSkills.map((s) => (
                  <span key={s} className="skill-chip missing">
                    + {s}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* Recommended Project to Close the Gap */}
          <div className="project-recommendation-card">
            <div className="project-rec-header">
              <span className="rec-badge">RECOMMENDED PORTFOLIO PROJECT</span>
              <h3>Capstone Project to bridge your skill gap</h3>
              <p>{roleData.projectIdea}</p>
            </div>
            <div className="project-tech-tags">
              <strong>Key Technologies Covered:</strong>
              <div className="chips-wrap mt-2">
                {missingSkills.slice(0, 4).map((tech) => (
                  <span key={tech} className="skill-chip found">
                    {tech}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default SkillGapPage;
