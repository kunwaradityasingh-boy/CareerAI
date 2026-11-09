import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/useAuth";
import { getStudentProfile } from "../../services/studentProfileService";
import { getResumeHistory } from "../../services/resumeService";

const modules = [
  {
    number: "01",
    title: "Resume Analyzer",
    description: "Scan your resume against ATS algorithms, identify missing keywords, and get AI recommendations.",
    badge: "⚡ Fully Functional",
    path: "/resume-analyzer",
    actionLabel: "Launch Analyzer →",
    active: true,
  },
  {
    number: "02",
    title: "Skill Gap Analysis",
    description: "Compare your technical proficiencies with real job market requirements for your target role.",
    badge: "🎯 Available",
    path: "/skill-gap",
    actionLabel: "View Skill Gap →",
    active: true,
  },
  {
    number: "03",
    title: "Career Roadmap",
    description: "Follow a step-by-step milestone progression from foundational CS to placement readiness.",
    badge: "🗺️ Available",
    path: "/roadmap",
    actionLabel: "Open Roadmap →",
    active: true,
  },
  {
    number: "04",
    title: "Placement Preparation",
    description: "Prepare for online assessments, technical coding rounds, and behavioral interview questions.",
    badge: "Coming soon",
    path: "/roadmap",
    actionLabel: "Explore Prep Steps →",
    active: false,
  },
];

function Dashboard() {
  const { user, token, logout } = useAuth();
  const navigate = useNavigate();

  const [profile, setProfile] = useState(null);
  const [profileLoading, setProfileLoading] = useState(Boolean(token));
  const [profileError, setProfileError] = useState("");
  const [latestResume, setLatestResume] = useState(null);

  useEffect(() => {
    let isMounted = true;

    if (!token) return;

    async function loadData() {
      try {
        setProfileLoading(true);
        setProfileError("");

        const [profileData, resumeHistory] = await Promise.allSettled([
          getStudentProfile(token),
          getResumeHistory(token),
        ]);

        if (!isMounted) return;

        if (profileData.status === "fulfilled") {
          setProfile(profileData.value);
        } else if (profileData.reason?.response?.status === 401) {
          logout();
          navigate("/", { replace: true });
          return;
        }

        if (resumeHistory.status === "fulfilled" && resumeHistory.value?.length > 0) {
          setLatestResume(resumeHistory.value[0]);
        }
      } catch {
        if (isMounted) {
          setProfileError("Unable to load some dashboard details. Please try again.");
        }
      } finally {
        if (isMounted) {
          setProfileLoading(false);
        }
      }
    }

    loadData();

    return () => {
      isMounted = false;
    };
  }, [token, logout, navigate]);

  const firstName = user?.name?.trim().split(/\s+/)[0] || "Student";

  return (
    <div className="dashboard-page-content">
      {/* Welcome Hero Card */}
      <section className="welcome-section">
        <div>
          <span className="section-kicker">YOUR CAREER WORKSPACE</span>
          <h1>Welcome back, {firstName}.</h1>
          <p>
            Your career journey starts with knowing where you stand. Take the next step
            towards placement readiness with CareerAI tools.
          </p>
        </div>

        <div className="welcome-date">CAREERAI STUDENT PORTAL</div>
      </section>

      {/* Quick Stat Cards Row */}
      <section className="stats-cards-grid">
        <div className="stat-card" onClick={() => navigate("/profile")}>
          <div className="stat-card-icon">👤</div>
          <div className="stat-card-info">
            <span className="stat-card-label">Profile Status</span>
            <strong>{profile ? "Profile Completed" : "Incomplete Profile"}</strong>
            <span className="stat-card-link">
              {profile ? `${profile.target_role || "Role set"} · Edit →` : "Complete Profile →"}
            </span>
          </div>
        </div>

        <div className="stat-card" onClick={() => navigate("/resume-analyzer")}>
          <div className="stat-card-icon">⚡</div>
          <div className="stat-card-info">
            <span className="stat-card-label">Latest ATS Score</span>
            <strong>
              {latestResume ? `${latestResume.overall_score}/100 Score` : "No Resume Scanned"}
            </strong>
            <span className="stat-card-link">
              {latestResume ? "View Latest Report →" : "Scan Your Resume Now →"}
            </span>
          </div>
        </div>

        <div className="stat-card" onClick={() => navigate("/skill-gap")}>
          <div className="stat-card-icon">🎯</div>
          <div className="stat-card-info">
            <span className="stat-card-label">Skill Gap Analysis</span>
            <strong>
              {profile?.technical_skills?.length
                ? `${profile.technical_skills.length} Skills Listed`
                : "Add Skills"}
            </strong>
            <span className="stat-card-link">Check Missing Skills →</span>
          </div>
        </div>

        <div className="stat-card" onClick={() => navigate("/roadmap")}>
          <div className="stat-card-icon">🗺️</div>
          <div className="stat-card-info">
            <span className="stat-card-label">Career Roadmap</span>
            <strong>Placement Pathway</strong>
            <span className="stat-card-link">Track Milestones →</span>
          </div>
        </div>
      </section>

      {/* Student Profile Overview Card */}
      <section className="student-details-card">
        <div className="section-heading">
          <div>
            <span className="section-kicker">ACADEMIC & CAREER PROFILE</span>
            <h2>Your Student Profile</h2>
            <p>Your saved academic information, target role, and technical skills.</p>
          </div>

          <button
            type="button"
            className="profile-edit-button"
            onClick={() => navigate("/profile")}
          >
            {profile ? "Edit Profile" : "Complete Profile"}
          </button>
        </div>

        {profileLoading ? (
          <p className="loading-text">Loading your profile...</p>
        ) : profileError ? (
          <p role="alert" className="text-red-500">{profileError}</p>
        ) : profile ? (
          <div className="student-details-grid">
            <div>
              <span>College / University</span>
              <strong>{profile.college_name || "Not added"}</strong>
            </div>

            <div>
              <span>Degree</span>
              <strong>{profile.degree || "Not added"}</strong>
            </div>

            <div>
              <span>Branch</span>
              <strong>{profile.branch || "Not added"}</strong>
            </div>

            <div>
              <span>Graduation Year</span>
              <strong>{profile.graduation_year || "Not added"}</strong>
            </div>

            <div>
              <span>Target Job Role</span>
              <strong>{profile.target_role || "Not added"}</strong>
            </div>

            <div>
              <span>Preferred Industry</span>
              <strong>{profile.preferred_industry || "Not added"}</strong>
            </div>

            <div className="full-width-detail">
              <span>Technical Skills</span>
              <strong>
                {profile.technical_skills?.join(", ") || "Not added"}
              </strong>
            </div>
          </div>
        ) : (
          <div className="empty-profile-banner">
            <p>Your student profile has not been created yet.</p>
            <button
              type="button"
              className="profile-edit-button mt-2"
              onClick={() => navigate("/profile")}
            >
              Complete Profile Now
            </button>
          </div>
        )}
      </section>

      {/* Dedicated Tools & Modules Section */}
      <section className="modules-section" id="modules">
        <div className="section-heading">
          <div>
            <span className="section-kicker">YOUR TOOLKIT</span>
            <h2>Career Development Tools</h2>
            <p>Dedicated tools to help you analyze, upskill, and prepare for interviews.</p>
          </div>

          <span className="module-count">04 MODULES</span>
        </div>

        <div className="module-grid">
          {modules.map((module) => (
            <article
              className={`module-card ${module.active ? "interactive" : ""}`}
              key={module.number}
              onClick={() => navigate(module.path)}
            >
              <div className="module-card-top">
                <span className="module-number">{module.number}</span>
                <span className={`coming-soon ${module.active ? "badge-live" : ""}`}>
                  {module.badge}
                </span>
              </div>

              <h3>{module.title}</h3>
              <p>{module.description}</p>

              <div className="module-card-footer">
                <span className="action-text">{module.actionLabel}</span>
                <span>↗</span>
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

export default Dashboard;
