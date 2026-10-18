import { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import {
  generateQuiz,
  evaluateQuiz,
  getStudentProfile,
  getSkills,
  createLearningActivity,
} from "../api/client";
import "./QuizPage.css";

function QuizPage() {
  const navigate = useNavigate();
  const location = useLocation();

  const [topic, setTopic] = useState(() => location.state?.topic || "");
  const [milestone] = useState(() => location.state?.milestone || null);
  const [quiz, setQuiz] = useState(null);
  const [answers, setAnswers] = useState([]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [student, setStudent] = useState(null);
  const [skills, setSkills] = useState([]);

  useEffect(() => {
    const loadStudentData = async () => {
      try {
        const [profile, savedSkills] = await Promise.all([
          getStudentProfile(),
          getSkills(),
        ]);

        setStudent(profile);
        setSkills(savedSkills);
      } catch (error) {
        setError(error.message);
      }
    };

    loadStudentData();
  }, []);

  const quizStudent = student
    ? {
        name: student.full_name,
        email: "",
        degree: student.degree,
        branch: student.branch,
        current_year: student.current_year,
        semester: student.semester,
        career_goal: student.career_goal,
        interests: student.interests
          ? student.interests
              .split(",")
              .map((interest) => interest.trim())
              .filter(Boolean)
          : [],
        weekly_hours: student.weekly_hours || 1,
        skills: skills.map((skill) => ({
          name: skill.name,
          category: "Technical Skill",
          current_level: skill.proficiency,
          target_level: 80,
        })),
      }
    : null;

  const handleGenerateQuiz = async () => {
    if (!quizStudent) {
      setError("Student profile is not loaded yet.");
      return;
    }

    if (!topic.trim()) {
      setError("Please enter a quiz topic.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const generatedQuiz = await generateQuiz(
        quizStudent,
        topic.trim(),
        5
      );

      setQuiz(generatedQuiz);
      setAnswers(
        new Array(generatedQuiz.questions.length).fill("")
      );
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitQuiz = async () => {
    if (!quiz) return;

    const unanswered = answers.some(
      (answer) => !answer
    );

    if (unanswered) {
      setError("Please answer all questions before submitting.");
      return;
    }

    setSubmitting(true);
    setError("");

    try {
      const evaluation = await evaluateQuiz(
        quiz,
        answers
      );

      setResult(evaluation);

      // Persist quiz attempt to learning history (non-blocking)
      try {
        const totalQ = evaluation.total_questions || quiz.questions?.length || 5;
        const correct = evaluation.correct_answers || 0;
        const scoreVal = evaluation.score_percentage !== undefined
          ? evaluation.score_percentage
          : (totalQ > 0 ? (correct / totalQ) * 100 : 0);
        await createLearningActivity({
          activity_type: "quiz",
          title: `Quiz: ${topic.trim()}`,
          summary: `Score: ${correct}/${totalQ} (${Math.round(scoreVal)}%)`,
          score: Math.min(100.0, Math.max(0.0, scoreVal)),
          data: {
            topic: topic.trim(),
            milestone: milestone || null,
            quiz: quiz,
            answers: answers,
            evaluation: evaluation,
          },
        });
      } catch (historyErr) {
        console.warn("Could not persist quiz activity to user history:", historyErr);
      }
    } catch (error) {
      setError(error.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="quiz-page">
      <button
        className="back-button"
        onClick={() => navigate("/")}
      >
        ← Back to Dashboard
      </button>

      <header className="quiz-header">
        <div className="quiz-icon">📝</div>

        <div>
          <p className="eyebrow">AI QUIZ</p>
          <h1>Test Your Knowledge</h1>
          <p>
            Choose a topic and let AI generate an adaptive quiz
            tailored to your roadmap and current skill level.
          </p>
        </div>
      </header>

      {!quiz && (
        <section className="quiz-setup-card">
          <p className="eyebrow">QUIZ TOPIC</p>

          <h2>What do you want to practice?</h2>

          <input
            type="text"
            placeholder="e.g. Python, Machine Learning, DSA"
            value={topic}
            onChange={(event) => setTopic(event.target.value)}
          />

          <button
            onClick={handleGenerateQuiz}
            disabled={loading || !student}
          >
            {loading ? "Generating Quiz..." : "Generate Quiz"}
          </button>
        </section>
      )}

      {error && (
        <div className="quiz-error">
          {error}
        </div>
      )}

      {quiz && !result && (
        <section className="quiz-container">
          <div className="quiz-info">
            <p className="eyebrow">YOUR QUIZ</p>

            <h2>{quiz.topic}</h2>

            <p>
              Difficulty: <strong>{quiz.difficulty}</strong>
            </p>
          </div>

          {quiz.questions.map((question, index) => (
            <div className="quiz-question-card" key={index}>
              <h3>
                {index + 1}. {question.question}
              </h3>

              <div className="quiz-options">
                {question.options.map((option) => (
                  <button
                    key={option}
                    type="button"
                    className={
                      answers[index] === option
                        ? "quiz-option selected"
                        : "quiz-option"
                    }
                    aria-pressed={answers[index] === option}
                    style={{
                      background:
                        answers[index] === option
                          ? "var(--accent-primary)"
                          : "var(--bg-surface)",
                      color:
                        answers[index] === option
                          ? "#ffffff"
                          : "var(--text-primary)",
                      border:
                        answers[index] === option
                          ? "2px solid var(--accent-primary)"
                          : "1px solid var(--border-color)",
                    }}
                    onClick={() => {
                      const updatedAnswers = [...answers];
                      updatedAnswers[index] = option;
                      setAnswers(updatedAnswers);
                    }}
                  >
                    {option}
                  </button>
                ))}
              </div>
            </div>
          ))}
          <div className="quiz-submit-section">
            <button
              className="quiz-submit-button"
              onClick={handleSubmitQuiz}
              disabled={submitting}
            >
              {submitting ? "Evaluating..." : "Submit Quiz"}
            </button>
          </div>
        </section>
      )}

      {result && (
        <section className="quiz-results">
          <p className="eyebrow">QUIZ RESULTS</p>

          <h2>Your Quiz Performance</h2>

          <div className="quiz-score">
            <strong>{result.score_percentage}%</strong>
            <span>
              {result.correct_answers} / {result.total_questions} correct
            </span>
          </div>

          <div className="quiz-recommendation">
            <h3>🎯 Recommendation</h3>
            <p>{result.recommendation}</p>
          </div>

          {result.weak_topics.length > 0 && (
            <div className="quiz-weak-topics">
              <h3>⚠️ Areas to Improve</h3>

              <ul>
                {result.weak_topics.map((weakTopic, index) => (
                  <li key={index} style={{ marginBottom: "8px" }}>
                    <span>{weakTopic}</span>
                    <button
                      type="button"
                      style={{
                        marginLeft: "12px",
                        padding: "3px 8px",
                        fontSize: "0.85rem",
                        cursor: "pointer",
                        borderRadius: "4px",
                        border: "1px solid #2563eb",
                        backgroundColor: "#eff6ff",
                        color: "#1d4ed8",
                      }}
                      onClick={() =>
                        navigate("/tutor", {
                          state: {
                            topic: weakTopic,
                            milestone: milestone || null,
                            question: `Can you explain the key concepts of ${weakTopic} and give examples to help me improve on what I missed in my quiz?`,
                          },
                        })
                      }
                    >
                      Study with AI Tutor →
                    </button>
                  </li>
                ))}
              </ul>

              <div style={{ marginTop: "16px", display: "flex", gap: "10px", flexWrap: "wrap" }}>
                <button
                  type="button"
                  style={{
                    padding: "8px 16px",
                    backgroundColor: "#2563eb",
                    color: "#ffffff",
                    border: "none",
                    borderRadius: "6px",
                    cursor: "pointer",
                    fontWeight: 500,
                  }}
                  onClick={() =>
                    navigate("/tutor", {
                      state: {
                        topic: result.weak_topics[0],
                        milestone: milestone || null,
                        question: `Can you explain the key concepts of ${result.weak_topics[0]} and guide me on how to master them?`,
                      },
                    })
                  }
                >
                  🤖 Study Weak Topics with AI Tutor
                </button>
                <button
                  type="button"
                  style={{
                    padding: "8px 16px",
                    backgroundColor: "#4b5563",
                    color: "#ffffff",
                    border: "none",
                    borderRadius: "6px",
                    cursor: "pointer",
                    fontWeight: 500,
                  }}
                  onClick={() => navigate("/roadmap")}
                >
                  🗺️ Review Roadmap
                </button>
              </div>
            </div>
          )}

          {result.weak_topics.length === 0 && (
            <div style={{ marginTop: "16px", marginBottom: "16px" }}>
              <button
                type="button"
                style={{
                  padding: "8px 16px",
                  backgroundColor: "#059669",
                  color: "#ffffff",
                  border: "none",
                  borderRadius: "6px",
                  cursor: "pointer",
                  fontWeight: 500,
                }}
                onClick={() => navigate("/roadmap")}
              >
                🎉 Continue on Roadmap →
              </button>
            </div>
          )}

          <div className="quiz-question-results">
            <h3>Question Review</h3>

            {result.question_results.map((question, index) => (
              <div
                className={
                  question.is_correct
                    ? "quiz-result-question correct"
                    : "quiz-result-question incorrect"
                }
                key={index}
              >
                <h4>
                  {index + 1}. {question.question}
                </h4>

                <p>
                  <strong>Your answer:</strong>{" "}
                  {question.student_answer}
                </p>

                <p>
                  <strong>Correct answer:</strong>{" "}
                  {question.correct_answer}
                </p>

                <p>{question.explanation}</p>
              </div>
            ))}
          </div>

          <button
            className="quiz-retake-button"
            onClick={() => {
              setQuiz(null);
              setAnswers([]);
              setResult(null);
              setError("");
            }}
          >
            Retake Quiz
          </button>
        </section>
      )}
    </div>
  );
}

export default QuizPage;
