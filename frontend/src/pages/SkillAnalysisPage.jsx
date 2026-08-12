import { useEffect, useRef, useState } from "react";
import {
  analyzeSkills,
  getSkills,
  saveSkill,
  updateSkill as updateSkillApi,
  deleteSkill as deleteSkillApi,
} from "../api/client";
import { useNavigate } from "react-router-dom";
import "./SkillAnalysisPage.css";

function SkillAnalysisPage() {
  const navigate = useNavigate();

  const [skills, setSkills] = useState([]);

  const [skillInput, setSkillInput] = useState("");

  const [analysis, setAnalysis] = useState(() => {
    const savedAnalysis = localStorage.getItem("skillAnalysis");

    return savedAnalysis ? JSON.parse(savedAnalysis) : null;
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
  const loadSkills = async () => {
    try {
      const savedSkills = await getSkills();
      setSkills(savedSkills);
    } catch (error) {
      setError(error.message);
    }
  };

  loadSkills();
}, []);

  const isInitialLoad = useRef(true);

  useEffect(() => {
    localStorage.setItem("skillInputs", JSON.stringify(skills));

    if (isInitialLoad.current) {
      isInitialLoad.current = false;
      return;
    }

    localStorage.removeItem("skillAnalysis");
    setAnalysis(null);
  }, [skills]);

 const addSkill = async () => {
  const skill = skillInput.trim();

  if (!skill) return;

  if (
    skills.some(
      (item) => item.name.toLowerCase() === skill.toLowerCase()
    )
  ) {
    return;
  }

  const newSkill = {
    name: skill,
    proficiency: 50,
    strengths: "",
    weak_areas: "",
    experience: "",
  };

  try {
    const savedSkill = await saveSkill(newSkill);

    setSkills([...skills, savedSkill]);
    setSkillInput("");
    setError("");
  } catch (error) {
    setError(error.message);
  }
};

  const removeSkill = async (skillName) => {
  const currentSkill = skills.find(
    (skill) => skill.name === skillName
  );

  if (!currentSkill) return;

  try {
    await deleteSkillApi(currentSkill.id);

    setSkills((currentSkills) =>
      currentSkills.filter(
        (skill) => skill.id !== currentSkill.id
      )
    );

    setError("");
  } catch (error) {
    setError(error.message);
  }
};

const updateSkill = (skillName, field, value) => {
  setSkills((currentSkills) =>
    currentSkills.map((skill) =>
      skill.name === skillName
        ? { ...skill, [field]: value }
        : skill
    )
  );
};
const handleSaveChanges = async () => {
  try {
    setLoading(true);
    setError("");

    const updatedSkills = [];

    for (const skill of skills) {
      const savedSkill = await updateSkillApi(
        skill.id,
        {
          name: skill.name,
          proficiency: skill.proficiency,
          strengths: skill.strengths,
          weak_areas: skill.weak_areas,
          experience: skill.experience,
        }
      );

      updatedSkills.push(savedSkill);
    }

    setSkills(updatedSkills);
  } catch (error) {
    setError(error.message);
  } finally {
    setLoading(false);
  }
};

  const handleKeyDown = (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      addSkill();
    }
  };
  const handleAnalyze = async () => {
    if (skills.length === 0) return;

    setLoading(true);
    setError("");

    try {
        const result = await analyzeSkills(skills);

        setAnalysis(result);
        localStorage.setItem("skillAnalysis", JSON.stringify(result));
    } catch (error) {
        setError(error.message);
    } finally {
        setLoading(false);
    }
    };

  return (
    <div className="skill-analysis-page">
      <button
        className="back-button"
        onClick={() => navigate("/")}
      >
        ← Back to Dashboard
      </button>

      <header className="skill-analysis-header">
        <div className="skill-analysis-icon">🧠</div>

        <div>
          <p className="eyebrow">SKILL ANALYSIS</p>

          <h1>Analyze Your Skills</h1>

          <p className="skill-analysis-subtitle">
            Enter your technical skills and let AI identify your
            strengths, weaknesses, and areas for improvement.
          </p>
        </div>
      </header>

      <section className="skill-input-card">
        <p className="eyebrow">YOUR SKILLS</p>

        <h2>What skills do you currently have?</h2>

        <p>
          Add the technical skills you want the AI to analyze.
        </p>

        <div className="skill-input-row">
          <input
            type="text"
            placeholder="e.g. Python"
            value={skillInput}
            onChange={(event) => setSkillInput(event.target.value)}
            onKeyDown={handleKeyDown}
          />

          <button onClick={addSkill}>
            + Add Skill
          </button>
        </div>

        {skills.length > 0 && (
  <div className="selected-skills">
    {skills.map((skill) => (
      <div className="skill-input-card" key={skill.name}>
        <div className="skill-input-card-header">
          <h3>{skill.name}</h3>

          <button
            className="remove-skill-button"
            onClick={() => removeSkill(skill.name)}
            aria-label={`Remove ${skill.name}`}
          >
            ×
          </button>
        </div>

        <div className="skill-field">
          <label>Your proficiency</label>

          <div className="proficiency-options">
            {[20, 40, 60, 80, 100].map((level) => (
              <button
                key={level}
                type="button"
                className={
                  skill.proficiency === level
                    ? "proficiency-option active"
                    : "proficiency-option"
                }
                onClick={() =>
                  updateSkill(
                    skill.name,
                    "proficiency",
                    level
                  )
                }
              >
                {level <= 20
                  ? "Beginner"
                  : level <= 40
                  ? "Basic"
                  : level <= 60
                  ? "Intermediate"
                  : level <= 80
                  ? "Advanced"
                  : "Expert"}
              </button>
            ))}
          </div>
        </div>

        <div className="skill-field">
          <label>What are you good at?</label>

          <textarea
            placeholder="e.g. Python fundamentals, NumPy, Pandas..."
            value={skill.strengths}
            onChange={(event) =>
              updateSkill(
                skill.name,
                "strengths",
                event.target.value
              )
            }
          />
        </div>

        <div className="skill-field">
          <label>What do you struggle with?</label>

          <textarea
            placeholder="e.g. Advanced OOP, async programming..."
            value={skill.weak_areas}
            onChange={(event) =>
              updateSkill(
                skill.name,
                "weak_areas",
                event.target.value
              )
            }
          />
        </div>

        <div className="skill-field">
          <label>Projects / Experience</label>

          <textarea
            placeholder="Describe projects or practical experience..."
            value={skill.experience}
            onChange={(event) =>
              updateSkill(
                skill.name,
                "experience",
                event.target.value
              )
            }
          />
        </div>
      </div>
    ))}
  </div>
)}

        {skills.length === 0 && (
          <div className="skills-empty-state">
            <span>💡</span>
            <p>
              Add skills such as Python, Machine Learning,
              TensorFlow, SQL, or DSA.
            </p>
          </div>
        )}
        <button
          className="save-skills-button"
          onClick={handleSaveChanges}
          disabled={skills.length === 0 || loading}
        >
          {loading ? "Saving..." : "Save Changes"}
        </button>
        <button
            className="analyze-skills-button"
            onClick={handleAnalyze}
            disabled={skills.length === 0 || loading}
            >
            {loading ? "Analyzing..." : "Analyze My Skills"}
            </button>
            </section>

      {error && (
        <div className="skill-analysis-error">
          {error}
        </div>
      )}

      {analysis && (
        <section className="skill-analysis-results">
          <div className="skill-analysis-results-header">
            <p className="eyebrow">AI ANALYSIS</p>

            <h2>Your Skill Analysis</h2>

            <p>{analysis.summary}</p>
          </div>

          <div className="analyzed-skills">
            {analysis.skills.map((skill) => (
              <div className="analyzed-skill-card" key={skill.name}>
                <div className="analyzed-skill-header">
                  <div>
                    <h3>{skill.name}</h3>
                  </div>

                  <div className="proficiency-score">
                    <strong>{skill.proficiency}</strong>
                    <span>/ 100</span>
                  </div>
                </div>

                <div className="proficiency-bar">
                  <div
                    className="proficiency-fill"
                    style={{
                      width: `${skill.proficiency}%`,
                    }}
                  />
                </div>

                <div className="skill-analysis-columns">
                  <div>
                    <h4>✓ Strengths</h4>

                    <ul>
                      {skill.strengths.map((strength, index) => (
                        <li key={index}>{strength}</li>
                      ))}
                    </ul>
                  </div>

                  <div>
                    <h4>⚠ Areas to Improve</h4>

                    <ul>
                      {skill.weak_areas.map((area, index) => (
                        <li key={index}>{area}</li>
                      ))}
                    </ul>
                  </div>
                </div>

                <div className="skill-gap-section">
                  <h4>Skill Gap</h4>

                  <p>{skill.gap}</p>
                </div>

                <div className="next-steps-section">
                  <h4>🎯 Recommended Next Steps</h4>

                  <ol>
                    {skill.next_steps.map((step, index) => (
                      <li key={index}>{step}</li>
                    ))}
                  </ol>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

export default SkillAnalysisPage;