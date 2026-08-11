import { useEffect, useState } from "react";
import "./App.css";
import {
  checkHealth,
  generateAssessment,
  generateRoadmap,
} from "./api/client";

import { Routes, Route, useNavigate } from "react-router-dom";
import AssessmentPage from "./pages/AssessmentPage";
import RoadmapPage from "./pages/RoadmapPage";

function App() {
  const [apiStatus, setApiStatus] = useState("Checking backend...");
  const [assessment, setAssessment] = useState(() => {
    const savedAssessment = localStorage.getItem("assessment");

    return savedAssessment ? JSON.parse(savedAssessment) : null;
  });
  const [assessmentLoading, setAssessmentLoading] = useState(false);
  const [assessmentError, setAssessmentError] = useState("");
  const [roadmap, setRoadmap] = useState(null);
  const [roadmapLoading, setRoadmapLoading] = useState(false);
  const [roadmapError, setRoadmapError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    checkHealth()
      .then(() => {
        setApiStatus("Backend connected");
      })
      .catch(() => {
        setApiStatus("Backend unavailable");
      });
  }, []);

  const student = {
    name: "Vaibhav",
    email: "vaibhav@example.com",
    degree: "B.Tech",
    branch: "Information Technology",
    current_year: 3,
    semester: 5,
    career_goal: "AI Engineer",
    interests: ["Python", "Machine Learning", "Deep Learning"],
    weekly_hours: 10,
    skills: [
      {
        name: "Python",
        category: "Programming",
        current_level: 30,
        target_level: 90,
      },
      {
        name: "DSA",
        category: "Computer Science",
        current_level: 35,
        target_level: 85,
      },
      {
        name: "Machine Learning",
        category: "AI",
        current_level: 20,
        target_level: 80,
      },
    ],
  };
  const handleAssessment = async () => {
  setAssessmentLoading(true);
  setAssessmentError("");

  try {
    const result = await generateAssessment(student);

    setAssessment(result);
    localStorage.setItem("assessment", JSON.stringify(result));

  } catch (error) {
    setAssessmentError(error.message);
  } finally {
    setAssessmentLoading(false);
  }
};

const handleRoadmap = async () => {
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
          <span className="avatar">V</span>
          <span>Student</span>
        </div>
      </header>

      <main className="dashboard">
        {assessment && (
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

                  setAssessment(null);

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
                onClick={() => setAssessment(null)}
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
            <p>Analyze your current skills and identify learning gaps.</p>
            <button onClick={handleAssessment} disabled={assessmentLoading}>
              {assessmentLoading ? "Analyzing..." : "Start Assessment"}
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
            <button>Ask Tutor</button>
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
  </Routes>
);
}

export default App;