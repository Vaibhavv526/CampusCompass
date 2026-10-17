import { useEffect, useState, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { getCurrentUser, logoutUser } from "../api/auth";
import { getLearningHistory, getLearningActivity } from "../api/client";
import "./LearningHistoryPage.css";

const PAGE_SIZE = 10;

function formatDateTime(isoString) {
  if (!isoString) return "";
  try {
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return isoString;
    return date.toLocaleString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return isoString;
  }
}

function getActivityTypeMeta(type) {
  switch (type?.toLowerCase()) {
    case "assessment":
      return {
        label: "Skill Assessment",
        icon: "📊",
        badgeClass: "badge-assessment",
      };
    case "quiz":
      return {
        label: "Quiz",
        icon: "📝",
        badgeClass: "badge-quiz",
      };
    case "roadmap":
      return {
        label: "Roadmap",
        icon: "🗺️",
        badgeClass: "badge-roadmap",
      };
    case "tutor":
      return {
        label: "AI Tutor",
        icon: "🤖",
        badgeClass: "badge-tutor",
      };
    default:
      return {
        label: type ? type.charAt(0).toUpperCase() + type.slice(1) : "Activity",
        icon: "💡",
        badgeClass: "badge-generic",
      };
  }
}

function LearningHistoryPage() {
  const navigate = useNavigate();

  const [currentUser, setCurrentUser] = useState(null);
  const [authChecking, setAuthChecking] = useState(true);

  // Filter: "all" | "assessment" | "quiz" | "roadmap"
  const [filter, setFilter] = useState("all");

  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState("");
  const [hasMore, setHasMore] = useState(false);

  // Selected activity modal state
  const [selectedActivity, setSelectedActivity] = useState(null);
  const [modalLoading, setModalLoading] = useState(false);
  const [modalError, setModalError] = useState("");

  // Race-condition safety refs
  const activeRequestIdRef = useRef(0);
  const selectedActivityIdRef = useRef(null);

  // 1. Authenticate user on mount
  useEffect(() => {
    let isCancelled = false;

    const checkAuth = async () => {
      try {
        const user = await getCurrentUser();
        if (!isCancelled) {
          setCurrentUser(user);
          setAuthChecking(false);
        }
      } catch {
        if (!isCancelled) {
          logoutUser();
          setCurrentUser(null);
          navigate("/login");
        }
      }
    };

    checkAuth();

    return () => {
      isCancelled = true;
    };
  }, [navigate]);

  // 2. Fetch learning history (initial or filter change or append)
  const fetchActivities = useCallback(
    async (targetFilter, offset = 0, isAppend = false) => {
      const requestId = isAppend ? activeRequestIdRef.current : ++activeRequestIdRef.current;

      if (!isAppend) {
        setLoading(true);
        setError("");
      } else {
        setLoadingMore(true);
      }

      try {
        const params = {
          limit: PAGE_SIZE,
          offset,
        };
        if (targetFilter && targetFilter !== "all") {
          params.activity_type = targetFilter;
        }

        const data = await getLearningHistory(params);
        if (activeRequestIdRef.current !== requestId) {
          // Stale response from previous filter or cancelled request
          return;
        }

        const fetchedList = Array.isArray(data) ? data : [];

        setActivities((prev) => {
          if (!isAppend) {
            return fetchedList;
          }
          // Deduplicate by ID when appending pages
          const existingIds = new Set(prev.map((item) => item.id));
          const freshItems = fetchedList.filter((item) => !existingIds.has(item.id));
          return [...prev, ...freshItems];
        });

        setHasMore(fetchedList.length === PAGE_SIZE);
      } catch (err) {
        if (activeRequestIdRef.current === requestId) {
          setError(err.message || "Failed to load learning history.");
        }
      } finally {
        if (activeRequestIdRef.current === requestId) {
          setLoading(false);
          setLoadingMore(false);
        }
      }
    },
    []
  );

  // Fetch whenever authenticated user is verified or filter changes
  useEffect(() => {
    let isCancelled = false;
    const reqRef = activeRequestIdRef;

    if (!currentUser?.id) {
      Promise.resolve().then(() => {
        if (!isCancelled) {
          setActivities([]);
          setSelectedActivity(null);
        }
      });
      return () => {
        isCancelled = true;
      };
    }

    Promise.resolve().then(() => {
      if (!isCancelled) {
        setActivities([]);
        setError("");
        setHasMore(false);
        fetchActivities(filter, 0, false);
      }
    });

    return () => {
      isCancelled = true;
      reqRef.current++;
    };
  }, [currentUser?.id, filter, fetchActivities]);

  // Handle Load More
  const handleLoadMore = () => {
    if (loadingMore || !hasMore) return;
    fetchActivities(filter, activities.length, true);
  };

  // Open Activity Details Modal
  const handleOpenDetails = async (activity) => {
    if (!activity?.id) return;
    setSelectedActivity(activity);
    selectedActivityIdRef.current = activity.id;
    setModalLoading(true);
    setModalError("");

    try {
      const fullActivity = await getLearningActivity(activity.id);
      if (selectedActivityIdRef.current === activity.id) {
        setSelectedActivity(fullActivity);
      }
    } catch {
      if (selectedActivityIdRef.current === activity.id) {
        setModalError("Could not refresh full activity details. Showing cached summary.");
      }
    } finally {
      if (selectedActivityIdRef.current === activity.id) {
        setModalLoading(false);
      }
    }
  };

  const handleCloseModal = () => {
    selectedActivityIdRef.current = null;
    setSelectedActivity(null);
    setModalError("");
  };

  // Close modal on escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape" && selectedActivity) {
        handleCloseModal();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [selectedActivity]);

  if (authChecking) {
    return (
      <div className="learning-history-page">
        <div className="history-empty-card">
          <div className="history-empty-icon">⏳</div>
          <h2>Loading Session...</h2>
          <p>Verifying authentication credentials...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="learning-history-page">
      <button className="back-button" onClick={() => navigate("/")}>
        ← Back to Dashboard
      </button>

      <header className="history-header">
        <div className="history-header-icon">📜</div>
        <div className="history-header-content">
          <p className="history-eyebrow">STUDENT LEARNING RECORD</p>
          <h1>Learning History</h1>
          <p className="history-subtitle">
            Review your past skill assessments, quiz results, and personalized roadmaps.
          </p>
        </div>
      </header>

      {/* Filter Tabs & Refresh */}
      <section className="history-filters-bar">
        <div className="history-filter-pills">
          <button
            type="button"
            className={`filter-pill ${filter === "all" ? "active" : ""}`}
            onClick={() => setFilter("all")}
          >
            All Activities
          </button>
          <button
            type="button"
            className={`filter-pill ${filter === "assessment" ? "active" : ""}`}
            onClick={() => setFilter("assessment")}
          >
            📊 Assessments
          </button>
          <button
            type="button"
            className={`filter-pill ${filter === "quiz" ? "active" : ""}`}
            onClick={() => setFilter("quiz")}
          >
            📝 Quizzes
          </button>
          <button
            type="button"
            className={`filter-pill ${filter === "roadmap" ? "active" : ""}`}
            onClick={() => setFilter("roadmap")}
          >
            🗺️ Roadmaps
          </button>
        </div>

        <button
          type="button"
          className="refresh-button"
          onClick={() => fetchActivities(filter, 0, false)}
          disabled={loading}
          title="Refresh learning history"
        >
          🔄 Refresh
        </button>
      </section>

      {/* Error state */}
      {error && (
        <div className="history-error-banner">
          <div className="error-message-text">
            <strong>Unable to load activities:</strong> {error}
          </div>
          <button
            type="button"
            className="retry-button"
            onClick={() => fetchActivities(filter, 0, false)}
          >
            Retry
          </button>
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div className="history-loading-container">
          <div className="history-spinner" />
          <p>Loading your learning history...</p>
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && activities.length === 0 && (
        <div className="history-empty-card">
          <div className="history-empty-icon">📜</div>
          <h2>No Learning History Yet</h2>
          <p>
            {filter === "all"
              ? "You haven't completed any assessments, quizzes, or generated roadmaps yet. Start learning to build your personal history!"
              : `You haven't recorded any ${filter} activities yet.`}
          </p>
          <div className="empty-actions-row">
            <button
              type="button"
              className="primary-button"
              onClick={() => navigate("/")}
            >
              Start an Activity
            </button>
            <button
              type="button"
              className="secondary-button"
              onClick={() => navigate("/quiz")}
            >
              Take a Quiz
            </button>
          </div>
        </div>
      )}

      {/* Activities Grid */}
      {!loading && activities.length > 0 && (
        <>
          <div className="history-cards-grid">
            {activities.map((activity) => {
              const meta = getActivityTypeMeta(activity.activity_type);
              const hasScore = activity.score !== null && activity.score !== undefined;
              const scoreNum = hasScore ? Math.round(activity.score) : null;

              return (
                <div className="history-activity-card" key={activity.id}>
                  <div className="card-top-row">
                    <span className={`activity-badge ${meta.badgeClass}`}>
                      <span>{meta.icon}</span> {meta.label}
                    </span>
                    <span className="activity-timestamp">
                      {formatDateTime(activity.created_at)}
                    </span>
                  </div>

                  <h3 className="activity-title">{activity.title}</h3>

                  {activity.summary && (
                    <p className="activity-summary">{activity.summary}</p>
                  )}

                  <div className="card-bottom-row">
                    {hasScore ? (
                      <div className="activity-score-chip">
                        <span className="score-label">Score / Progress</span>
                        <strong
                          className={`score-value ${
                            scoreNum >= 80
                              ? "score-high"
                              : scoreNum >= 50
                              ? "score-mid"
                              : "score-low"
                          }`}
                        >
                          {scoreNum}%
                        </strong>
                      </div>
                    ) : (
                      <div className="activity-type-tag">
                        <span>Status: Completed</span>
                      </div>
                    )}

                    <button
                      type="button"
                      className="view-details-button"
                      onClick={() => handleOpenDetails(activity)}
                    >
                      View Details →
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Load More Button */}
          {hasMore && (
            <div className="load-more-container">
              <button
                type="button"
                className="load-more-button"
                onClick={handleLoadMore}
                disabled={loadingMore}
              >
                {loadingMore ? "Loading more..." : "Load More Activities"}
              </button>
            </div>
          )}
        </>
      )}

      {/* Modal / Activity Details View */}
      {selectedActivity && (
        <div className="history-modal-overlay" onClick={handleCloseModal}>
          <div
            className="history-modal-card"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="modal-title"
          >
            <div className="modal-header">
              <div className="modal-header-meta">
                <span
                  className={`activity-badge ${
                    getActivityTypeMeta(selectedActivity.activity_type).badgeClass
                  }`}
                >
                  <span>
                    {getActivityTypeMeta(selectedActivity.activity_type).icon}
                  </span>{" "}
                  {getActivityTypeMeta(selectedActivity.activity_type).label}
                </span>
                <span className="modal-timestamp">
                  {formatDateTime(selectedActivity.created_at)}
                </span>
              </div>
              <button
                type="button"
                className="modal-close-button"
                onClick={handleCloseModal}
                aria-label="Close modal"
              >
                ×
              </button>
            </div>

            <h2 id="modal-title" className="modal-title">
              {selectedActivity.title}
            </h2>

            {modalLoading && (
              <p className="modal-refreshing-hint">Refreshing details from server...</p>
            )}
            {modalError && (
              <p className="modal-error-hint">{modalError}</p>
            )}

            {selectedActivity.summary && (
              <div className="modal-summary-box">
                <strong>Summary:</strong> {selectedActivity.summary}
              </div>
            )}

            <div className="modal-body-content">
              {/* Type-Specific Details Render */}
              <ActivityDetailContent
                activity={selectedActivity}
                navigate={navigate}
                onClose={handleCloseModal}
              />
            </div>

            <div className="modal-footer">
              <button
                type="button"
                className="modal-secondary-button"
                onClick={handleCloseModal}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Type-specific breakdown of the activity payload data
 */
function ActivityDetailContent({ activity, navigate, onClose }) {
  const { activity_type, data, score } = activity;

  if (!data || Object.keys(data).length === 0) {
    return (
      <div className="empty-details-box">
        <p>No detailed result payload was stored for this activity record.</p>
      </div>
    );
  }

  // 1. QUIZ DETAILS
  if (activity_type === "quiz") {
    const evaluation = data.evaluation || {};
    const feedbackList = evaluation.feedback || [];
    const questions = data.quiz?.questions || [];
    const answers = data.answers || [];

    const totalQ = evaluation.total_questions || questions.length || 0;
    const correctQ = evaluation.correct_answers ?? (score !== null && score !== undefined ? Math.round((score / 100) * totalQ) : 0);
    const scorePct = evaluation.score_percentage ?? (score !== null && score !== undefined ? Math.round(score) : null);

    return (
      <div className="detail-section quiz-detail-section">
        <div className="quiz-score-banner">
          <div className="score-stat">
            <span className="score-stat-label">Topic</span>
            <strong>{data.topic || data.quiz?.topic || "General"}</strong>
          </div>
          <div className="score-stat">
            <span className="score-stat-label">Score</span>
            <strong className="score-stat-value">
              {correctQ} / {totalQ} ({scorePct ?? 0}%)
            </strong>
          </div>
        </div>

        {feedbackList.length > 0 ? (
          <div className="quiz-questions-review">
            <h4>Question Breakdown:</h4>
            {feedbackList.map((item, idx) => (
              <div
                key={idx}
                className={`quiz-feedback-card ${
                  item.is_correct ? "correct" : "incorrect"
                }`}
              >
                <div className="question-header">
                  <span className="question-number">Q{idx + 1}</span>
                  <span className="question-text">{item.question}</span>
                  <span
                    className={`status-pill ${
                      item.is_correct ? "status-correct" : "status-incorrect"
                    }`}
                  >
                    {item.is_correct ? "✓ Correct" : "✗ Incorrect"}
                  </span>
                </div>

                <div className="answer-comparison">
                  <div className="answer-item">
                    <span>Your Answer:</span>{" "}
                    <strong>{item.student_answer || "(None)"}</strong>
                  </div>
                  {!item.is_correct && item.correct_answer && (
                    <div className="answer-item correct-answer">
                      <span>Correct Answer:</span>{" "}
                      <strong>{item.correct_answer}</strong>
                    </div>
                  )}
                </div>

                {item.explanation && (
                  <p className="explanation-text">
                    💡 <em>{item.explanation}</em>
                  </p>
                )}
              </div>
            ))}
          </div>
        ) : questions.length > 0 ? (
          <div className="quiz-questions-review">
            <h4>Questions:</h4>
            {questions.map((q, idx) => (
              <div key={idx} className="quiz-feedback-card">
                <div className="question-header">
                  <span className="question-number">Q{idx + 1}</span>
                  <span className="question-text">{q.question}</span>
                </div>
                <div className="answer-comparison">
                  <div className="answer-item">
                    <span>Selected Answer:</span>{" "}
                    <strong>{answers[idx] || "(Not recorded)"}</strong>
                  </div>
                  {q.correct_answer && (
                    <div className="answer-item correct-answer">
                      <span>Correct Answer:</span>{" "}
                      <strong>{q.correct_answer}</strong>
                    </div>
                  )}
                </div>
                {q.explanation && (
                  <p className="explanation-text">💡 {q.explanation}</p>
                )}
              </div>
            ))}
          </div>
        ) : null}
      </div>
    );
  }

  // 2. ASSESSMENT DETAILS
  if (activity_type === "assessment") {
    const summaryText = data.summary || "";
    const skillGaps = Array.isArray(data.skill_gaps) ? data.skill_gaps : [];
    const recommendations = Array.isArray(data.recommendations)
      ? data.recommendations
      : typeof data.recommendations === "string"
      ? [{ task: data.recommendations }]
      : [];

    return (
      <div className="detail-section assessment-detail-section">
        {summaryText && (
          <div className="assessment-overview-card">
            <h4>Assessment Overview</h4>
            <p>{summaryText}</p>
          </div>
        )}

        {skillGaps.length > 0 && (
          <div className="skill-gaps-section">
            <h4>Identified Skill Gaps ({skillGaps.length}):</h4>
            <div className="skill-gaps-list">
              {skillGaps.map((gapItem, idx) => {
                const priority = (gapItem.priority || "Medium").toString();
                const prioLower = priority.toLowerCase();
                const prioClass =
                  prioLower === "high" || prioLower === "1"
                    ? "prio-high"
                    : prioLower === "medium" || prioLower === "2"
                    ? "prio-med"
                    : "prio-low";

                return (
                  <div className="skill-gap-item" key={idx}>
                    <div className="skill-gap-header">
                      <strong>{gapItem.skill_name || `Skill #${idx + 1}`}</strong>
                      <span className={`priority-badge ${prioClass}`}>
                        {priority} Priority
                      </span>
                    </div>

                    <div className="skill-levels-row">
                      <div className="level-bar-container">
                        <span className="level-label">
                          Current: {gapItem.current_level ?? "N/A"}%
                        </span>
                        <div className="level-track">
                          <div
                            className="level-fill current"
                            style={{ width: `${Math.min(100, Math.max(0, gapItem.current_level || 0))}%` }}
                          />
                        </div>
                      </div>

                      <div className="level-bar-container">
                        <span className="level-label">
                          Target: {gapItem.target_level ?? "N/A"}%
                        </span>
                        <div className="level-track">
                          <div
                            className="level-fill target"
                            style={{ width: `${Math.min(100, Math.max(0, gapItem.target_level || 0))}%` }}
                          />
                        </div>
                      </div>
                    </div>

                    {gapItem.gap !== undefined && (
                      <p className="gap-metric">
                        Proficiency Gap: <strong>{gapItem.gap}%</strong>
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {recommendations.length > 0 && (
          <div className="recommendations-section">
            <h4>Actionable Recommendations:</h4>
            <div className="recommendations-list">
              {recommendations.map((rec, idx) => (
                <div className="recommendation-card" key={idx}>
                  <h5>🎯 Action Item #{idx + 1}</h5>
                  {rec.task && <p className="rec-task"><strong>Task:</strong> {rec.task}</p>}
                  {rec.resources && (
                    <p className="rec-resources">
                      <strong>Resources:</strong> {rec.resources}
                    </p>
                  )}
                  {rec.timeline && (
                    <p className="rec-timeline">
                      <strong>Timeline:</strong> {rec.timeline}
                    </p>
                  )}
                  {!rec.task && !rec.resources && !rec.timeline && (
                    <p>{typeof rec === "string" ? rec : JSON.stringify(rec)}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  // 3. ROADMAP DETAILS
  if (activity_type === "roadmap") {
    const steps = Array.isArray(data.steps) ? data.steps : [];
    const completedCount = steps.filter((s) => s.completed).length;
    const progressPct =
      steps.length > 0
        ? Math.round((completedCount / steps.length) * 100)
        : score !== null && score !== undefined
        ? Math.round(score)
        : 0;

    return (
      <div className="detail-section roadmap-detail-section">
        <div className="roadmap-progress-header">
          <div className="roadmap-progress-stats">
            <span>Overall Milestone Completion:</span>
            <strong>
              {completedCount} of {steps.length} steps ({progressPct}%)
            </strong>
          </div>
          <div className="roadmap-progress-track">
            <div
              className="roadmap-progress-fill"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>

        {steps.length > 0 && (
          <div className="roadmap-milestones-list">
            <h4>Milestones ({steps.length}):</h4>
            {steps.map((step, idx) => (
              <div
                key={idx}
                className={`milestone-item ${step.completed ? "completed" : ""}`}
              >
                <div className="milestone-item-header">
                  <span className="milestone-status-icon">
                    {step.completed ? "✓" : "○"}
                  </span>
                  <span className="milestone-title">
                    Step {idx + 1}: {step.title}
                  </span>
                  <span
                    className={`milestone-badge ${
                      step.completed ? "status-done" : "status-todo"
                    }`}
                  >
                    {step.completed ? "Completed" : "In Progress"}
                  </span>
                </div>

                {step.description && (
                  <p className="milestone-desc">{step.description}</p>
                )}

                {Array.isArray(step.skills) && step.skills.length > 0 && (
                  <div className="milestone-skills">
                    {step.skills.map((skill, sIdx) => (
                      <span className="skill-chip" key={sIdx}>
                        {skill}
                      </span>
                    ))}
                  </div>
                )}

                {step.estimated_time && (
                  <p className="milestone-time">
                    ⏱️ Estimated Time: {step.estimated_time}
                  </p>
                )}

                {Array.isArray(step.resources) && step.resources.length > 0 && (
                  <div className="milestone-resources">
                    <strong>Recommended Resources:</strong>
                    <ul>
                      {step.resources.map((res, rIdx) => (
                        <li key={rIdx}>{res}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        <div className="roadmap-open-action">
          <button
            type="button"
            className="primary-button"
            onClick={() => {
              onClose();
              navigate("/roadmap", {
                state: {
                  roadmap: {
                    ...(data || {}),
                    _activityId: activity.id,
                  },
                },
              });
            }}
          >
            🗺️ Open in Interactive Roadmap View
          </button>
        </div>
      </div>
    );
  }

  // 4. GENERIC / FALLBACK
  return (
    <div className="detail-section generic-detail-section">
      <h4>Activity Result Data:</h4>
      <pre className="generic-json-preview">
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
}

export default LearningHistoryPage;
