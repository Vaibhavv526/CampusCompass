import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { loginUser, registerUser } from "../api/auth";
import "./Auth.css";

function RegisterPage() {
  const navigate = useNavigate();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const handleRegister = async (event) => {
    event.preventDefault();

    setLoading(true);
    setError("");
    setSuccess("");

    try {
      await registerUser(
        fullName,
        email,
        password
      );

      await loginUser(email, password);

      setSuccess(
        "Account created successfully. Redirecting to dashboard..."
      );

      setTimeout(() => {
        navigate("/");
      }, 1000);
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">

        <div className="auth-header">
          <div className="auth-logo">🧠</div>

          <h1>AI Student Mentor</h1>

          <p>
            Create your personalized learning account
          </p>
        </div>

        <form
          className="auth-form"
          onSubmit={handleRegister}
        >

          <div className="auth-field">
            <label>Full Name</label>

            <input
              type="text"
              value={fullName}
              onChange={(event) =>
                setFullName(event.target.value)
              }
              placeholder="Enter your full name"
              required
            />
          </div>

          <div className="auth-field">
            <label>Email</label>

            <input
              type="email"
              value={email}
              onChange={(event) =>
                setEmail(event.target.value)
              }
              placeholder="Enter your email"
              required
            />
          </div>

          <div className="auth-field">
            <label>Password</label>

            <input
              type="password"
              value={password}
              onChange={(event) =>
                setPassword(event.target.value)
              }
              placeholder="Create a password"
              minLength={8}
              required
            />
          </div>

          {error && (
            <div className="auth-error">
              {error}
            </div>
          )}

          {success && (
            <div className="auth-success">
              {success}
            </div>
          )}

          <button
            className="auth-submit-button"
            type="submit"
            disabled={loading}
          >
            {loading
              ? "Creating Account..."
              : "Create Account"}
          </button>

        </form>

        <div className="auth-switch">
          Already have an account?{" "}

          <button
            type="button"
            className="auth-link-button"
            onClick={() => navigate("/login")}
          >
            Login
          </button>
        </div>

      </div>
    </div>
  );
}

export default RegisterPage;