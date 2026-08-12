import { useEffect, useState } from "react";
import "./QuizPage.css";
import { useNavigate } from "react-router-dom";
import {
  generateQuiz,
  evaluateQuiz,
  getStudentProfile,
  getSkills,
} from "../api/client";

function QuizPage() {
  const navigate = useNavigate();

  const [quiz, setQuiz] = useState(null);
  const [answers, setAnswers] = useState([]);
  const [result, setResult] = useState(null);

  const [topic, setTopic] = useState("");
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
  console.log("Submitting quiz:", {
    quiz,
    answers,
  });

  const evaluation = await evaluateQuiz(
    quiz,
    answers
  );

  console.log("Quiz evaluation received:", evaluation);

  setResult(evaluation);
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
          Choose a topic and let AI generate a personalized quiz
          based on your learning level.
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

    {quiz && (
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
                            ? "#2563eb"
                            : "#ffffff",
                        color:
                        answers[index] === option
                            ? "#ffffff"
                            : "#111827",
                        border:
                        answers[index] === option
                            ? "2px solid #2563eb"
                            : "1px solid #d1d5db",
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
          {result.weak_topics.map((topic, index) => (
            <li key={index}>{topic}</li>
          ))}
        </ul>
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