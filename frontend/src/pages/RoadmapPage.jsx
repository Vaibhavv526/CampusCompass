import { useState, useEffect, useCallback } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { getCurrentUser } from "../api/auth";
import {
  getLearningHistory,
  updateLearningActivity,
  getStudentProgress,
} from "../api/client";
import "./RoadmapPage.css";

function RoadmapPage() {
  const navigate = useNavigate();
  const location = useLocation();

  const [currentUser, setCurrentUser] = useState(null);
  const initialRoadmap = location.state?.roadmap || null;
  const initialStudent = location.state?.student || null;

  const [roadmap, setRoadmap] = useState(initialRoadmap);
  const [student] = useState(initialStudent);
  const [activityId, setActivityId] = useState(initialRoadmap?._activityId || null);
  const [steps, setSteps] = useState(initialRoadmap?.steps || []);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [progressSummary, setProgressSummary] = useState(null);

  // Helper to merge completion status from localStorage so saved state is never lost
  const mergeSavedCompletion = (baseSteps, userId) => {
    if (!userId || !Array.isArray(baseSteps)) return baseSteps;
    try {
      const storageKey = `roadmapSteps_${userId}`;
      const saved = localStorage.getItem(storageKey);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          return baseSteps.map((step, idx) => {
            const savedStep =
              parsed[idx] || parsed.find((s) => s.title === step.title);
            return savedStep ? { ...step, completed: savedStep.completed } : step;
          });
        }
      }
    } catch (e) {
      console.warn("Failed to merge localStorage steps:", e);
    }
    return baseSteps;
  };

  // Enrich steps with reliable mastery data from progress response
  const enrichStepsWithMastery = (stepsList, masteryMilestones) => {
    if (!Array.isArray(stepsList)) return [];
    if (!Array.isArray(masteryMilestones) || masteryMilestones.length === 0) {
      return stepsList.map((step) => ({
        ...step,
        mastery_status: step.mastery_status || "NOT_STARTED",
        latest_score: step.latest_score ?? null,
        highest_score: step.highest_score ?? null,
        attempt_count: step.attempt_count || 0,
        evidence_source: step.evidence_source || null,
        review_warning: step.review_warning || null,
      }));
    }

    return stepsList.map((step, idx) => {
      const normTitle = (step.title || "").trim().toLowerCase();
      const matched = masteryMilestones.find(
        (m) =>
          m.milestone_index === idx ||
          (m.title || "").trim().toLowerCase() === normTitle
      );

      if (matched) {
        return {
          ...step,
          completed: matched.completed ?? step.completed,
          mastery_status: matched.mastery_status,
          latest_score: matched.latest_score,
          highest_score: matched.highest_score,
          attempt_count: matched.attempt_count,
          evidence_source: matched.evidence_source,
          review_warning: matched.review_warning,
        };
      }

      return {
        ...step,
        mastery_status: "NOT_STARTED",
        latest_score: null,
        highest_score: null,
        attempt_count: 0,
        evidence_source: null,
        review_warning: null,
      };
    });
  };

  const restoreRoadmap = useCallback(
    async (userObj) => {
      setLoading(true);
      setError("");

      try {
        let activeRoadmap = initialRoadmap;
        let actId = initialRoadmap?._activityId || null;

        if (!activeRoadmap) {
          const historyItems = await getLearningHistory({
            activity_type: "roadmap",
            limit: 1,
          });

          if (historyItems && historyItems.length > 0) {
            const latest = historyItems[0];
            actId = latest.id;
            activeRoadmap = latest.data || {};
          }
        }

        if (!activeRoadmap) {
          setRoadmap(null);
          setSteps([]);
          setLoading(false);
          return;
        }

        setRoadmap(activeRoadmap);
        setActivityId(actId);

        let baseSteps = activeRoadmap.steps || [];

        const effectiveUser = userObj || currentUser;
        if (effectiveUser?.id) {
          baseSteps = mergeSavedCompletion(baseSteps, effectiveUser.id);
        }

        let masteryMilestones = [];
        try {
          const progressRes = await getStudentProgress();
          if (progressRes?.roadmap_progress) {
            setProgressSummary(progressRes.roadmap_progress);
            masteryMilestones = progressRes.roadmap_progress.milestones || [];
          }
        } catch (progErr) {
          console.warn("Could not fetch progress intelligence for roadmap mastery:", progErr);
        }

        const enriched = enrichStepsWithMastery(baseSteps, masteryMilestones);
        setSteps(enriched);
      } catch (err) {
        console.error("Failed to load roadmap:", err);
        setError(
          err.message ||
            "Unable to restore your roadmap. Please check your connection and try again."
        );
      } finally {
        setLoading(false);
      }
    },
    [initialRoadmap, currentUser]
  );

  useEffect(() => {
    let isCancelled = false;

    const init = async () => {
      let user = null;
      try {
        user = await getCurrentUser();
        if (!isCancelled) {
          setCurrentUser(user);
        }
      } catch (err) {
        console.warn("User not authenticated or profile error:", err);
      }

      if (!isCancelled) {
        restoreRoadmap(user);
      }
    };

    init();

    return () => {
      isCancelled = true;
    };
  }, [restoreRoadmap]);

  const toggleStep = async (index) => {
    const updatedSteps = steps.map((step, stepIndex) =>
      stepIndex === index
        ? {
            ...step,
            completed: !step.completed,
          }
        : step
    );

    setSteps(updatedSteps);

    const completedStepsCount = updatedSteps.filter(
      (step) => step.completed
    ).length;

    const progressPercentage =
      updatedSteps.length > 0
        ? Math.round((completedStepsCount / updatedSteps.length) * 100)
        : 0;

    if (currentUser?.id) {
      const storageKey = `roadmapSteps_${currentUser.id}`;
      localStorage.setItem(storageKey, JSON.stringify(updatedSteps));
    }

    if (activityId) {
      try {
        const summaryText = `${completedStepsCount} of ${updatedSteps.length} steps completed (${progressPercentage}%)`;
        await updateLearningActivity(activityId, {
          summary: summaryText,
          score: progressPercentage,
          data: {
            ...(roadmap || {}),
            steps: updatedSteps,
          },
        });
      } catch (err) {
        console.warn("Failed to persist milestone update to server:", err);
      }
    }
  };

  const renderMasteryBadge = (step) => {
    const status = step.mastery_status || "NOT_STARTED";

    if (status === "MASTERED") {
      const scoreStr =
        step.latest_score !== null && step.latest_score !== undefined
          ? ` (${Math.round(step.latest_score)}%)`
          : "";
      return (
        <span
          className="mastery-badge badge-mastered"
          title="Mastered based on recorded quiz evidence (latest score >= 70%)"
        >
          ✓ Mastered{scoreStr}
        </span>
      );
    }

    if (status === "NEEDS_REVIEW") {
      const scoreStr =
        step.latest_score !== null && step.latest_score !== undefined
          ? ` (${Math.round(step.latest_score)}%)`
          : "";
      return (
        <span
          className="mastery-badge badge-needs-review"
          title="Review recommended based on quiz performance (< 60% or weak-topic signal)"
        >
          ⚠️ Needs Review{scoreStr}
        </span>
      );
    }

    if (status === "IN_PROGRESS") {
      let scoreDetail = "";
      if (step.latest_score !== null && step.latest_score !== undefined) {
        scoreDetail = ` (${Math.round(step.latest_score)}%)`;
      } else if (step.evidence_source === "tutor") {
        scoreDetail = " (Tutor Session)";
      }
      return (
        <span
          className="mastery-badge badge-in-progress"
          title="Practiced in quiz (60–69%) or active in AI tutor"
        >
          ⏳ In Progress{scoreDetail}
        </span>
      );
    }

    return (
      <span
        className="mastery-badge badge-not-started"
        title="No reliable quiz evidence recorded yet"
      >
        ○ Not Practiced
      </span>
    );
  };

  const completedSteps = steps.filter((step) => step.completed).length;

  const progressPercentage =
    steps.length > 0
      ? Math.round((completedSteps / steps.length) * 100)
      : 0;

  if (loading) {
    return (
      <div className="roadmap-page">
        <button className="back-button" onClick={() => navigate("/")}>
          ← Back to Dashboard
        </button>

        <div className="roadmap-empty">
          <div className="roadmap-empty-icon">⏳</div>
          <h1>Loading Roadmap & Mastery...</h1>
          <p>Restoring your personalized roadmap and milestone mastery progress.</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="roadmap-page">
        <button className="back-button" onClick={() => navigate("/")}>
          ← Back to Dashboard
        </button>

        <div className="roadmap-empty roadmap-error-state">
          <div className="roadmap-empty-icon">⚠️</div>
          <h1>Unable to Load Roadmap</h1>
          <p>{error}</p>

          <div
            style={{
              marginTop: "20px",
              display: "flex",
              gap: "12px",
              justifyContent: "center",
            }}
          >
            <button className="primary-button" onClick={() => restoreRoadmap()}>
              🔄 Try Again
            </button>
            <button
              className="roadmap-dashboard-button"
              onClick={() => navigate("/")}
            >
              Go to Dashboard
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!roadmap || !steps || steps.length === 0) {
    return (
      <div className="roadmap-page">
        <button className="back-button" onClick={() => navigate("/")}>
          ← Back to Dashboard
        </button>

        <div className="roadmap-empty">
          <div className="roadmap-empty-icon">🗺️</div>
          <h1>No Roadmap Available</h1>
          <p>
            Please generate your personalized roadmap from the dashboard first.
          </p>

          <button className="primary-button" onClick={() => navigate("/")}>
            Go to Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="roadmap-page">
      <button className="back-button" onClick={() => navigate("/")}>
        ← Back to Dashboard
      </button>

      <header className="roadmap-page-header">
        <div className="roadmap-icon">🗺️</div>

        <div>
          <p className="eyebrow">PERSONALIZED ROADMAP & MILESTONE MASTERY</p>

          <h1>{roadmap.title}</h1>

          <p className="roadmap-subtitle">
            {student?.name
              ? `${student.name}'s personalized learning path`
              : "Your personalized learning path"}
          </p>
        </div>
      </header>

      <section className="roadmap-progress">
        <div className="roadmap-progress-header">
          <div>
            <p className="eyebrow">YOUR PROGRESS</p>
            <h3>
              {completedSteps} of {steps.length} milestones completed
            </h3>
          </div>

          <strong>{progressPercentage}%</strong>
        </div>

        <div className="roadmap-progress-bar">
          <div
            className="roadmap-progress-fill"
            style={{
              width: `${progressPercentage}%`,
            }}
          />
        </div>

        {progressSummary?.recommended_focus_milestone && (
          <div className="roadmap-focus-banner">
            <span className="focus-tag">🎯 Recommended Focus:</span>
            <span>
              <strong>{progressSummary.recommended_focus_milestone}</strong> — Focus here next to reinforce required skills.
            </span>
          </div>
        )}

        <div className="roadmap-mastery-legend">
          <p className="mastery-disclaimer">
            ℹ️ <strong>Mastery Evidence:</strong> Milestone mastery badges reflect evidence from recorded quiz results and tutor interactions, not proof of long-term retention. Milestone completion remains advisory.
          </p>
        </div>
      </section>

      <section className="roadmap-timeline">
        {steps.map((step, index) => {
          const isFocus =
            progressSummary?.recommended_focus_milestone &&
            progressSummary.recommended_focus_milestone.trim().toLowerCase() ===
              (step.title || "").trim().toLowerCase();

          return (
            <div
              className={`roadmap-item ${isFocus ? "roadmap-item-focus" : ""}`}
              key={index}
            >
              <div className="roadmap-number">{index + 1}</div>

              <div className="roadmap-card">
                <div className="roadmap-card-header">
                  <div>
                    <div className="roadmap-title-row">
                      <h3>{step.title}</h3>
                      {renderMasteryBadge(step)}
                    </div>

                    <div className="roadmap-skills">
                      {step.skills?.map((skill) => (
                        <span key={skill}>{skill}</span>
                      ))}
                    </div>
                  </div>

                  <span className="roadmap-hours">
                    {step.estimated_hours} hrs
                  </span>
                </div>

                <p className="roadmap-description">{step.description}</p>

                {step.attempt_count > 0 && (
                  <div className="mastery-evidence-row">
                    <span className="mastery-evidence-text">
                      📊 Quiz Evidence: {step.attempt_count}{" "}
                      {step.attempt_count === 1 ? "attempt" : "attempts"} | Latest:{" "}
                      {step.latest_score !== null ? `${Math.round(step.latest_score)}%` : "N/A"}{" "}
                      | Highest:{" "}
                      {step.highest_score !== null ? `${Math.round(step.highest_score)}%` : "N/A"}
                    </span>
                  </div>
                )}

                {step.completed && step.mastery_status === "NEEDS_REVIEW" && (
                  <div className="milestone-review-alert" role="alert">
                    <span className="alert-icon">⚠️</span>
                    <div className="alert-content">
                      <strong>Review Warning (Advisory):</strong>
                      <p>
                        You marked this milestone complete, but your recorded quiz results indicate performance below 60% or weak topics. Consider reviewing and retaking the milestone quiz before advancing.
                      </p>
                    </div>
                  </div>
                )}

                <div className="roadmap-actions-row">
                  <button
                    type="button"
                    className="milestone-action-btn milestone-quiz-btn"
                    onClick={() =>
                      navigate("/quiz", {
                        state: {
                          topic: step.title,
                          milestone: step.title,
                          skills: step.skills || [],
                        },
                      })
                    }
                  >
                    📝 Practice in Quiz
                  </button>

                  <button
                    type="button"
                    className="milestone-action-btn milestone-tutor-btn"
                    onClick={() =>
                      navigate("/tutor", {
                        state: {
                          topic: step.title,
                          question: `Can you explain the concepts for "${step.title}" outlined in my roadmap step: "${step.description}"?`,
                        },
                      })
                    }
                  >
                    🤖 Ask Tutor
                  </button>
                </div>

                <div
                  className="roadmap-status"
                  onClick={() => toggleStep(index)}
                  style={{ cursor: "pointer", marginTop: "14px" }}
                >
                  {step.completed ? (
                    <span className="completed">✓ Completed</span>
                  ) : (
                    <span className="not-completed">○ Not completed</span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </section>

      <section className="roadmap-next-section">
        <div>
          <p className="roadmap-next-eyebrow">WHAT'S NEXT?</p>
          <h2>Keep practicing to master each milestone.</h2>
          <p>
            Complete quizzes and engage with the AI Tutor to turn milestones from
            In Progress to Mastered.
          </p>
        </div>

        <button
          className="roadmap-dashboard-button"
          onClick={() => navigate("/")}
        >
          ← Back to Dashboard
        </button>
      </section>
    </div>
  );
}

export default RoadmapPage;
