import { useEffect, useState } from "react";
import SkillAnalysisPage from "./pages/SkillAnalysisPage";
import "./App.css";
import RecommendationPage from "./pages/RecommendationPage";
import {
  checkHealth,
  generateAssessment,
  generateRoadmap,
  getStudentProfile,
  getSkills,
  createLearningActivity,
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


function App() {
  const [apiStatus, setApiStatus] = useState("Checking backend...");
  const [assessment, setAssessment] = useState(null);
  const [skillAnalysis, setSkillAnalysis] = useState(null);
  const [showAssessmentPopup, setShowAssessmentPopup] = useState(false);
  const [assessmentLoading, setAssessmentLoading] = useState(false);
  const [assessmentError, setAssessmentError] = useState("");
  const [roadmap, setRoadmap] = useState(null);
  const [roadmapLoading, setRoadmapLoading] = useState(false);
  const [roadmapError, setRoadmapError] = useState("");
  const [historyWarning, setHistoryWarning] = useState("");
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
      } catch (error) {
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

  // Scoped assessment and skill analysis restoration per authenticated user ID
  useEffect(() => {
    if (!currentUser?.id) {
      setAssessment(null);
      setSkillAnalysis(null);
      return;
    }

    const userAssessmentKey = `assessment_${currentUser.id}`;
    const savedAssessment = localStorage.getItem(userAssessmentKey);
    setAssessment(savedAssessment ? JSON.parse(savedAssessment) : null);

    const userSkillKey = `skillAnalysis_${currentUser.id}`;
    const savedSkillAnalysis = localStorage.getItem(userSkillKey);
    setSkillAnalysis(savedSkillAnalysis ? JSON.parse(savedSkillAnalysis) : null);
  }, [currentUser?.id]);

  useEffect(() => {
    checkHealth()
      .then(() => {
        setApiStatus("Backend connected");
      })
      .catch(() => {
        setApiStatus("Backend unavailable");
      });
  }, []);

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
  const savedAssessment = userAssessmentKey ? localStorage.getItem(userAssessmentKey) : null;

  const assessmentData = assessment
    || (savedAssessment ? JSON.parse(savedAssessment) : null);

  if (!assessmentData) {
    setRoadmapError("Please complete the assessment first.");
    return;
  }

  setRoadmapLoading(true);
  setRoadmapError("");

  try {
    const result = await generateRoadmap(student, assessmentData);
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
      <header className="dashboard-header">
        <div>
          <h1>AI Student Mentor</h1>
          <p>Your personalized learning companion</p>
          <p className="api-status">{apiStatus}</p>
        </div>

        <div className="student-badge">
  <span className="avatar">
    {currentUser?.full_name?.charAt(0).toUpperCase() || "U"}
  </span>

  <span>
    {currentUser?.full_name || "Student"}
  </span>

  <button
    className="history-button"
    onClick={() => navigate("/learning-history")}
    title="View your saved learning activities"
  >
    📜 Learning History
  </button>

  <button
    className="profile-button"
    onClick={() => navigate("/student-profile")}
    title="View & Edit Profile, Change Password"
  >
    ⚙️ Profile & Settings
  </button>

  <button
    className="logout-button"
    onClick={handleLogout}
  >
    Logout
  </button>
</div>
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
        <section className="welcome-section">
          <h2>Welcome back</h2>
          <p>
            Track your learning progress, get personalized recommendations,
            practice with quizzes, and ask your AI tutor for help.
          </p>
        </section>

        <section className="dashboard-grid">
           <div className="dashboard-card">
            <h3>📊 Assessment</h3>

            <p>
              Analyze your current skills and identify learning gaps.
            </p>

            <button
              onClick={handleAssessment}
              disabled={assessmentLoading}
            >
              {assessmentLoading ? "Generating..." : "Start Assessment"}
            </button>
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


        {roadmapError && (
          <div className="assessment-error">
            {roadmapError}
          </div>
        )}
        {historyWarning && (
          <div className="assessment-error" style={{ backgroundColor: "#fef3c7", color: "#92400e", borderColor: "#fde68a" }}>
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