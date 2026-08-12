import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { loginUser } from "../api/auth";
import "./Auth.css";

function LoginPage() {
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleLogin = async (event) => {
    event.preventDefault();

    setLoading(true);
    setError("");

    try {
      await loginUser(email, password);

      navigate("/");
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
            Your personalized learning companion
          </p>
        </div>

        <form
          className="auth-form"
          onSubmit={handleLogin}
        >

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
              placeholder="Enter your password"
              required
            />
          </div>

          {error && (
            <div className="auth-error">
              {error}
            </div>
          )}

          <button
            className="auth-submit-button"
            type="submit"
            disabled={loading}
          >
            {loading ? "Logging in..." : "Login"}
          </button>

        </form>

        <div className="auth-switch">
          Don't have an account?{" "}

          <button
            type="button"
            className="auth-link-button"
            onClick={() => navigate("/register")}
          >
            Create Account
          </button>
        </div>

      </div>
    </div>
  );
}

export default LoginPage;