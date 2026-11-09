import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/useAuth";
import { getStudentProfile } from "../../services/studentProfileService";

const modules = [
  {
    number: "01",
    title: "Resume Analyzer",
    description: "Review your resume and identify areas for improvement.",
  },
  {
    number: "02",
    title: "Skill Gap Analysis",
    description: "Understand which skills you need for your target role.",
  },
  {
    number: "03",
    title: "Career Roadmap",
    description: "Build a structured path towards your career goals.",
  },
  {
    number: "04",
    title: "Placement Preparation",
    description: "Prepare for aptitude, coding and interviews.",
  },
];

function Dashboard() {
  const { user, token, logout } = useAuth();
  const navigate = useNavigate();

  const [profile, setProfile] = useState(null);
  const [profileLoading, setProfileLoading] = useState(true);
  const [profileError, setProfileError] = useState("");

  useEffect(() => {
    let isMounted = true;

    async function loadProfile() {
      try {
        setProfileLoading(true);
        setProfileError("");

        const data = await getStudentProfile(token);

        if (isMounted) {
          setProfile(data);
        }
      } catch (error) {
        if (!isMounted) return;

        if (error.response?.status === 401) {
          logout();
          navigate("/", { replace: true });
          return;
        }

        if (error.response?.status === 404) {
          setProfile(null);
        } else {
          setProfileError(
            "Unable to load your student profile. Please try again.",
          );
        }
      } finally {
        if (isMounted) {
          setProfileLoading(false);
        }
      }
    }

    if (token) {
      loadProfile();
    } else {
      setProfileLoading(false);
    }

    return () => {
      isMounted = false;
    };
  }, [token, logout, navigate]);

  function handleLogout() {
    logout();
    navigate("/", { replace: true });
  }

  const firstName = user?.name?.trim().split(/\s+/)[0] || "Student";

  return (
    <div className="dashboard-shell">
      <aside className="dashboard-sidebar">
        <div className="dashboard-brand">
          <span className="dashboard-brand-mark">C</span>
          <span>CareerAI</span>
        </div>

        <div className="sidebar-label">WORKSPACE</div>

        <nav className="sidebar-nav">
          <a href="#overview" className="sidebar-link active">
            <span>⌂</span>
            Overview
          </a>

          <a href="#modules" className="sidebar-link">
            <span>▤</span>
            Career tools
          </a>

          <button
            type="button"
            className="sidebar-link"
            onClick={() => navigate("/profile")}
          >
            <span>◉</span>
            My profile
          </button>
        </nav>

        <div className="sidebar-bottom">
          <div className="sidebar-user">
            <div className="user-avatar">
              {firstName.charAt(0).toUpperCase()}
            </div>

            <div className="sidebar-user-info">
              <strong>{user?.name || "Student"}</strong>
              <span>Student account</span>
            </div>
          </div>

          <button
            type="button"
            className="logout-button"
            onClick={handleLogout}
          >
            <span>↪</span>
            Sign out
          </button>
        </div>
      </aside>

      <main className="dashboard-main">
        <header className="dashboard-topbar">
          <div>
            <span className="topbar-label">STUDENT WORKSPACE</span>
            <p>Career development</p>
          </div>

          <div className="topbar-account">
            <span className="account-status"></span>
            Account active
          </div>
        </header>

        <div className="dashboard-content" id="overview">
          <section className="welcome-section">
            <div>
              <span className="section-kicker">YOUR CAREER WORKSPACE</span>
              <h1>Welcome back, {firstName}.</h1>
              <p>
                Your career journey starts with knowing where you stand. Take
                the next step at your own pace.
              </p>
            </div>

            <div className="welcome-date">CAREERAI STUDENT PORTAL</div>
          </section>

          <section className="profile-summary">
            <div className="profile-avatar">
              {firstName.charAt(0).toUpperCase()}
            </div>

            <div className="profile-details">
              <span className="section-kicker">YOUR ACCOUNT</span>
              <h2>{user?.name || "Student"}</h2>
              <p>{user?.email || "Email unavailable"}</p>
            </div>

            <span className="verified-label">Registered student</span>
          </section>

          <section className="student-details-card">
            <div className="section-heading">
              <div>
                <span className="section-kicker">
                  ACADEMIC & CAREER DETAILS
                </span>
                <h2>Your student profile</h2>
                <p>Your saved academic information and career preferences.</p>
              </div>

              <button
                type="button"
                className="profile-edit-button"
                onClick={() => navigate("/profile")}
              >
                Edit profile
              </button>
            </div>

            {profileLoading ? (
              <p>Loading your profile...</p>
            ) : profileError ? (
              <p role="alert">{profileError}</p>
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

                <div>
                  <span>Technical Skills</span>
                  <strong>
                    {profile.technical_skills?.join(", ") || "Not added"}
                  </strong>
                </div>

                <div>
                  <span>Career Interests</span>
                  <strong>
                    {profile.career_interests?.join(", ") || "Not added"}
                  </strong>
                </div>
              </div>
            ) : (
              <div>
                <p>Your student profile has not been created yet.</p>

                <button
                  type="button"
                  className="profile-edit-button"
                  onClick={() => navigate("/profile")}
                >
                  Complete profile
                </button>
              </div>
            )}
          </section>

          <section className="modules-section" id="modules">
            <div className="section-heading">
              <div>
                <span className="section-kicker">YOUR TOOLKIT</span>
                <h2>Career development tools</h2>
                <p>
                  Tools to help you understand and prepare for your next step.
                </p>
              </div>

              <span className="module-count">04 MODULES</span>
            </div>

            <div className="module-grid">
              {modules.map((module) => (
                <article className="module-card" key={module.number}>
                  <div className="module-card-top">
                    <span className="module-number">{module.number}</span>
                    <span className="coming-soon">Coming soon</span>
                  </div>

                  <h3>{module.title}</h3>
                  <p>{module.description}</p>

                  <div className="module-card-footer">
                    <span>In development</span>
                    <span>↗</span>
                  </div>
                </article>
              ))}
            </div>
          </section>

          <footer className="dashboard-footer">
            CareerAI · Career & Placement Intelligence
          </footer>
        </div>
      </main>
    </div>
  );
}

export default Dashboard;
