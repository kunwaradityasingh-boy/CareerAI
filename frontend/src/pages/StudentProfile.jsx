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
    return <p>Loading student profile...</p>;
  }

  return (
    <main className="profile-page">
      <div className="profile-header">
        <button type="button" onClick={() => navigate("/dashboard")}>
          ← Dashboard
        </button>

        <h1>Student Profile</h1>
        <p>Manage your academic details and career preferences.</p>
      </div>

      {error && <p role="alert">{error}</p>}
      {success && <p role="status">{success}</p>}

      <form onSubmit={handleSubmit} className="profile-form">
        <div>
          <label htmlFor="college_name">
            College / University <span aria-hidden="true">*</span>
          </label>
          <input
            id="college_name"
            name="college_name"
            value={form.college_name}
            onChange={handleChange}
            maxLength={150}
            required
            aria-required="true"
          />
        </div>

        <div>
          <label htmlFor="degree">
            Degree <span aria-hidden="true">*</span>
          </label>
          <input
            id="degree"
            name="degree"
            value={form.degree}
            onChange={handleChange}
            maxLength={100}
            required
            aria-required="true"
          />
        </div>

        <div>
          <label htmlFor="branch">
            Branch / Specialization <span aria-hidden="true">*</span>
          </label>
          <input
            id="branch"
            name="branch"
            value={form.branch}
            onChange={handleChange}
            maxLength={120}
            required
            aria-required="true"
          />
        </div>

        <div>
          <label htmlFor="graduation_year">
            Graduation Year <span aria-hidden="true">*</span>
          </label>
          <input
            id="graduation_year"
            name="graduation_year"
            type="number"
            min="2000"
            max="2100"
            step="1"
            value={form.graduation_year}
            onChange={handleChange}
            required
            aria-required="true"
          />
        </div>

        <div>
          <label htmlFor="target_role">
            Target Job Role <span aria-hidden="true">*</span>
          </label>
          <input
            id="target_role"
            name="target_role"
            value={form.target_role}
            onChange={handleChange}
            maxLength={120}
            required
            aria-required="true"
          />
        </div>

        <div>
          <label htmlFor="preferred_industry">
            Preferred Industry <span aria-hidden="true">*</span>
          </label>
          <input
            id="preferred_industry"
            name="preferred_industry"
            value={form.preferred_industry}
            onChange={handleChange}
            maxLength={120}
            required
            aria-required="true"
          />
        </div>

        <div>
          <label htmlFor="technical_skills">
            Technical Skills (comma-separated) <span aria-hidden="true">*</span>
          </label>
          <textarea
            id="technical_skills"
            name="technical_skills"
            value={form.technical_skills}
            onChange={handleChange}
            placeholder="Python, Java, SQL, React"
            rows={3}
            required
            aria-required="true"
          />
        </div>

        <div>
          <label htmlFor="career_interests">
            Career Interests (comma-separated) <span aria-hidden="true">*</span>
          </label>
          <textarea
            id="career_interests"
            name="career_interests"
            value={form.career_interests}
            onChange={handleChange}
            placeholder="Cloud Computing, AI, Backend Development"
            rows={3}
            required
            aria-required="true"
          />
        </div>

        <button type="submit" disabled={saving}>
          {saving ? "Saving..." : "Save Profile"}
        </button>
      </form>
    </main>
  );
}

export default StudentProfile;
