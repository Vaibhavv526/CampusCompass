import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { getCurrentUser } from "../api/auth";
import { getLearningHistory, getStudentProfile } from "../api/client";

function AssessmentPage() {
  const location = useLocation();
  const navigate = useNavigate();

  const routerAssessment = location.state?.assessment || null;
  const routerStudent = location.state?.student || null;

  const [assessment, setAssessment] = useState(routerAssessment);
  const [student, setStudent] = useState(routerStudent);
  const [loading, setLoading] = useState(!routerAssessment);

  useEffect(() => {
    let isCancelled = false;

    const restoreAssessmentData = async () => {
      // Restore student profile if absent to display accurate career goal
      if (!routerStudent) {
        try {
          const profile = await getStudentProfile();
          if (!isCancelled && profile) {
            setStudent({
              name: profile.full_name,
              career_goal: profile.career_goal,
              weekly_hours: profile.weekly_hours,
            });
          }
        } catch {
          // Profile restoration optional
        }
      }

      // If already available from router state, restoration complete
      if (routerAssessment) {
        if (!isCancelled) setLoading(false);
        return;
      }

      setLoading(true);

      let currentUser = null;
      try {
        currentUser = await getCurrentUser();
      } catch {
        // User not logged in or token invalid
      }

      let restored = null;

      // 1. Check user-scoped localStorage
      if (currentUser?.id) {
        try {
          const raw = localStorage.getItem(`assessment_${currentUser.id}`);
          if (raw) {
            restored = JSON.parse(raw);
          }
        } catch (e) {
          console.warn("Failed to parse cached assessment from localStorage", e);
        }
      }

      // 2. Fallback: Authenticated learning history
      if (!restored && currentUser) {
        try {
          const historyItems = await getLearningHistory({
            activity_type: "assessment",
            limit: 1,
          });
          if (historyItems && historyItems.length > 0 && historyItems[0].data) {
            restored = historyItems[0].data;
            if (currentUser?.id) {
              try {
                localStorage.setItem(`assessment_${currentUser.id}`, JSON.stringify(restored));
              } catch (e) {
                console.warn("Failed to cache assessment to localStorage", e);
              }
            }
          }
        } catch (err) {
          console.warn("Failed to fetch assessment from learning history", err);
        }
      }

      if (!isCancelled) {
        setAssessment(restored);
        setLoading(false);
      }
    };

    restoreAssessmentData();

    return () => {
      isCancelled = true;
    };
  }, [routerAssessment, routerStudent]);

  if (loading) {
    return (
      <div className="assessment-page">
        <div className="assessment-empty">
          <div className="assessment-empty-icon">⏳</div>
          <h1>Loading Assessment</h1>
          <p>Restoring your personalized skill gap analysis...</p>
        </div>
      </div>
    );
  }

  if (!assessment || !Array.isArray(assessment.skill_gaps)) {
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
    (skill) => (skill.priority || "").toLowerCase() === "high"
  ).length;

  const totalSkillGaps = assessment.skill_gaps.length;
  const careerGoal = student?.career_goal || "AI Engineer";
  const article = careerGoal.match(/^[aeiou]/i) ? "an" : "a";

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
              Your path toward becoming {article}{" "}
              <span>{careerGoal}</span>
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
              const priority = (skill.priority || "medium").toLowerCase();

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
              sequence of learning steps toward your {careerGoal} goal.
            </p>
          </div>

          <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", flexShrink: 0 }}>
            <button
              type="button"
              className="proceed-roadmap-btn"
              onClick={() =>
                navigate("/roadmap", {
                  state: {
                    assessment,
                    student,
                  },
                })
              }
              style={{
                backgroundColor: "#2563eb",
                color: "#ffffff",
                border: "none",
                borderRadius: "8px",
                padding: "12px 20px",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              Proceed to Roadmap →
            </button>
            <button
              type="button"
              className="back-dashboard-btn"
              onClick={() => navigate("/")}
              style={{
                backgroundColor: "#ffffff",
                color: "#101828",
                border: "none",
                borderRadius: "8px",
                padding: "12px 20px",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              ← Back to Dashboard
            </button>
          </div>
        </section>
      </main>
    </div>
  );
}

export default AssessmentPage;
