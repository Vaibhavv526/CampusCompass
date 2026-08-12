const API_BASE_URL = "http://127.0.0.1:8000";

export async function loginUser(email, password) {
  const formData = new URLSearchParams();

  formData.append("username", email);
  formData.append("password", password);

  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: formData,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(
      `Login failed (${response.status}): ${errorText}`
    );
  }

  const data = await response.json();

  localStorage.setItem("access_token", data.access_token);

  return data;
}

export async function registerUser(
  fullName,
  email,
  password
) {
  const response = await fetch(`${API_BASE_URL}/auth/register`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      full_name: fullName,
      email,
      password,
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(
      `Registration failed (${response.status}): ${errorText}`
    );
  }

  return response.json();
}

export function getAccessToken() {
  return localStorage.getItem("access_token");
}

export function logoutUser() {
  localStorage.removeItem("access_token");
}

export async function getCurrentUser() {
  const token = getAccessToken();

  const response = await fetch(
    `${API_BASE_URL}/auth/me`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );

  if (!response.ok) {
    const errorText = await response.text();

    throw new Error(
      `Failed to get current user (${response.status}): ${errorText}`
    );
  }

  return response.json();
}