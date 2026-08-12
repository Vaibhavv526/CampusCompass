import { useEffect, useState } from "react";
import "./RecommendationPage.css";
import { useNavigate } from "react-router-dom";
import {
  getStudentProfile,
  getSkills,
  getRecommendations,
} from "../api/client";

function RecommendationPage() {
  const navigate = useNavigate();

  const [student, setStudent] = useState(null);
  const [skills, setSkills] = useState([]);
  const [recommendations, setRecommendations] = useState(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const loadRecommendations = async () => {
      try {
        const [profile, savedSkills] = await Promise.all([
          getStudentProfile(),
          getSkills(),
        ]);

        setStudent(profile);
        setSkills(savedSkills);

        const studentData = {
          name: profile.full_name,
          email: "",
          degree: profile.degree,
          branch: profile.branch,
          current_year: profile.current_year,
          semester: profile.semester,
          career_goal: profile.career_goal,
          interests: profile.interests
            ? profile.interests
                .split(",")
                .map((interest) => interest.trim())
                .filter(Boolean)
            : [],
          weekly_hours: profile.weekly_hours || 1,
          skills: savedSkills.map((skill) => ({
            name: skill.name,
            category: "Technical Skill",
            current_level: skill.proficiency,
            target_level: 80,
          })),
        };

        const result = await getRecommendations(studentData);

        setRecommendations(result);
      } catch (error) {
        setError(error.message);
      } finally {
        setLoading(false);
      }
    };

    loadRecommendations();
  }, []);

  if (loading) {
    return <div>Loading recommendations...</div>;
  }

  if (error) {
    return <div>{error}</div>;
  }

    return (
        <div className="recommendation-page">
            <button
            className="back-button"
            onClick={() => navigate("/")}
            >
            ← Back to Dashboard
            </button>

            <header className="recommendation-header">
            <div className="recommendation-icon">💡</div>

            <p className="recommendation-eyebrow">
                AI RECOMMENDATIONS
            </p>

            <h1>Your Personalized Recommendations</h1>

            <p>
                Personalized skills, projects, resources, and next steps
                based on your current profile and career goal.
            </p>
            </header>

            {recommendations && (
            <>
                <section className="recommendation-summary">
                <h2>Your AI Summary</h2>
                <p>{recommendations.summary}</p>
                </section>

                {recommendations.recommended_skills?.length > 0 && (
                <section className="recommendation-section">
                    <h2>🎯 Recommended Skills</h2>

                    <div className="recommendation-grid">
                    {recommendations.recommended_skills.map(
                        (skill, index) => (
                        <div
                            className="recommendation-card"
                            key={index}
                        >
                            <div className="recommendation-number">
                            {index + 1}
                            </div>

                            <h3>{skill}</h3>
                        </div>
                        )
                    )}
                    </div>
                </section>
                )}

                {recommendations.recommended_projects?.length > 0 && (
                <section className="recommendation-section">
                    <h2>🚀 Recommended Projects</h2>

                    <div className="recommendation-grid">
                    {recommendations.recommended_projects.map(
                        (project, index) => (
                        <div
                            className="recommendation-card"
                            key={index}
                        >
                            <div className="recommendation-number">
                            {index + 1}
                            </div>

                            <h3>{project}</h3>
                        </div>
                        )
                    )}
                    </div>
                </section>
                )}

                {recommendations.recommended_resources?.length > 0 && (
                <section className="recommendation-section">
                    <h2>📚 Recommended Resources</h2>

                    <div className="recommendation-grid">
                    {recommendations.recommended_resources.map(
                        (resource, index) => {
                        const resourceTitle =
                            typeof resource === "string"
                            ? resource
                            : resource.title;

                        const resourceLink =
                            typeof resource === "object"
                            ? resource.link
                            : "";

                        return (
                            <div
                            className="recommendation-card"
                            key={index}
                            >
                            <div className="recommendation-number">
                                {index + 1}
                            </div>

                            <h3>{resourceTitle}</h3>

                            {resourceLink && (
                                <a
                                className="recommendation-resource-link"
                                href={resourceLink}
                                target="_blank"
                                rel="noopener noreferrer"
                                >
                                Open Resource →
                                </a>
                            )}
                            </div>
                        );
                        }
                    )}
                    </div>
                </section>
                )}

                {recommendations.next_steps?.length > 0 && (
                <section className="recommendation-section">
                    <h2>📌 Next Steps</h2>

                    <div className="recommendation-next-steps">
                    {recommendations.next_steps.map((step, index) => (
                        <div
                        className="recommendation-step"
                        key={index}
                        >
                        <span className="recommendation-step-number">
                            {index + 1}.
                        </span>

                        <span>{step}</span>
                        </div>
                    ))}
                    </div>
                </section>
                )}
            </>
            )}
        </div>
        );
}
              

export default RecommendationPage;