import { useEffect, useState } from "react";
import "./App.css";

import { checkHealth } from "./api/client";

function App() {
  const [apiStatus, setApiStatus] = useState("Checking backend...");

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

  return (
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
            <button>Start Assessment</button>
          </div>

          <div className="dashboard-card">
            <h3>🗺️ Learning Roadmap</h3>
            <p>Generate a personalized roadmap toward your career goal.</p>
            <button>View Roadmap</button>
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
      </main>
    </div>
  );
}

export default App;