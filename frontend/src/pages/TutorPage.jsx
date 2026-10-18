import { useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import {
  askTutor,
  getStudentProfile,
  getSkills,
  createLearningActivity,
} from "../api/client";
import "./TutorPage.css";

function TutorPage() {
  const navigate = useNavigate();
  const location = useLocation();

  const [topic, setTopic] = useState(() => location.state?.topic || "");
  const [question, setQuestion] = useState(() => location.state?.question || "");
  const [milestone] = useState(() => location.state?.milestone || null);
  const [answer, setAnswer] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [historyNotice, setHistoryNotice] = useState("");

  const [studentProfile, setStudentProfile] = useState(null);
  const [studentSkills, setStudentSkills] = useState([]);

  useEffect(() => {
    let isCancelled = false;

    const loadStudentData = async () => {
      try {
        const [profile, skills] = await Promise.all([
          getStudentProfile().catch((err) => {
            console.warn("Could not fetch student profile for tutor:", err);
            return null;
          }),
          getSkills().catch((err) => {
            console.warn("Could not fetch skills for tutor:", err);
            return [];
          }),
        ]);

        if (!isCancelled) {
          setStudentProfile(profile);
          setStudentSkills(skills || []);
        }
      } catch (err) {
        console.warn("Failed loading student data for tutor:", err);
      }
    };

    loadStudentData();

    return () => {
      isCancelled = true;
    };
  }, []);

  const handleAskTutor = async () => {
    if (!topic.trim() || !question.trim()) {
      setError("Please enter both a topic and a question.");
      return;
    }

    setLoading(true);
    setError("");
    setHistoryNotice("");

    try {
      const student = {
        name: studentProfile?.full_name || "Student",
        email: "",
        degree: studentProfile?.degree || "Undergraduate",
        branch: studentProfile?.branch || "Computer Science",
        current_year: studentProfile?.current_year || 1,
        semester: studentProfile?.semester || 1,
        career_goal: studentProfile?.career_goal || "Software Engineer",
        interests: studentProfile?.interests
          ? studentProfile.interests
              .split(",")
              .map((item) => item.trim())
              .filter(Boolean)
          : [],
        weekly_hours: studentProfile?.weekly_hours || 10,
        skills: (studentSkills || []).map((skill) => ({
          name: skill.name,
          category: "Technical Skill",
          current_level: skill.proficiency ?? 50,
          target_level: 80,
        })),
      };

      const result = await askTutor(
        student,
        topic.trim(),
        question.trim()
      );

      setAnswer(result);

      // Persist completed tutor session to learning history (non-blocking)
      try {
        const explanationSnippet = result.explanation
          ? (result.explanation.length > 200
              ? result.explanation.slice(0, 200) + "..."
              : result.explanation)
          : `Question: ${question.trim().slice(0, 100)}`;

        await createLearningActivity({
          activity_type: "tutor",
          title: `AI Tutor: ${topic.trim()}`.slice(0, 255),
          summary: explanationSnippet.slice(0, 1000),
          score: null,
          data: {
            topic: topic.trim(),
            milestone: milestone || null,
            question: question.trim(),
            answer: result,
          },
        });
      } catch (historyErr) {
        console.warn("Could not persist tutor session to learning history:", historyErr);
        setHistoryNotice("Explanation received, but could not be saved to your learning history.");
      }
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="tutor-page">
      <button
        className="back-button"
        onClick={() => navigate("/")}
      >
        ← Back to Dashboard
      </button>

      <header className="tutor-header">
        <div className="tutor-icon">🤖</div>

        <div>
          <p className="eyebrow">AI TUTOR</p>

          <h1>Learn with Your AI Tutor</h1>

          <p className="tutor-subtitle">
            Ask questions and get personalized explanations
            based on your learning level, career goal, and roadmap context.
          </p>
        </div>
      </header>

      <section className="tutor-input-card">
        <p className="eyebrow">ASK YOUR QUESTION</p>

        <h2>What would you like to learn?</h2>

        <div className="tutor-field">
          <label>Topic</label>

          <input
            type="text"
            placeholder="e.g. Python, Machine Learning, DSA"
            value={topic}
            onChange={(event) => setTopic(event.target.value)}
          />
        </div>

        <div className="tutor-field">
          <label>Your Question</label>

          <textarea
            placeholder="e.g. What is a Python decorator and why do we use it?"
            value={question}
            onChange={(event) =>
              setQuestion(event.target.value)
            }
          />
        </div>

        <button
          className="ask-tutor-button"
          onClick={handleAskTutor}
          disabled={loading}
        >
          {loading ? "Thinking..." : "Ask AI Tutor"}
        </button>
      </section>

      {error && (
        <div className="tutor-error">
          {error}
        </div>
      )}

      {historyNotice && (
        <div className="tutor-error" style={{ backgroundColor: "var(--status-warning-bg)", color: "var(--status-warning-text)", borderColor: "var(--status-warning-border)" }}>
          ⚠️ {historyNotice}
        </div>
      )}

      {answer && (
        <section className="tutor-results">
          <div className="tutor-result-header">
            <p className="eyebrow">AI EXPLANATION</p>

            <h2>{answer.topic}</h2>
          </div>

          <div className="tutor-section">
            <h3>📖 Explanation</h3>

            <p>{answer.explanation}</p>
          </div>

          <div className="tutor-section">
            <h3>💡 Key Points</h3>

            <ul>
              {answer.key_points.map((point, index) => (
                <li key={index}>{point}</li>
              ))}
            </ul>
          </div>

          <div className="tutor-section">
            <h3>🛠️ Practical Example</h3>

            <p>{answer.example}</p>
          </div>

          <div className="tutor-section">
            <h3>🎯 Practice Task</h3>

            <p>{answer.practice_task}</p>
          </div>

          <div className="tutor-followup-actions" style={{ display: "flex", gap: "12px", marginTop: "24px", flexWrap: "wrap" }}>
            <button
              type="button"
              className="tutor-action-btn tutor-practice-btn"
              onClick={() =>
                navigate("/quiz", {
                  state: {
                    topic: answer.topic || topic,
                    milestone: milestone || null,
                  },
                })
              }
              style={{
                backgroundColor: "#2563eb",
                color: "#ffffff",
                border: "none",
                borderRadius: "8px",
                padding: "10px 18px",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              📝 Practice in Quiz
            </button>
            <button
              type="button"
              className="tutor-action-btn tutor-roadmap-btn"
              onClick={() => navigate("/roadmap")}
              style={{
                backgroundColor: "var(--btn-secondary-bg)",
                color: "var(--btn-secondary-text)",
                border: "1px solid var(--btn-secondary-border)",
                borderRadius: "8px",
                padding: "10px 18px",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              🗺️ Return to Roadmap
            </button>
          </div>
        </section>
      )}
    </div>
  );
}

export default TutorPage;
