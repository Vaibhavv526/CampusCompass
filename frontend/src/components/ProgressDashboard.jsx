import "./ProgressDashboard.css";

export function ProgressDashboard({ progress, loading, error, onRefresh, navigate }) {
  if (loading) {
    return (
      <section className="progress-dashboard-container loading" aria-busy="true">
        <div className="progress-loading-spinner" />
        <p>Loading your progress intelligence and analytics...</p>
      </section>
    );
  }

  if (error) {
    return (
      <section className="progress-dashboard-container error">
        <div className="progress-error-banner">
          <span>⚠️ {error}</span>
          <button type="button" onClick={onRefresh} className="progress-retry-btn">
            🔄 Retry
          </button>
        </div>
      </section>
    );
  }

  if (!progress || !progress.has_history || progress.total_activities === 0) {
    return (
      <section className="progress-dashboard-container empty">
        <div className="progress-empty-card">
          <div className="progress-empty-icon">🌱</div>
          <h3>Welcome to Your Learning Dashboard</h3>
          <p>
            Start your learning journey to see real-time skill analytics, score trends,
            and evidence-based recommendations.
          </p>
          <div className="progress-empty-actions">
            <button
              type="button"
              className="progress-action-btn primary"
              onClick={() => navigate("/assessment")}
            >
              📊 Take Initial Skill Assessment
            </button>
            <button
              type="button"
              className="progress-action-btn secondary"
              onClick={() => navigate("/quiz")}
            >
              📝 Take a Diagnostic Quiz
            </button>
          </div>
        </div>
      </section>
    );
  }

  const { quiz_analytics, roadmap_progress, weak_topics, improving_topics, recommended_actions, recent_activities } = progress;

  return (
    <section className="progress-dashboard-container">
      <div className="progress-header">
        <div className="progress-header-title">
          <h2>🎯 Learning Progress & Intelligence</h2>
          <span className="progress-badge-activities">
            {progress.total_activities} activities tracked
          </span>
        </div>
        <button
          type="button"
          onClick={onRefresh}
          className="progress-refresh-btn"
          title="Refresh analytics"
        >
          🔄 Refresh
        </button>
      </div>

      {/* 1. Key Metrics Overview */}
      <div className="progress-metrics-grid">
        {/* Metric 1: Quiz Performance */}
        <div className="progress-metric-card">
          <div className="metric-header">
            <span className="metric-icon">📝</span>
            <span className="metric-label">Quiz Performance</span>
          </div>
          {quiz_analytics.total_attempts > 0 ? (
            <>
              <div className="metric-value-row">
                <span className="metric-value">{Math.round(quiz_analytics.average_score)}%</span>
                <span className="metric-subtext">avg score</span>
              </div>
              <div className="metric-details">
                <span>{quiz_analytics.total_attempts} attempt(s)</span>
                {quiz_analytics.trend === "improving" && (
                  <span className="trend-badge improving" title={`+${quiz_analytics.score_delta}% from first quiz`}>
                    📈 Improving (+{quiz_analytics.score_delta}%)
                  </span>
                )}
                {quiz_analytics.trend === "declining" && (
                  <span className="trend-badge declining" title={`${quiz_analytics.score_delta}% from first quiz`}>
                    📉 Declining ({quiz_analytics.score_delta}%)
                  </span>
                )}
                {quiz_analytics.trend === "steady" && (
                  <span className="trend-badge steady">
                    ➡️ Steady ({quiz_analytics.score_delta > 0 ? `+${quiz_analytics.score_delta}` : quiz_analytics.score_delta}%)
                  </span>
                )}
                {quiz_analytics.trend === "insufficient_data" && (
                  <span className="trend-badge baseline">
                    ⚪ Baseline set
                  </span>
                )}
              </div>
            </>
          ) : (
            <div className="metric-empty-state">
              <span className="metric-empty-text">No quizzes taken yet</span>
              <button
                type="button"
                className="metric-quick-btn"
                onClick={() => navigate("/quiz")}
              >
                Take Diagnostic Quiz →
              </button>
            </div>
          )}
        </div>

        {/* Metric 2: Roadmap Completion */}
        <div className="progress-metric-card">
          <div className="metric-header">
            <span className="metric-icon">🗺️</span>
            <span className="metric-label">Roadmap Milestones</span>
          </div>
          {roadmap_progress && roadmap_progress.has_roadmap ? (
            <>
              <div className="metric-value-row">
                <span className="metric-value">
                  {roadmap_progress.completed_milestones} / {roadmap_progress.total_milestones}
                </span>
                <span className="metric-subtext">
                  ({Math.round(roadmap_progress.completion_percentage)}%)
                </span>
              </div>
              <div className="progress-bar-track">
                <div
                  className="progress-bar-fill"
                  style={{ width: `${Math.min(100, Math.max(0, roadmap_progress.completion_percentage))}%` }}
                />
              </div>
              <div className="metric-details">
                {roadmap_progress.next_milestone ? (
                  <span className="next-milestone-text" title={roadmap_progress.next_milestone}>
                    Next: {roadmap_progress.next_milestone}
                  </span>
                ) : (
                  <span className="milestones-completed-badge">🎉 All milestones complete!</span>
                )}
              </div>
            </>
          ) : (
            <div className="metric-empty-state">
              <span className="metric-empty-text">No active roadmap</span>
              <button
                type="button"
                className="metric-quick-btn"
                onClick={() => navigate("/roadmap")}
              >
                Generate Roadmap →
              </button>
            </div>
          )}
        </div>

        {/* Metric 3: Focus & Skill Areas */}
        <div className="progress-metric-card">
          <div className="metric-header">
            <span className="metric-icon">🎯</span>
            <span className="metric-label">Target Focus Areas</span>
          </div>
          <div className="metric-value-row">
            <span className="metric-value">{weak_topics.length}</span>
            <span className="metric-subtext">focus topic(s)</span>
          </div>
          <div className="metric-details">
            {progress.skill_gaps.length > 0 ? (
              <span>{progress.skill_gaps.length} skill gap(s) identified</span>
            ) : (
              <span>Skills aligned with goals</span>
            )}
          </div>
        </div>
      </div>

      {/* 2. Prioritized Next Steps (Evidence-Based Recommendations) */}
      {recommended_actions && recommended_actions.length > 0 && (
        <div className="progress-recommendations-section">
          <h3>⚡ Recommended Next Steps</h3>
          <div className="progress-recommendations-grid">
            {recommended_actions.map((action, idx) => (
              <div key={idx} className="progress-recommendation-card">
                <div className="rec-card-top">
                  <span className="rec-priority-badge">Step {idx + 1}</span>
                  <span className="rec-type-tag">{action.action_type.replace(/_/g, " ")}</span>
                </div>
                <h4>{action.title}</h4>
                <p>{action.description}</p>
                <button
                  type="button"
                  className="rec-action-button"
                  onClick={() => navigate(action.target_route, { state: action.context })}
                >
                  Start Action →
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 3. Topic Insights: Weak & Improving Topics */}
      {(weak_topics.length > 0 || improving_topics.length > 0) && (
        <div className="progress-topics-section">
          {weak_topics.length > 0 && (
            <div className="topics-block weak-block">
              <h4>⚠️ Topics Needing Review</h4>
              <div className="topic-pills-wrap">
                {weak_topics.map((t, idx) => (
                  <div key={idx} className="topic-pill weak">
                    <span>{t}</span>
                    <button
                      type="button"
                      className="pill-action-btn"
                      title={`Ask AI Tutor about ${t}`}
                      onClick={() =>
                        navigate("/tutor", {
                          state: {
                            topic: t,
                            question: `Can you explain the key concepts of ${t} and clarify common misconceptions?`,
                          },
                        })
                      }
                    >
                      🤖 Ask Tutor
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {improving_topics.length > 0 && (
            <div className="topics-block improving-block">
              <h4>✨ Demonstrated Growth</h4>
              <div className="topic-pills-wrap">
                {improving_topics.map((t, idx) => (
                  <div key={idx} className="topic-pill improving">
                    <span>🎉 {t}</span>
                    <span className="improving-indicator">Higher scores recorded</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* 4. Recent Timeline Preview */}
      {recent_activities && recent_activities.length > 0 && (
        <div className="progress-recent-section">
          <div className="recent-section-header">
            <h4>⏱️ Recent Activity</h4>
            <button
              type="button"
              className="view-all-history-link"
              onClick={() => navigate("/learning-history")}
            >
              View Full History →
            </button>
          </div>
          <div className="recent-activity-list">
            {recent_activities.slice(0, 3).map((act) => (
              <div key={act.id} className="recent-activity-item">
                <span className="activity-type-badge">{act.activity_type}</span>
                <span className="activity-title" title={act.title}>{act.title}</span>
                {act.score !== null && act.score !== undefined && (
                  <span className="activity-score-badge">{Math.round(act.score)}%</span>
                )}
                <span className="activity-date">
                  {new Date(act.created_at).toLocaleDateString(undefined, {
                    month: "short",
                    day: "numeric",
                  })}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

export default ProgressDashboard;
