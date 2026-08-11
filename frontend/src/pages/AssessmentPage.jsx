import { useLocation, useNavigate } from "react-router-dom";

function AssessmentPage() {
  const location = useLocation();
  const navigate = useNavigate();

  const assessment = location.state?.assessment;
  const student = location.state?.student;

  if (!assessment) {
    return (
      <div className="assessment-page">
        <div className="assessment-empty">
          <div className="assessment-empty-icon">📊</div>

          <h1>Assessment Analysis</h1>

          <p>
            No assessment data is available. Please run the assessment
            from the dashboard first.
          </p>

          <button onClick={() => navigate("/")}>
            ← Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  const highPriorityCount = assessment.skill_gaps.filter(
    (skill) => skill.priority.toLowerCase() === "high"
  ).length;

  const totalSkillGaps = assessment.skill_gaps.length;

  return (
    <div className="assessment-page">
      <header className="assessment-page-header">
        <button
          className="back-button"
          onClick={() => navigate("/")}
        >
          ← Dashboard
        </button>

        <div className="assessment-title-section">
          <div className="assessment-title-icon">📊</div>

          <div>
            <h1>Skill Assessment</h1>
            <p>
              Personalized AI analysis for{" "}
              <strong>{student?.name || "Student"}</strong>
            </p>
          </div>
        </div>
      </header>

      <main className="assessment-content">
        <section className="assessment-hero">
          <div>
            <span className="section-label">AI ANALYSIS</span>

            <h2>
              Your path toward becoming an{" "}
              <span>AI Engineer</span>
            </h2>

            <p>
              Our AI analyzed your current skills against your career
              goal and identified the areas that need the most attention.
            </p>
          </div>

          <div className="assessment-summary-stats">
            <div className="summary-stat">
              <strong>{totalSkillGaps}</strong>
              <span>Skills analyzed</span>
            </div>

            <div className="summary-stat">
              <strong>{highPriorityCount}</strong>
              <span>High priority</span>
            </div>

            <div className="summary-stat">
              <strong>{student?.weekly_hours || 0}</strong>
              <span>Hours / week</span>
            </div>
          </div>
        </section>

        <section className="skill-analysis-section">
          <div className="section-heading">
            <div>
              <span className="section-label">SKILL ANALYSIS</span>
              <h2>Your skill gaps</h2>
            </div>

            <p>
              Focus on the skills with the largest gaps and highest
              priority.
            </p>
          </div>

          <div className="assessment-skill-grid">
            {assessment.skill_gaps.map((skill) => {
              const priority = skill.priority.toLowerCase();

              return (
                <article
                  className="assessment-skill-card"
                  key={skill.skill_name}
                >
                  <div className="assessment-skill-card-header">
                    <div>
                      <h3>{skill.skill_name}</h3>
                      <span className={`priority ${priority}`}>
                        {skill.priority}
                      </span>
                    </div>

                    <div className="gap-score">
                      <strong>{skill.gap}</strong>
                      <span>gap</span>
                    </div>
                  </div>

                  <div className="skill-progress-section">
                    <div className="progress-labels">
                      <span>
                        Current <strong>{skill.current_level}</strong>
                      </span>

                      <span>
                        Target <strong>{skill.target_level}</strong>
                      </span>
                    </div>

                    <div className="progress-track">
                      <div
                        className="progress-current"
                        style={{
                          width: `${skill.current_level}%`,
                        }}
                      />

                      <div
                        className="progress-target"
                        style={{
                          left: `${skill.target_level}%`,
                        }}
                      />
                    </div>
                  </div>

                  {skill.task && (
                    <div className="skill-action">
                      <span className="skill-action-icon">🎯</span>

                      <div>
                        <span>Recommended focus</span>
                        <p>{skill.task}</p>
                      </div>
                    </div>
                  )}

                  {skill.timeline && (
                    <div className="skill-timeline">
                      <span>⏱</span>
                      <span>Timeline: {skill.timeline}</span>
                    </div>
                  )}
                </article>
              );
            })}
          </div>
        </section>

        {assessment.recommendations?.length > 0 && (
          <section className="ai-recommendations-section">
            <div className="section-heading">
              <div>
                <span className="section-label">AI GUIDANCE</span>
                <h2>Recommended next steps</h2>
              </div>
            </div>

            <div className="recommendation-grid">
              {assessment.recommendations.map(
                (recommendation, index) => (
                  <article
                    className="ai-recommendation-card"
                    key={index}
                  >
                    <div className="recommendation-number">
                      {String(index + 1).padStart(2, "0")}
                    </div>

                    <div className="recommendation-content">
                      <p>
                        {recommendation.description ||
                          recommendation.task}
                      </p>

                      {recommendation.goal && (
                        <span>
                          Goal: {recommendation.goal}
                        </span>
                      )}

                      {recommendation.timeline && (
                        <span>
                          Timeline: {recommendation.timeline}
                        </span>
                      )}
                    </div>
                  </article>
                )
              )}
            </div>
          </section>
        )}

        <section className="assessment-next-step">
          <div>
            <span className="section-label">WHAT'S NEXT?</span>

            <h2>Turn this analysis into a learning roadmap.</h2>

            <p>
              Use your assessment results to generate a personalized
              sequence of learning steps toward your AI Engineer goal.
            </p>
          </div>

          <button
            onClick={() => navigate("/")}
          >
            ← Back to Dashboard
          </button>
        </section>
      </main>
    </div>
  );
}

export default AssessmentPage;