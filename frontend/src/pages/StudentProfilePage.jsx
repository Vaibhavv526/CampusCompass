import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  createStudentProfile,
  getStudentProfile,
  updateStudentProfile,
} from "../api/client";
import { getCurrentUser, changePassword } from "../api/auth";
import "./Auth.css";

function StudentProfilePage() {
  const navigate = useNavigate();

  // Active view tab: "profile" or "security"
  const [activeTab, setActiveTab] = useState("profile");

  // Profile data state
  const [currentUser, setCurrentUser] = useState(null);
  const [isNewProfile, setIsNewProfile] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);

  const [form, setForm] = useState({
    full_name: "",
    degree: "",
    branch: "",
    current_year: "",
    semester: "",
    career_goal: "",
    interests: "",
    weekly_hours: "",
  });

  const [profileLoading, setProfileLoading] = useState(false);
  const [profileError, setProfileError] = useState("");
  const [profileSuccess, setProfileSuccess] = useState("");

  // Password state
  const [passwordForm, setPasswordForm] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [passwordError, setPasswordError] = useState("");
  const [passwordSuccess, setPasswordSuccess] = useState("");

  // Load user and existing profile
  useEffect(() => {
    const loadProfileData = async () => {
      setInitialLoading(true);
      try {
        const user = await getCurrentUser();
        setCurrentUser(user);

        try {
          const profile = await getStudentProfile();
          setForm({
            full_name: profile.full_name || user.full_name || "",
            degree: profile.degree || "",
            branch: profile.branch || "",
            current_year: String(profile.current_year ?? ""),
            semester: String(profile.semester ?? ""),
            career_goal: profile.career_goal || "",
            interests: profile.interests || "",
            weekly_hours: String(profile.weekly_hours ?? ""),
          });
          setIsNewProfile(false);
          setIsEditing(false);
        } catch (err) {
          if (err.message && err.message.includes("(404)")) {
            // New user without a profile yet: onboarding mode
            setIsNewProfile(true);
            setIsEditing(true);
            setForm((prev) => ({
              ...prev,
              full_name: user.full_name || "",
            }));
          } else {
            setProfileError(err.message);
          }
        }
      } catch (err) {
        setProfileError(err.message);
      } finally {
        setInitialLoading(false);
      }
    };

    loadProfileData();
  }, []);

  const handleProfileChange = (event) => {
    const { name, value } = event.target;
    setForm((previous) => ({
      ...previous,
      [name]: value,
    }));
  };

  const handlePasswordChange = (event) => {
    const { name, value } = event.target;
    setPasswordForm((previous) => ({
      ...previous,
      [name]: value,
    }));
  };

  const handleCancelEdit = () => {
    // Reload form to saved state
    getStudentProfile()
      .then((profile) => {
        setForm({
          full_name: profile.full_name || currentUser?.full_name || "",
          degree: profile.degree || "",
          branch: profile.branch || "",
          current_year: String(profile.current_year ?? ""),
          semester: String(profile.semester ?? ""),
          career_goal: profile.career_goal || "",
          interests: profile.interests || "",
          weekly_hours: String(profile.weekly_hours ?? ""),
        });
        setIsEditing(false);
        setProfileError("");
      })
      .catch((err) => {
        setProfileError(err.message);
      });
  };

  const handleProfileSubmit = async (event) => {
    event.preventDefault();
    setProfileLoading(true);
    setProfileError("");
    setProfileSuccess("");

    const payload = {
      full_name: form.full_name.trim() || undefined,
      degree: form.degree.trim(),
      branch: form.branch.trim(),
      current_year: Number(form.current_year),
      semester: Number(form.semester),
      career_goal: form.career_goal.trim(),
      interests: form.interests.trim() || null,
      weekly_hours: form.weekly_hours ? Number(form.weekly_hours) : null,
    };

    try {
      if (isNewProfile) {
        await createStudentProfile(payload);
        setProfileSuccess("Profile created successfully!");
        setTimeout(() => navigate("/"), 1000);
      } else {
        const updated = await updateStudentProfile(payload);
        setForm({
          full_name: updated.full_name,
          degree: updated.degree,
          branch: updated.branch,
          current_year: String(updated.current_year),
          semester: String(updated.semester),
          career_goal: updated.career_goal,
          interests: updated.interests || "",
          weekly_hours: String(updated.weekly_hours ?? ""),
        });
        setIsEditing(false);
        setProfileSuccess("Profile updated successfully!");
        setTimeout(() => setProfileSuccess(""), 4000);
      }
    } catch (error) {
      setProfileError(error.message);
    } finally {
      setProfileLoading(false);
    }
  };

  const handlePasswordSubmit = async (event) => {
    event.preventDefault();
    setPasswordError("");
    setPasswordSuccess("");

    if (!passwordForm.current_password) {
      setPasswordError("Current password is required.");
      return;
    }

    if (passwordForm.new_password.length < 8) {
      setPasswordError("New password must be at least 8 characters long.");
      return;
    }

    if (passwordForm.new_password !== passwordForm.confirm_password) {
      setPasswordError("New password and confirmation do not match.");
      return;
    }

    setPasswordLoading(true);

    try {
      await changePassword(
        passwordForm.current_password,
        passwordForm.new_password
      );
      setPasswordSuccess("Password changed successfully!");
      setPasswordForm({
        current_password: "",
        new_password: "",
        confirm_password: "",
      });
      setTimeout(() => setPasswordSuccess(""), 4000);
    } catch (error) {
      setPasswordError(error.message);
    } finally {
      setPasswordLoading(false);
    }
  };

  if (initialLoading) {
    return (
      <div className="auth-page">
        <div className="auth-card" style={{ maxWidth: "560px", textAlign: "center" }}>
          <div className="auth-logo">🎓</div>
          <h2>Loading Profile...</h2>
          <p style={{ color: "var(--text-secondary)" }}>Fetching your campus records...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-page">
      <div className="auth-card" style={{ maxWidth: "620px" }}>
        {/* Navigation Bar */}
        <div className="profile-top-nav">
          <button
            type="button"
            className="profile-back-link"
            onClick={() => navigate("/")}
          >
            ← Back to Dashboard
          </button>
        </div>

        <div className="auth-header" style={{ marginBottom: "20px" }}>
          <div className="auth-logo">🎓</div>
          <h1>{isNewProfile ? "Complete Your Profile" : "Profile & Settings"}</h1>
          <p>
            {isNewProfile
              ? "Tell us about yourself so AI Student Mentor can personalize your experience."
              : "Manage your academic profile, study goals, and account security."}
          </p>
        </div>

        {/* Tab Selection (only for existing profile) */}
        {!isNewProfile && (
          <div className="profile-tabs">
            <button
              type="button"
              className={`profile-tab ${activeTab === "profile" ? "active" : ""}`}
              onClick={() => setActiveTab("profile")}
            >
              👤 Academic Profile
            </button>
            <button
              type="button"
              className={`profile-tab ${activeTab === "security" ? "active" : ""}`}
              onClick={() => setActiveTab("security")}
            >
              🔒 Password & Security
            </button>
          </div>
        )}

        {/* PROFILE TAB */}
        {activeTab === "profile" && (
          <div>
            {profileSuccess && <div className="auth-success">{profileSuccess}</div>}
            {profileError && <div className="auth-error">{profileError}</div>}

            {/* Read-only View Mode */}
            {!isEditing && !isNewProfile ? (
              <div className="profile-view-section">
                <div className="profile-header-card">
                  <div className="profile-avatar-large">
                    {form.full_name?.charAt(0).toUpperCase() || "S"}
                  </div>
                  <div>
                    <h2 className="profile-name-title">{form.full_name || "Student"}</h2>
                    <p className="profile-email-sub">{currentUser?.email}</p>
                  </div>
                </div>

                <div className="profile-details-grid">
                  <div className="profile-detail-item">
                    <span className="detail-label">Degree</span>
                    <span className="detail-value">{form.degree || "—"}</span>
                  </div>

                  <div className="detail-item">
                    <span className="detail-label">Branch / Major</span>
                    <span className="detail-value">{form.branch || "—"}</span>
                  </div>

                  <div className="detail-item">
                    <span className="detail-label">Current Year</span>
                    <span className="detail-value">Year {form.current_year || "—"}</span>
                  </div>

                  <div className="detail-item">
                    <span className="detail-label">Semester</span>
                    <span className="detail-value">Semester {form.semester || "—"}</span>
                  </div>

                  <div className="detail-item full-width">
                    <span className="detail-label">Career Goal</span>
                    <span className="detail-value highlight">{form.career_goal || "—"}</span>
                  </div>

                  <div className="detail-item full-width">
                    <span className="detail-label">Interests & Topics</span>
                    <span className="detail-value">{form.interests || "—"}</span>
                  </div>

                  <div className="detail-item">
                    <span className="detail-label">Weekly Study Hours</span>
                    <span className="detail-value">{form.weekly_hours ? `${form.weekly_hours} hrs/week` : "Not specified"}</span>
                  </div>
                </div>

                <div style={{ marginTop: "24px" }}>
                  <button
                    type="button"
                    className="auth-submit-button"
                    onClick={() => setIsEditing(true)}
                  >
                    ✏️ Edit Profile Information
                  </button>
                </div>
              </div>
            ) : (
              /* Editable Form Mode (also used for new profile onboarding) */
              <form className="auth-form" onSubmit={handleProfileSubmit}>
                <div className="auth-field">
                  <label>Full Name</label>
                  <input
                    name="full_name"
                    value={form.full_name}
                    onChange={handleProfileChange}
                    placeholder="e.g. Alex Johnson"
                    required
                  />
                </div>

                <div className="auth-field">
                  <label>Email (Account ID)</label>
                  <input
                    value={currentUser?.email || ""}
                    disabled
                    style={{ background: "var(--bg-surface-hover)", color: "var(--text-muted)", cursor: "not-allowed" }}
                  />
                </div>

                <div className="form-row-2">
                  <div className="auth-field">
                    <label>Degree</label>
                    <input
                      name="degree"
                      value={form.degree}
                      onChange={handleProfileChange}
                      placeholder="e.g. B.Tech"
                      required
                    />
                  </div>

                  <div className="auth-field">
                    <label>Branch / Major</label>
                    <input
                      name="branch"
                      value={form.branch}
                      onChange={handleProfileChange}
                      placeholder="e.g. Information Technology"
                      required
                    />
                  </div>
                </div>

                <div className="form-row-2">
                  <div className="auth-field">
                    <label>Current Year</label>
                    <input
                      type="number"
                      name="current_year"
                      value={form.current_year}
                      onChange={handleProfileChange}
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
                      onChange={handleProfileChange}
                      min="1"
                      max="20"
                      placeholder="e.g. 5"
                      required
                    />
                  </div>
                </div>

                <div className="auth-field">
                  <label>Career Goal</label>
                  <input
                    name="career_goal"
                    value={form.career_goal}
                    onChange={handleProfileChange}
                    placeholder="e.g. Machine Learning Engineer"
                    required
                  />
                </div>

                <div className="auth-field">
                  <label>Interests & Topics (comma-separated)</label>
                  <input
                    name="interests"
                    value={form.interests}
                    onChange={handleProfileChange}
                    placeholder="e.g. AI, Cloud, Python, System Design"
                  />
                </div>

                <div className="auth-field">
                  <label>Weekly Study Hours</label>
                  <input
                    type="number"
                    name="weekly_hours"
                    value={form.weekly_hours}
                    onChange={handleProfileChange}
                    min="1"
                    max="168"
                    placeholder="e.g. 15"
                  />
                </div>

                <div className="profile-form-buttons">
                  <button
                    className="auth-submit-button"
                    type="submit"
                    disabled={profileLoading}
                  >
                    {profileLoading
                      ? "Saving Profile..."
                      : isNewProfile
                      ? "Continue to Dashboard"
                      : "Save Changes"}
                  </button>

                  {!isNewProfile && (
                    <button
                      type="button"
                      className="profile-cancel-button"
                      onClick={handleCancelEdit}
                      disabled={profileLoading}
                    >
                      Cancel
                    </button>
                  )}
                </div>
              </form>
            )}
          </div>
        )}

        {/* SECURITY & PASSWORD TAB */}
        {activeTab === "security" && !isNewProfile && (
          <div>
            {passwordSuccess && <div className="auth-success">{passwordSuccess}</div>}
            {passwordError && <div className="auth-error">{passwordError}</div>}

            <form className="auth-form" onSubmit={handlePasswordSubmit}>
              <div className="auth-field">
                <label>Current Password</label>
                <div className="password-input-wrapper">
                  <input
                    type={showCurrentPassword ? "text" : "password"}
                    name="current_password"
                    value={passwordForm.current_password}
                    onChange={handlePasswordChange}
                    placeholder="Enter your current password"
                    required
                  />
                  <button
                    type="button"
                    className="password-toggle-btn"
                    onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                  >
                    {showCurrentPassword ? "Hide" : "Show"}
                  </button>
                </div>
              </div>

              <div className="auth-field">
                <label>New Password (min. 8 characters)</label>
                <div className="password-input-wrapper">
                  <input
                    type={showNewPassword ? "text" : "password"}
                    name="new_password"
                    value={passwordForm.new_password}
                    onChange={handlePasswordChange}
                    placeholder="Enter new secure password"
                    minLength="8"
                    required
                  />
                  <button
                    type="button"
                    className="password-toggle-btn"
                    onClick={() => setShowNewPassword(!showNewPassword)}
                  >
                    {showNewPassword ? "Hide" : "Show"}
                  </button>
                </div>
              </div>

              <div className="auth-field">
                <label>Confirm New Password</label>
                <div className="password-input-wrapper">
                  <input
                    type={showConfirmPassword ? "text" : "password"}
                    name="confirm_password"
                    value={passwordForm.confirm_password}
                    onChange={handlePasswordChange}
                    placeholder="Re-enter new secure password"
                    minLength="8"
                    required
                  />
                  <button
                    type="button"
                    className="password-toggle-btn"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  >
                    {showConfirmPassword ? "Hide" : "Show"}
                  </button>
                </div>
              </div>

              <button
                className="auth-submit-button"
                type="submit"
                disabled={passwordLoading}
                style={{ marginTop: "10px" }}
              >
                {passwordLoading ? "Updating Password..." : "Update Password"}
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}

export default StudentProfilePage;
