import { getAccessToken } from "./auth";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

async function request(endpoint, options = {}) {
  const token = getAccessToken();
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    headers: {
      "Content-Type": "application/json",

      ...(token
        ? {
            Authorization: `Bearer ${token}`,
          }
        : {}),

      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    const errorText = await response.text();

    throw new Error(
      `API request failed (${response.status}): ${errorText}`
    );
  }

  if (response.status === 204) {
  return null;
  }

  return response.json();
}

export async function checkHealth() {
  return request("/api/health");
}

export async function generateAssessment(student) {
  return request("/api/assessment", {
    method: "POST",
    body: JSON.stringify(student),
  });
}

export async function generateRoadmap(student, assessment) {
  return request("/api/roadmap", {
    method: "POST",
    body: JSON.stringify({
      student,
      assessment,
    }),
  });
}

export async function askTutor(student, topic, question) {
  return request("/api/tutor", {
    method: "POST",
    body: JSON.stringify({
      student,
      topic,
      question,
    }),
  });
}
export async function analyzeSkills(skills) {
  return request("/api/skill-analysis", {
    method: "POST",
    body: JSON.stringify({
      skills,
    }),
  });
}

export async function generateQuiz(student, topic, numQuestions = 5) {
  return request("/api/quiz", {
    method: "POST",
    body: JSON.stringify({
      student,
      topic,
      num_questions: numQuestions,
    }),
  });
}

export async function evaluateQuiz(quiz, studentAnswers) {
  return request("/api/quiz/evaluate", {
    method: "POST",
    body: JSON.stringify({
      quiz,
      student_answers: studentAnswers,
    }),
  });
}

export async function getRecommendations(student) {
  return request("/api/recommendations", {
    method: "POST",
    body: JSON.stringify(student),
  });
}
export async function getSkills() {
  return request("/api/skills");
}

export async function saveSkill(skill) {
  return request("/api/skills", {
    method: "POST",
    body: JSON.stringify(skill),
  });
}
export async function deleteSkill(skillId) {
  return request(`/api/skills/${skillId}`, {
    method: "DELETE",
  });
}

export async function updateSkill(skillId, skill) {
  return request(`/api/skills/${skillId}`, {
    method: "PUT",
    body: JSON.stringify(skill),
  });
}

export async function getStudentProfile() {
  return request("/api/student-profile");
}

export async function createStudentProfile(profile) {
  return request("/api/student-profile", {
    method: "POST",
    body: JSON.stringify(profile),
  });
}
export async function updateStudentProfile(profile) {
  return request("/api/student-profile", {
    method: "PUT",
    body: JSON.stringify(profile),
  });
}


export async function createLearningActivity(activity) {
  return request("/api/learning-history", {
    method: "POST",
    body: JSON.stringify(activity),
  });
}

export async function getLearningHistory(params = {}) {
  const query = new URLSearchParams();
  if (params.activity_type) query.set("activity_type", params.activity_type);
  if (params.limit !== undefined) query.set("limit", params.limit);
  if (params.offset !== undefined) query.set("offset", params.offset);
  const qs = query.toString();
  return request(`/api/learning-history${qs ? `?${qs}` : ""}`);
}

export async function getLearningActivity(activityId) {
  return request(`/api/learning-history/${activityId}`);
}

export async function updateLearningActivity(activityId, updateData) {
  return request(`/api/learning-history/${activityId}`, {
    method: "PATCH",
    body: JSON.stringify(updateData),
  });
}

export async function deleteLearningActivity(activityId) {
  return request(`/api/learning-history/${activityId}`, {
    method: "DELETE",
  });
}
