import { useEffect, useState } from "react";
import SkillAnalysisPage from "./pages/SkillAnalysisPage";
import "./App.css";
import {
  checkHealth,
  generateAssessment,
  generateRoadmap,
  getStudentProfile,
  getSkills,
} from "./api/client";
import {
  getCurrentUser,
  logoutUser,
} from "./api/auth";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
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


function App() {
  const [apiStatus, setApiStatus] = useState("Checking backend...");
  const [assessment, setAssessment] = useState(() => {
    const savedAssessment = localStorage.getItem("assessment");

    return savedAssessment ? JSON.parse(savedAssessment) : null;
  });
  const [skillAnalysis, setSkillAnalysis] = useState(() => {
  const savedSkillAnalysis = localStorage.getItem("skillAnalysis");

  return savedSkillAnalysis
    ? JSON.parse(savedSkillAnalysis)
    : null;
});
  const [showAssessmentPopup, setShowAssessmentPopup] = useState(false);
  const [assessmentLoading, setAssessmentLoading] = useState(false);
  const [assessmentError, setAssessmentError] = useState("");
  const [roadmap, setRoadmap] = useState(null);
  const [roadmapLoading, setRoadmapLoading] = useState(false);
  const [roadmapError, setRoadmapError] = useState("");
const navigate = useNavigate();
const location = useLocation();

const [currentUser, setCurrentUser] = useState(null);
const [studentProfile, setStudentProfile] = useState(null);
const [studentSkills, setStudentSkills] = useState([]);
  useEffect(() => {
  const publicRoutes = ["/login", "/register"];

  if (publicRoutes.includes(location.pathname)) {
    return;
  }

  const loadCurrentUser = async () => {
    try {
      const user = await getCurrentUser();
      setCurrentUser(user);
    } catch (error) {
      logoutUser();
      navigate("/login");
    }
  };

  loadCurrentUser();
}, [location.pathname, navigate]);
useEffect(() => {
  if (!currentUser || location.pathname !== "/") {
    return;
  }

  const loadStudentData = async () => {
    try {
      const profile = await getStudentProfile();
      const skills = await getSkills();

      setStudentProfile(profile);
      setStudentSkills(skills);
    } catch (error) {
      if (error.message.includes("(404)")) {
        navigate("/student-profile");
      }
    }
  };

  loadStudentData();
}, [currentUser, location.pathname, navigate]);

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
    localStorage.setItem("assessment", JSON.stringify(result));
    setShowAssessmentPopup(true);

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

  const savedAssessment = localStorage.getItem("assessment");

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
  } catch (error) {
    setRoadmapError(error.message);
  } finally {
    setRoadmapLoading(false);
  }
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
    className="logout-button"
    onClick={() => {
      logoutUser();
      navigate("/login");
    }}
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
          <h2>Welcome back 👋</h2>
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
            <button>Take Quiz</button>
          </div>

          <div className="dashboard-card">
            <h3>💡 Recommendations</h3>
            <p>
              Discover skills, projects, and resources recommended for you.
            </p>
            <button>View Recommendations</button>
          </div>
        </section>


        {roadmapError && (
          <div className="assessment-error">
            {roadmapError}
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
    <Route
      path="/skill-analysis"
      element={<SkillAnalysisPage />}
    />
    <Route
      path="/student-profile"
      element={<StudentProfilePage />}
    />
  </Routes>
);
}

export default App;