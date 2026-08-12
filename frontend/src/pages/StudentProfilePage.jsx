import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createStudentProfile } from "../api/client";
import "./Auth.css";

function StudentProfilePage() {
  const navigate = useNavigate();

  const [form, setForm] = useState({
    degree: "",
    branch: "",
    current_year: "",
    semester: "",
    career_goal: "",
    interests: "",
    weekly_hours: "",
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleChange = (event) => {
    const { name, value } = event.target;

    setForm((previous) => ({
      ...previous,
      [name]: value,
    }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    setLoading(true);
    setError("");

    try {
      await createStudentProfile({
        degree: form.degree,
        branch: form.branch,
        current_year: Number(form.current_year),
        semester: Number(form.semester),
        career_goal: form.career_goal,
        interests: form.interests || null,
        weekly_hours: form.weekly_hours
          ? Number(form.weekly_hours)
          : null,
      });

      navigate("/");
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div
        className="auth-card"
        style={{ maxWidth: "520px" }}
      >
        <div className="auth-header">
          <div className="auth-logo">🎓</div>

          <h1>Complete Your Profile</h1>

          <p>
            Tell us about yourself so AI Student Mentor
            can personalize your learning experience.
          </p>
        </div>

        <form
          className="auth-form"
          onSubmit={handleSubmit}
        >
          <div className="auth-field">
            <label>Degree</label>

            <input
              name="degree"
              value={form.degree}
              onChange={handleChange}
              placeholder="e.g. B.Tech"
              required
            />
          </div>

          <div className="auth-field">
            <label>Branch</label>

            <input
              name="branch"
              value={form.branch}
              onChange={handleChange}
              placeholder="e.g. Information Technology"
              required
            />
          </div>

          <div className="auth-field">
            <label>Current Year</label>

            <input
              type="number"
              name="current_year"
              value={form.current_year}
              onChange={handleChange}
              min="1"
              max="10"
              placeholder="e.g. 3"
              required
            />
          </div>

          <div className="auth-field">
            <label>Semester</label>

            <input
              type="number"
              name="semester"
              value={form.semester}
              onChange={handleChange}
              min="1"
              max="20"
              placeholder="e.g. 5"
              required
            />
          </div>

          <div className="auth-field">
            <label>Career Goal</label>

            <input
              name="career_goal"
              value={form.career_goal}
              onChange={handleChange}
              placeholder="e.g. AI Engineer"
              required
            />
          </div>

          <div className="auth-field">
            <label>Interests</label>

            <input
              name="interests"
              value={form.interests}
              onChange={handleChange}
              placeholder="e.g. AI, ML, Python, Deep Learning"
            />
          </div>

          <div className="auth-field">
            <label>Weekly Study Hours</label>

            <input
              type="number"
              name="weekly_hours"
              value={form.weekly_hours}
              onChange={handleChange}
              min="1"
              max="168"
              placeholder="e.g. 15"
            />
          </div>

          {error && (
            <div className="auth-error">
              {error}
            </div>
          )}

          <button
            className="auth-submit-button"
            type="submit"
            disabled={loading}
          >
            {loading
              ? "Saving Profile..."
              : "Continue to Dashboard"}
          </button>
        </form>
      </div>
    </div>
  );
}

export default StudentProfilePage;