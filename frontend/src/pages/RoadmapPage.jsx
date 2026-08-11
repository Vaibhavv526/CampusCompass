import { useLocation, useNavigate } from "react-router-dom";
import "./RoadmapPage.css";

function RoadmapPage() {
  const location = useLocation();
  const navigate = useNavigate();

  const roadmap = location.state?.roadmap;
  const student = location.state?.student;

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

      <section className="roadmap-intro">
        <p className="eyebrow">TARGET ROLE</p>

        <h2>
          Your path toward becoming an{" "}
          <span>{roadmap.target_role}</span>
        </h2>

        <p>
          Follow these learning steps in order to gradually build the
          skills required for your career goal.
        </p>
      </section>

      <section className="roadmap-timeline">
        {roadmap.steps.map((step, index) => (
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

              <div className="roadmap-status">
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