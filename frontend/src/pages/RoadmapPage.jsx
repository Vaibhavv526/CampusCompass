import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { getCurrentUser } from "../api/auth";
import "./RoadmapPage.css";

function RoadmapPage() {
  const location = useLocation();
  const navigate = useNavigate();

  const roadmap = location.state?.roadmap;
  const student = location.state?.student;
  const [currentUser, setCurrentUser] = useState(null);

    useEffect(() => {
      const loadUser = async () => {
        try {
          const user = await getCurrentUser();
          setCurrentUser(user);
        } catch (error) {
          console.error("Failed to load current user:", error);
        }
      };

      loadUser();
    }, []);
  const [steps, setSteps] = useState([]);

  useEffect(() => {
    if (!currentUser || !roadmap) {
      return;
    }

    const storageKey = `roadmapSteps_${currentUser.id}`;

    const savedSteps = localStorage.getItem(storageKey);

    setSteps(
      savedSteps
        ? JSON.parse(savedSteps)
        : roadmap.steps || []
    );
  }, [currentUser, roadmap]);
 const toggleStep = (index) => {
  setSteps((currentSteps) => {
    const updatedSteps = currentSteps.map((step, stepIndex) =>
      stepIndex === index
        ? {
            ...step,
            completed: !step.completed,
          }
        : step
    );

    if (currentUser) {
      const storageKey = `roadmapSteps_${currentUser.id}`;

      localStorage.setItem(
        storageKey,
        JSON.stringify(updatedSteps)
      );
    }

    return updatedSteps;
  });
};

const completedSteps = steps.filter(
  (step) => step.completed
).length;

const progressPercentage =
  steps.length > 0
    ? Math.round((completedSteps / steps.length) * 100)
    : 0;

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

              <div
                className="roadmap-status"
                onClick={() => toggleStep(index)}
                style={{ cursor: "pointer" }}
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