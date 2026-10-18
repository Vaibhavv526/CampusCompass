import { useEffect, useState, useCallback } from "react";
import SkillAnalysisPage from "./pages/SkillAnalysisPage";
import "./App.css";
import RecommendationPage from "./pages/RecommendationPage";
import {
  generateAssessment,
  generateRoadmap,
  getStudentProfile,
  getSkills,
  createLearningActivity,
  getLearningHistory,
  getStudentProgress,
} from "./api/client";
import {
  getCurrentUser,
  logoutUser,
} from "./api/auth";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import QuizPage from "./pages/QuizPage";
import {
  Routes,
  Route,
  useNavigate,
  useLocation,
} from "react-router-dom";
import AssessmentPage from "./pages/AssessmentPage";
import RoadmapPage from "./pages/RoadmapPage";
import TutorPage from "./pages/TutorPage";
import StudentProfilePage from "./pages/StudentProfilePage";
import LearningHistoryPage from "./pages/LearningHistoryPage";
import ProgressDashboard from "./components/ProgressDashboard";


function App() {
  const [assessment, setAssessment] = useState(null);
  const [skillAnalysis, setSkillAnalysis] = useState(null);
  const [showAssessmentPopup, setShowAssessmentPopup] = useState(false);
  const [assessmentLoading, setAssessmentLoading] = useState(false);
  const [assessmentError, setAssessmentError] = useState("");
  const [roadmap, setRoadmap] = useState(null);
  const [roadmapLoading, setRoadmapLoading] = useState(false);
  const [roadmapError, setRoadmapError] = useState("");
  const [historyWarning, setHistoryWarning] = useState("");
  const [progress, setProgress] = useState(null);
  const [progressLoading, setProgressLoading] = useState(false);
  const [progressError, setProgressError] = useState("");

  const [theme, setTheme] = useState(() => {
    try {
      const saved = localStorage.getItem("campuscompass-theme");
      return saved === "dark" || saved === "light" ? saved : "light";
    } catch {
      return "light";
    }
  });

  useEffect(() => {
    try {
      document.documentElement.setAttribute("data-theme", theme);
      localStorage.setItem("campuscompass-theme", theme);
    } catch (e) {
      console.warn("Failed to persist theme preference:", e);
    }
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  };
const navigate = useNavigate();
const location = useLocation();

const [currentUser, setCurrentUser] = useState(null);
const [studentProfile, setStudentProfile] = useState(null);
const [studentSkills, setStudentSkills] = useState([]);
  useEffect(() => {
    let isCancelled = false;
    const publicRoutes = ["/login", "/register"];

    if (publicRoutes.includes(location.pathname)) {
      return;
    }

    const loadCurrentUser = async () => {
      try {
        const user = await getCurrentUser();
        if (!isCancelled) {
          setCurrentUser(user);
        }
      } catch {
        if (!isCancelled) {
          logoutUser();
          setCurrentUser(null);
          navigate("/login");
        }
      }
    };

    loadCurrentUser();

    return () => {
      isCancelled = true;
    };
  }, [location.pathname, navigate]);

  useEffect(() => {
    if (!currentUser || location.pathname !== "/") {
      return;
    }

    let isCancelled = false;
    const loadStudentData = async () => {
      try {
        const profile = await getStudentProfile();
        const skills = await getSkills();

        if (!isCancelled) {
          setStudentProfile(profile);
          setStudentSkills(skills);
        }
      } catch (error) {
        if (!isCancelled && error.message.includes("(404)")) {
          navigate("/student-profile");
        }
      }
    };

    loadStudentData();

    return () => {
      isCancelled = true;
    };
  }, [currentUser, location.pathname, navigate]);

  const loadProgress = useCallback(async () => {
    if (!currentUser) return;
    setProgressLoading(true);
    setProgressError("");
    try {
      const data = await getStudentProgress();
      setProgress(data);
    } catch (err) {
      console.warn("Could not load student progress:", err);
      setProgressError(err.message || "Failed to load progress analytics");
    } finally {
      setProgressLoading(false);
    }
  }, [currentUser]);

  useEffect(() => {
    if (!currentUser || location.pathname !== "/") {
      return;
    }
    let isCancelled = false;

    Promise.resolve().then(async () => {
      if (isCancelled) return;
      setProgressLoading(true);
      setProgressError("");
      try {
        const data = await getStudentProgress();
        if (!isCancelled) {
          setProgress(data);
        }
      } catch (err) {
        if (!isCancelled) {
          console.warn("Could not load student progress:", err);
          setProgressError(err.message || "Failed to load progress analytics");
        }
      } finally {
        if (!isCancelled) {
          setProgressLoading(false);
        }
      }
    });

    return () => {
      isCancelled = true;
    };
  }, [currentUser, location.pathname]);


  // Scoped assessment and skill analysis restoration per authenticated user ID
  useEffect(() => {
    let isCancelled = false;

    if (!currentUser?.id) {
      Promise.resolve().then(() => {
        if (!isCancelled) {
          setAssessment(null);
          setSkillAnalysis(null);
        }
      });
      return () => {
        isCancelled = true;
      };
    }

    Promise.resolve().then(async () => {
      const userAssessmentKey = `assessment_${currentUser.id}`;
      let cachedAssessment = null;
      try {
        const raw = localStorage.getItem(userAssessmentKey);
        if (raw) cachedAssessment = JSON.parse(raw);
      } catch (e) {
        console.warn("Failed to parse cached assessment", e);
      }

      // Fallback: restore from authenticated learning history if absent in localStorage
      if (!cachedAssessment) {
        try {
          const historyItems = await getLearningHistory({
            activity_type: "assessment",
            limit: 1,
          });
          if (historyItems && historyItems.length > 0 && historyItems[0].data) {
            cachedAssessment = historyItems[0].data;
            try {
              localStorage.setItem(userAssessmentKey, JSON.stringify(cachedAssessment));
            } catch (e) {
              console.warn("Failed to cache retrieved assessment to localStorage", e);
            }
          }
        } catch (e) {
          console.warn("Could not fetch assessment from learning history", e);
        }
      }

      const userSkillKey = `skillAnalysis_${currentUser.id}`;
      let cachedSkillAnalysis = null;
      try {
        const raw = localStorage.getItem(userSkillKey);
        if (raw) cachedSkillAnalysis = JSON.parse(raw);
      } catch (e) {
        console.warn("Failed to parse cached skill analysis", e);
      }

      if (!isCancelled) {
        setAssessment(cachedAssessment);
        setSkillAnalysis(cachedSkillAnalysis);
      }
    });

    return () => {
      isCancelled = true;
    };
  }, [currentUser?.id]);

  const student = studentProfile
  ? {
      name: studentProfile.full_name,
      email: currentUser?.email,
      degree: studentProfile.degree,
      branch: studentProfile.branch,
      current_year: studentProfile.current_year,
      semester: studentProfile.semester,
      career_goal: studentProfile.career_goal,
      interests: studentProfile.interests
        ? studentProfile.interests
            .split(",")
            .map((item) => item.trim())
        : [],
      weekly_hours: studentProfile.weekly_hours,
      skills: studentSkills.map((skill) => ({
        name: skill.name,
        category: "Technical Skill",
        current_level: skill.proficiency,
        target_level: 100,
        strengths: skill.strengths,
        weak_areas: skill.weak_areas,
        experience: skill.experience,
      })),
    }
  : null;
  const handleAssessment = async () => {
  if (!student) {
    setAssessmentError("Student profile is still loading.");
    return;
  }

  setAssessmentLoading(true);
  setAssessmentError("");

  try {
    const result = await generateAssessment(student);

    setAssessment(result);
    if (currentUser?.id) {
      localStorage.setItem(`assessment_${currentUser.id}`, JSON.stringify(result));
    }
    setShowAssessmentPopup(true);

    // Phase 2A: Persist skill gap assessment to user history (non-blocking)
    try {
      const gaps = result.skill_gaps || [];
      const highCount = gaps.filter(
        (g) => (g.priority || "").toLowerCase() === "high"
      ).length;
      await createLearningActivity({
        activity_type: "assessment",
        title: `Skill Gap Assessment (${student.career_goal || "General"})`,
        summary: `${gaps.length} skills analyzed, ${highCount} high-priority gap(s)`,
        score: null,
        data: result,
      });
      setHistoryWarning("");
    } catch (historyErr) {
      console.warn("Could not persist assessment to user history:", historyErr);
      setHistoryWarning("Assessment completed, but could not be saved to your learning history.");
    }

  } catch (error) {
    setAssessmentError(error.message);
  } finally {
    setAssessmentLoading(false);
  }
};

const handleRoadmap = async () => {
  if (!student) {
    setRoadmapError("Student profile is still loading.");
    return;
  }

  const userAssessmentKey = currentUser?.id ? `assessment_${currentUser.id}` : null;
  let assessmentData = assessment;
  if (!assessmentData && userAssessmentKey) {
    try {
      const savedAssessment = localStorage.getItem(userAssessmentKey);
      if (savedAssessment) {
        assessmentData = JSON.parse(savedAssessment);
      }
    } catch (e) {
      console.warn("Failed to parse cached assessment from localStorage", e);
    }
  }

  setRoadmapLoading(true);
  setRoadmapError("");

  try {
    const result = await generateRoadmap(student, assessmentData || null);
    setRoadmap(result);

    // Phase 2A: Persist new roadmap to user history (non-blocking)
    try {
      const stepsCount = result.steps?.length || 0;
      const savedRoadmap = await createLearningActivity({
        activity_type: "roadmap",
        title: result.title || "Career Learning Roadmap",
        summary: `0 of ${stepsCount} milestones completed (0%)`,
        score: 0.0,
        data: result,
      });
      if (savedRoadmap?.id) {
        result._activityId = savedRoadmap.id;
        setRoadmap({ ...result, _activityId: savedRoadmap.id });
      }
      setHistoryWarning("");
    } catch (historyErr) {
      console.warn("Could not persist roadmap to user history:", historyErr);
      setHistoryWarning("Roadmap generated, but could not be saved to your learning history.");
    }
  } catch (error) {
    setRoadmapError(error.message);
  } finally {
    setRoadmapLoading(false);
  }
};

  const handleLogout = () => {
    logoutUser();
    setCurrentUser(null);
    setStudentProfile(null);
    setStudentSkills([]);
    setAssessment(null);
    setSkillAnalysis(null);
    setRoadmap(null);
    setShowAssessmentPopup(false);
    navigate("/login");
  };

  return (
    <Routes>
      <Route
        path="/"
        element={
    <div className="app">
      <header className="dashboard-navbar" role="banner">
        <div
          className="navbar-brand"
          onClick={() => navigate("/")}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              navigate("/");
            }
          }}
          tabIndex={0}
          role="button"
          aria-label="CampusCompass Dashboard"
        >
          <div className="brand-logo" aria-hidden="true">
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="12" cy="12" r="10" />
              <polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76" fill="currentColor" fillOpacity="0.25" />
            </svg>
          </div>
          <span className="brand-name">CampusCompass</span>
        </div>

        <nav className="navbar-actions" aria-label="Dashboard navigation">
          <button
            type="button"
            className="nav-btn nav-history-btn"
            onClick={() => navigate("/learning-history")}
            title="View your saved learning activities"
            aria-label="Learning History"
          >
            <svg
              className="nav-btn-icon"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
            <span className="nav-btn-text">Learning History</span>
          </button>

          <button
            type="button"
            className="nav-btn nav-theme-toggle"
            onClick={toggleTheme}
            title={theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"}
            aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
          >
            <span className="nav-btn-text">
              {theme === "dark" ? "Light Mode" : "Dark Mode"}
            </span>
          </button>

          <button
            type="button"
            className="profile-control-btn"
            onClick={() => navigate("/student-profile")}
            title="Profile & Settings"
            aria-label={`Profile and Settings for ${currentUser?.full_name || "Student"}`}
          >
            <span className="profile-avatar" aria-hidden="true">
              {currentUser?.full_name?.trim()?.charAt(0).toUpperCase() || "U"}
            </span>
            <span className="profile-name">
              {currentUser?.full_name || "Student"}
            </span>
          </button>

          <button
            type="button"
            className="nav-btn nav-logout-btn"
            onClick={handleLogout}
            title="Log out of your account"
            aria-label="Log out"
          >
            <span>Logout</span>
          </button>
        </nav>
      </header>

      <main className="dashboard">
        {showAssessmentPopup && assessment && (
          <div className="analysis-popup-overlay">
            <div className="analysis-popup">
              <div className="analysis-popup-icon">🎉</div>

              <h2>Assessment Complete!</h2>

              <p>
                Your personalized AI skill analysis is ready to view.
              </p>

              <button
                onClick={() => {
                  const assessmentData = assessment;

                  setShowAssessmentPopup(false);

                  navigate("/assessment", {
                    state: {
                      assessment: assessmentData,
                      student,
                    },
                  });
                }}
              >
                View Analysis
              </button>

              <button
                className="popup-secondary-button"
                onClick={() => setShowAssessmentPopup(false)}
              >
                Continue Dashboard
              </button>
            </div>
          </div>
        )}
        {roadmap && (
          <div className="analysis-popup-overlay">
            <div className="analysis-popup">
              <div className="analysis-popup-icon">🗺️</div>

              <h2>Roadmap Ready!</h2>

              <p>
                Your personalized learning roadmap is ready to view.
              </p>

              <button
                onClick={() => {
                  const roadmapData = roadmap;

                  setRoadmap(null);

                  navigate("/roadmap", {
                    state: {
                      roadmap: roadmapData,
                      student,
                    },
                  });
                }}
              >
                View Roadmap
              </button>

              <button
                className="popup-secondary-button"
                onClick={() => setRoadmap(null)}
              >
                Continue Dashboard
              </button>
            </div>
          </div>
        )}
        <section className="learning-overview-header">
          <h2>Learning Overview</h2>
          <p>Track your progress and continue learning.</p>
        </section>

        <ProgressDashboard
          progress={progress}
          loading={progressLoading}
          error={progressError}
          onRefresh={loadProgress}
          navigate={navigate}
        />

        <section className="dashboard-grid">
           <div className="dashboard-card">
            <h3>📊 Assessment</h3>

            <p>
              Analyze your current skills and identify learning gaps.
            </p>

            {assessment ? (
              <div className="card-action-group" style={{ display: "flex", gap: "10px", flexWrap: "wrap", marginTop: "12px" }}>
                <button
                  type="button"
                  onClick={() =>
                    navigate("/assessment", {
                      state: {
                        assessment,
                        student,
                      },
                    })
                  }
                >
                  View Assessment
                </button>
                <button
                  type="button"
                  className="secondary-action-btn"
                  onClick={handleAssessment}
                  disabled={assessmentLoading}
                  style={{
                    backgroundColor: "var(--btn-secondary-bg)",
                    color: "var(--btn-secondary-text)",
                    border: "1px solid var(--btn-secondary-border)",
                  }}
                >
                  {assessmentLoading ? "Generating..." : "Retake Assessment"}
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={handleAssessment}
                disabled={assessmentLoading}
              >
                {assessmentLoading ? "Generating..." : "Start Assessment"}
              </button>
            )}
          </div>
          <div className="dashboard-card">
            <h3>🧠 Skill Analysis</h3>

            <p>
              Analyze your technical skills, identify strengths and
              weaknesses, and get personalized improvement steps.
            </p>

            <button
              onClick={() => navigate("/skill-analysis")}
            >
              {skillAnalysis ? "View Analysis" : "Analyze Skills"}
            </button>
          </div>

          <div className="dashboard-card">
            <h3>🗺️ Learning Roadmap</h3>
            <p>Generate a personalized roadmap toward your career goal.</p>
            <button onClick={handleRoadmap} disabled={roadmapLoading}>
              {roadmapLoading ? "Generating..." : "View Roadmap"}
            </button>
          </div>

          <div className="dashboard-card">
            <h3>🤖 AI Tutor</h3>
            <p>Ask questions and get personalized explanations.</p>
            <button onClick={() => navigate("/tutor")}>
              Ask Tutor
            </button>
          </div>

          <div className="dashboard-card">
            <h3>📝 Quiz</h3>
            <p>Test your knowledge and identify weak areas.</p>
            <button onClick={() => navigate("/quiz")}>
              Take Quiz
            </button>
          </div>
          <div className="dashboard-card">
            <h3>💡 Recommendations</h3>
            <p>
              Discover skills, projects, and resources recommended for you.
            </p>
            <button onClick={() => navigate("/recommendations")}>
              View Recommendations
            </button>
          </div>

          <div className="dashboard-card">
            <h3>📜 Learning History</h3>
            <p>
              Review past assessments, quiz scores, and learning roadmap progress.
            </p>
            <button onClick={() => navigate("/learning-history")}>
              View History
            </button>
          </div>
        </section>


        {assessmentError && (
          <div className="assessment-error">
            {assessmentError}
          </div>
        )}
        {roadmapError && (
          <div className="assessment-error">
            {roadmapError}
          </div>
        )}
        {historyWarning && (
          <div className="assessment-error" style={{ backgroundColor: "var(--status-warning-bg)", color: "var(--status-warning-text)", borderColor: "var(--status-warning-border)" }}>
            ⚠️ {historyWarning}
          </div>
        )}
      </main>
            </div>
      }
    />

    <Route path="/assessment" element={<AssessmentPage />} />
    <Route path="/roadmap" element={<RoadmapPage />} />
    <Route path="/tutor" element={<TutorPage />} />
    <Route path="/login" element={<LoginPage />} />
    <Route path="/register" element={<RegisterPage />} />
    <Route path="/quiz" element={<QuizPage />} />
    <Route
      path="/skill-analysis"
      element={<SkillAnalysisPage />}
    />
    <Route
      path="/recommendations"
      element={<RecommendationPage />}
    />
    <Route
      path="/student-profile"
      element={<StudentProfilePage />}
    />
    <Route
      path="/learning-history"
      element={<LearningHistoryPage />}
    />
  </Routes>
);
}

export default App;