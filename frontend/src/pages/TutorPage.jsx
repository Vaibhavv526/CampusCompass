import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { askTutor } from "../api/client";
import "./TutorPage.css";

function TutorPage() {
  const navigate = useNavigate();

  const [topic, setTopic] = useState("");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleAskTutor = async () => {
    if (!topic.trim() || !question.trim()) {
      setError("Please enter both a topic and a question.");
      return;
    }

    setLoading(true);
    setError("");

    try {
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

      const result = await askTutor(
        student,
        topic,
        question
      );

      console.log("TUTOR RESULT:", result);

      setAnswer(result);
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
            based on your learning level and career goal.
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
        </section>
      )}
    </div>
  );
}

export default TutorPage;