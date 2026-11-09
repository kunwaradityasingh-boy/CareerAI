import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/useAuth";
import {
  getStudentProfile,
  saveStudentProfile,
} from "../../services/studentProfileService";

const emptyProfile = {
  college_name: "",
  degree: "",
  branch: "",
  graduation_year: "",
  target_role: "",
  preferred_industry: "",
  technical_skills: "",
  career_interests: "",
};

function StudentProfile() {
  const { token, logout } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState(emptyProfile);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    let isMounted = true;

    async function loadProfile() {
      try {
        const data = await getStudentProfile(token);

        if (!isMounted) return;

        setForm({
          college_name: data.college_name || "",
          degree: data.degree || "",
          branch: data.branch || "",
          graduation_year: String(data.graduation_year ?? ""),
          target_role: data.target_role || "",
          preferred_industry: data.preferred_industry || "",
          technical_skills: (data.technical_skills || []).join(", "),
          career_interests: (data.career_interests || []).join(", "),
        });
      } catch (err) {
        if (!isMounted) return;

        if (err.response?.status === 401) {
          logout();
          navigate("/", { replace: true });
          return;
        }

        if (err.response?.status !== 404) {
          setError(
            err.response?.data?.detail || "Unable to load student profile.",
          );
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    if (token) {
      loadProfile();
    } else {
      navigate("/", { replace: true });
    }

    return () => {
      isMounted = false;
    };
  }, [token, logout, navigate]);

  function handleChange(event) {
    const { name, value } = event.target;

    setForm((previous) => ({
      ...previous,
      [name]: value,
    }));

    setError("");
    setSuccess("");
  }

  function convertToList(value) {
    return [
      ...new Set(
        value
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
      ),
    ];
  }

  async function handleSubmit(event) {
    event.preventDefault();

    if (saving) return;

    setError("");
    setSuccess("");

    const collegeName = form.college_name.trim();
    const degree = form.degree.trim();
    const branch = form.branch.trim();
    const graduationYear = form.graduation_year.trim();
    const targetRole = form.target_role.trim();
    const preferredIndustry = form.preferred_industry.trim();

    const technicalSkills = convertToList(form.technical_skills);
    const careerInterests = convertToList(form.career_interests);

    if (!collegeName) {
      setError("College / University is required.");
      return;
    }

    if (!degree) {
      setError("Degree is required.");
      return;
    }

    if (!branch) {
      setError("Branch / Specialization is required.");
      return;
    }

    if (!graduationYear) {
      setError("Graduation Year is required.");
      return;
    }

    const year = Number(graduationYear);

    if (!Number.isInteger(year) || year < 2000 || year > 2100) {
      setError("Graduation year must be a valid year between 2000 and 2100.");
      return;
    }

    if (!targetRole) {
      setError("Target Job Role is required.");
      return;
    }

    if (!preferredIndustry) {
      setError("Preferred Industry is required.");
      return;
    }

    if (technicalSkills.length === 0) {
      setError("At least one Technical Skill is required.");
      return;
    }

    if (careerInterests.length === 0) {
      setError("At least one Career Interest is required.");
      return;
    }

    setSaving(true);

    const payload = {
      college_name: collegeName,
      degree,
      branch,
      graduation_year: year,
      target_role: targetRole,
      preferred_industry: preferredIndustry,
      technical_skills: technicalSkills,
      career_interests: careerInterests,
    };

    try {
      const data = await saveStudentProfile(token, payload);

      setForm({
        college_name: data.college_name || "",
        degree: data.degree || "",
        branch: data.branch || "",
        graduation_year: data.graduation_year || "",
        target_role: data.target_role || "",
        preferred_industry: data.preferred_industry || "",
        technical_skills: (data.technical_skills || []).join(", "),
        career_interests: (data.career_interests || []).join(", "),
      });

      setSuccess("Student profile saved successfully.");
    } catch (err) {
      if (err.response?.status === 401) {
        logout();
        navigate("/", { replace: true });
        return;
      }

      const detail = err.response?.data?.detail;

      if (Array.isArray(detail)) {
        setError(detail.map((item) => item.msg || "Invalid input.").join(" "));
      } else {
        setError(
          typeof detail === "string"
            ? detail
            : "Unable to save profile. Please check your input.",
        );
      }
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <p className="loading-text">Loading student profile...</p>;
  }

  return (
    <div className="profile-page-shell">
      <div className="page-header">
        <div className="page-header-text">
          <span className="section-kicker">PERSONAL & ACADEMIC DETAILS</span>
          <h1>Student Profile</h1>
          <p>
            Manage your academic background, target industry, and technical skills
            used across CareerAI tools.
          </p>
        </div>

        <button
          type="button"
          className="secondary-btn"
          onClick={() => navigate("/dashboard")}
        >
          ← Back to Dashboard
        </button>
      </div>

      {error && (
        <div className="alert-box alert-error" role="alert">
          <span>⚠️</span>
          <div>{error}</div>
        </div>
      )}

      {success && (
        <div className="alert-box alert-success" role="status">
          <span>✓</span>
          <div>{success}</div>
        </div>
      )}

      <div className="analyzer-card profile-card">
        <form onSubmit={handleSubmit} className="profile-form-grid">
          <div className="form-group">
            <label htmlFor="college_name">
              College / University <span className="req">*</span>
            </label>
            <input
              id="college_name"
              name="college_name"
              className="form-input"
              value={form.college_name}
              onChange={handleChange}
              placeholder="e.g. Stanford University, IIT Delhi"
              maxLength={150}
              required
              aria-required="true"
            />
          </div>

          <div className="form-group">
            <label htmlFor="degree">
              Degree <span className="req">*</span>
            </label>
            <input
              id="degree"
              name="degree"
              className="form-input"
              value={form.degree}
              onChange={handleChange}
              placeholder="e.g. B.Tech, B.S., M.S."
              maxLength={100}
              required
              aria-required="true"
            />
          </div>

          <div className="form-group">
            <label htmlFor="branch">
              Branch / Specialization <span className="req">*</span>
            </label>
            <input
              id="branch"
              name="branch"
              className="form-input"
              value={form.branch}
              onChange={handleChange}
              placeholder="e.g. Computer Science, Information Technology"
              maxLength={120}
              required
              aria-required="true"
            />
          </div>

          <div className="form-group">
            <label htmlFor="graduation_year">
              Graduation Year <span className="req">*</span>
            </label>
            <input
              id="graduation_year"
              name="graduation_year"
              className="form-input"
              type="number"
              min="2000"
              max="2100"
              step="1"
              value={form.graduation_year}
              onChange={handleChange}
              placeholder="2026"
              required
              aria-required="true"
            />
          </div>

          <div className="form-group">
            <label htmlFor="target_role">
              Target Job Role <span className="req">*</span>
            </label>
            <input
              id="target_role"
              name="target_role"
              className="form-input"
              value={form.target_role}
              onChange={handleChange}
              placeholder="e.g. Full Stack Developer, Data Scientist"
              maxLength={120}
              required
              aria-required="true"
            />
          </div>

          <div className="form-group">
            <label htmlFor="preferred_industry">
              Preferred Industry <span className="req">*</span>
            </label>
            <input
              id="preferred_industry"
              name="preferred_industry"
              className="form-input"
              value={form.preferred_industry}
              onChange={handleChange}
              placeholder="e.g. FinTech, SaaS, AI, HealthTech"
              maxLength={120}
              required
              aria-required="true"
            />
          </div>

          <div className="form-group full-width">
            <label htmlFor="technical_skills">
              Technical Skills (comma-separated) <span className="req">*</span>
              <span className="label-hint">These skills are compared during Skill Gap Analysis</span>
            </label>
            <textarea
              id="technical_skills"
              name="technical_skills"
              className="form-textarea"
              value={form.technical_skills}
              onChange={handleChange}
              placeholder="Python, JavaScript, React, Node.js, SQL, Docker, Git"
              rows={3}
              required
              aria-required="true"
            />
          </div>

          <div className="form-group full-width">
            <label htmlFor="career_interests">
              Career Interests & Focus Areas (comma-separated) <span className="req">*</span>
            </label>
            <textarea
              id="career_interests"
              name="career_interests"
              className="form-textarea"
              value={form.career_interests}
              onChange={handleChange}
              placeholder="Cloud Computing, AI & Machine Learning, Distributed Systems"
              rows={3}
              required
              aria-required="true"
            />
          </div>

          <div className="full-width form-actions">
            <button type="submit" className="submit-btn" disabled={saving}>
              {saving ? "Saving Changes..." : "Save Profile Changes →"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default StudentProfile;
