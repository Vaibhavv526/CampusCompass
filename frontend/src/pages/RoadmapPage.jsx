import { useState, useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { getCurrentUser } from "../api/auth";
import { getLearningHistory, updateLearningActivity } from "../api/client";
import "./RoadmapPage.css";

function RoadmapPage() {
  const navigate = useNavigate();
  const location = useLocation();

  const [currentUser, setCurrentUser] = useState(null);
  const initialRoadmap = location.state?.roadmap || null;
  const initialStudent = location.state?.student || null;

  const [roadmap, setRoadmap] = useState(initialRoadmap);
  const [student, setStudent] = useState(initialStudent);
  const [activityId, setActivityId] = useState(initialRoadmap?._activityId || null);
  const [steps, setSteps] = useState(initialRoadmap?.steps || []);
  const [loading, setLoading] = useState(!initialRoadmap);

  useEffect(() => {
    let isCancelled = false;

    const loadUser = async () => {
      try {
        const user = await getCurrentUser();
        if (!isCancelled) {
          setCurrentUser(user);
        }
      } catch (error) {
        console.error("Failed to load current user:", error);
      }
    };

    loadUser();

    return () => {
      isCancelled = true;
    };
  }, []);

  // Restore roadmap from persistent learning history if not passed in location.state (e.g., page refresh)
  useEffect(() => {
    let isCancelled = false;

    const restoreRoadmap = async () => {
      if (initialRoadmap) {
        setRoadmap(initialRoadmap);
        if (initialRoadmap._activityId) {
          setActivityId(initialRoadmap._activityId);
        }
        setSteps(initialRoadmap.steps || []);
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        const historyItems = await getLearningHistory({
          activity_type: "roadmap",
          limit: 1,
        });

        if (!isCancelled && historyItems && historyItems.length > 0) {
          const latest = historyItems[0];
          setActivityId(latest.id);
          const roadmapData = latest.data || {};
          setRoadmap(roadmapData);
          setSteps(roadmapData.steps || []);
        }
      } catch (err) {
        console.warn("Could not restore roadmap from learning history:", err);
      } finally {
        if (!isCancelled) {
          setLoading(false);
        }
      }
    };

    restoreRoadmap();

    return () => {
      isCancelled = true;
    };
  }, [initialRoadmap]);

  // Load user-specific steps overlay from localStorage if present
  useEffect(() => {
    if (!currentUser || !roadmap) {
      return;
    }

    const storageKey = `roadmapSteps_${currentUser.id}`;
    const savedSteps = localStorage.getItem(storageKey);

    if (savedSteps) {
      try {
        const parsed = JSON.parse(savedSteps);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setSteps(parsed);
        }
      } catch (e) {
        console.error("Failed to parse saved steps:", e);
      }
    }
  }, [currentUser, roadmap]);

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

    if (currentUser) {
      const storageKey = `roadmapSteps_${currentUser.id}`;
      localStorage.setItem(
        storageKey,
        JSON.stringify(updatedSteps)
      );
    }

    // Persist milestone change to existing learning activity record (non-blocking, no duplicate entries)
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

  const completedSteps = steps.filter(
    (step) => step.completed
  ).length;

  const progressPercentage =
    steps.length > 0
      ? Math.round((completedSteps / steps.length) * 100)
      : 0;

  if (loading) {
    return (
      <div className="roadmap-page">
        <button
          className="back-button"
          onClick={() => navigate("/")}
        >
          ← Back to Dashboard
        </button>

        <div className="roadmap-empty">
          <div className="roadmap-empty-icon">⏳</div>
          <h1>Loading Roadmap...</h1>
          <p>Restoring your personalized roadmap and milestone progress.</p>
        </div>
      </div>
    );
  }

  if (!roadmap) {
    return (
      <div className="roadmap-page">
        <button
          className="back-button"
          onClick={() => navigate("/")}
        >
          ← Back to Dashboard
        </button>

        <div className="roadmap-empty">
          <div className="roadmap-empty-icon">🗺️</div>
          <h1>No Roadmap Available</h1>
          <p>
            Please generate your personalized roadmap from the dashboard
            first.
          </p>

          <button
            className="back-button"
            onClick={() => navigate("/")}
          >
            Go to Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="roadmap-page">
      <button
        className="back-button"
        onClick={() => navigate("/")}
      >
        ← Back to Dashboard
      </button>

      <header className="roadmap-page-header">
        <div className="roadmap-icon">🗺️</div>

        <div>
          <p className="eyebrow">PERSONALIZED ROADMAP</p>

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
              {completedSteps} of {steps.length} steps completed
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
      </section>

      <section className="roadmap-timeline">
        {steps.map((step, index) => (
          <div className="roadmap-item" key={index}>
            <div className="roadmap-number">
              {index + 1}
            </div>

            <div className="roadmap-card">
              <div className="roadmap-card-header">
                <div>
                  <h3>{step.title}</h3>

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

              <p className="roadmap-description">
                {step.description}
              </p>

              <div style={{ marginTop: "10px", display: "flex", gap: "8px", flexWrap: "wrap", alignItems: "center" }}>
                <button
                  type="button"
                  style={{
                    padding: "4px 10px",
                    fontSize: "0.82rem",
                    borderRadius: "4px",
                    border: "1px solid #2563eb",
                    backgroundColor: "#eff6ff",
                    color: "#1d4ed8",
                    cursor: "pointer",
                    fontWeight: 500,
                  }}
                  onClick={() =>
                    navigate("/quiz", {
                      state: { topic: step.title },
                    })
                  }
                >
                  📝 Practice in Quiz
                </button>
                <button
                  type="button"
                  style={{
                    padding: "4px 10px",
                    fontSize: "0.82rem",
                    borderRadius: "4px",
                    border: "1px solid #059669",
                    backgroundColor: "#ecfdf5",
                    color: "#047857",
                    cursor: "pointer",
                    fontWeight: 500,
                  }}
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
                style={{ cursor: "pointer", marginTop: "12px" }}
              >
                {step.completed ? (
                  <span className="completed">
                    ✓ Completed
                  </span>
                ) : (
                  <span className="not-completed">
                    ○ Not completed
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
      </section>

      <section className="roadmap-next-section">
        <div>
          <p className="roadmap-next-eyebrow">WHAT'S NEXT?</p>

          <h2>Turn this analysis into a learning roadmap.</h2>

          <p>
            Use your assessment results to generate a personalized sequence
            of learning steps toward your AI Engineer goal.
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
