import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  loginUser,
  registerUser,
  getCurrentUser,
} from "../../services/authService";
import { useAuth } from "../context/useAuth";

function AuthPage({ initialMode = "login" }) {
  const [mode, setMode] = useState(initialMode);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const navigate = useNavigate();
  const { setSession } = useAuth();
  const isRegister = mode === "register";

  function changeMode(nextMode) {
    setMode(nextMode);
    setMessage("");
    setShowPassword(false);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setMessage("");

    const formData = new FormData(event.currentTarget);
    const name = String(formData.get("name") || "").trim();
    const email = String(formData.get("email") || "").trim();
    const password = String(formData.get("password") || "");
    const confirmPassword = String(formData.get("confirmPassword") || "");

    if (isRegister && name.length < 2) {
      setMessage("Name must contain at least 2 characters.");
      return;
    }

    if (password.length < 8 || password.length > 128) {
      setMessage("Password must contain 8–128 characters.");
      return;
    }

    if (isRegister && password !== confirmPassword) {
      setMessage("Passwords do not match.");
      return;
    }

    setLoading(true);

    try {
      if (isRegister) {
        await registerUser({ name, email, password });
      }

      const tokenData = await loginUser({ email, password });
      const userData = await getCurrentUser(tokenData.access_token);

      setSession(tokenData.access_token, userData);
      navigate("/dashboard", { replace: true });
    } catch (error) {
      const detail = error.response?.data?.detail;

      if (typeof detail === "string") {
        setMessage(detail);
      } else if (Array.isArray(detail)) {
        setMessage(detail.map((item) => item.msg).join(" "));
      } else {
        setMessage("Unable to connect. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-visual">
        <div className="brand">
          <div className="brand-mark">C</div>
          <span>CareerAI</span>
        </div>

        <div className="visual-copy">
          <div className="eyebrow">YOUR CAREER. YOUR FUTURE.</div>
          <h1>
            Build your future.
            <br />
            <span>Own your journey.</span>
          </h1>
          <p>
            One intelligent platform to understand your strengths, improve your
            skills and prepare for the career you want.
          </p>

          <div className="visual-points">
            <span>Resume insights</span>
            <span>Career guidance</span>
            <span>Skill development</span>
          </div>
        </div>

        <div className="visual-footer">
          CareerAI · Career & Placement Intelligence
        </div>
      </section>

      <section className="auth-panel">
        <div className="auth-card">
          <div className="brand mobile-brand">
            <div className="brand-mark">C</div>
            <span>CareerAI</span>
          </div>

          <div className="auth-heading">
            <h2>{isRegister ? "Create your account" : "Welcome back"}</h2>
            <p>
              {isRegister
                ? "Start building a smarter career plan today."
                : "Sign in to continue your career journey."}
            </p>
          </div>

          <div className="auth-tabs">
            <button
              type="button"
              className={!isRegister ? "active" : ""}
              onClick={() => changeMode("login")}
            >
              Sign In
            </button>
            <button
              type="button"
              className={isRegister ? "active" : ""}
              onClick={() => changeMode("register")}
            >
              Create Account
            </button>
          </div>

          <form className="form-fields" onSubmit={handleSubmit}>
            {isRegister && (
              <div className="field">
                <label htmlFor="name">Full name</label>
                <input
                  id="name"
                  name="name"
                  type="text"
                  placeholder="Enter your full name"
                  minLength={2}
                  maxLength={100}
                  autoComplete="name"
                  required
                />
              </div>
            )}

            <div className="field">
              <label htmlFor="email">Email address</label>
              <input
                id="email"
                name="email"
                type="email"
                placeholder="you@example.com"
                autoComplete="email"
                required
              />
            </div>

            <div className="field">
              <label htmlFor="password">Password</label>
              <div className="password-wrap">
                <input
                  id="password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="Enter your password"
                  minLength={8}
                  maxLength={128}
                  autoComplete={
                    isRegister ? "new-password" : "current-password"
                  }
                  required
                />
                <button
                  type="button"
                  className="password-toggle"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? "Hide" : "Show"}
                </button>
              </div>
            </div>

            {isRegister && (
              <div className="field">
                <label htmlFor="confirmPassword">Confirm password</label>
                <input
                  id="confirmPassword"
                  name="confirmPassword"
                  type={showPassword ? "text" : "password"}
                  placeholder="Re-enter your password"
                  minLength={8}
                  maxLength={128}
                  autoComplete="new-password"
                  required
                />
              </div>
            )}

            {message && (
              <div className="form-message" role="alert">
                {message}
              </div>
            )}

            <button type="submit" className="submit-button" disabled={loading}>
              {loading
                ? "Please wait..."
                : isRegister
                  ? "Create Account →"
                  : "Sign In →"}
            </button>
          </form>

          <div className="auth-legal">
            By continuing, you agree to CareerAI's
            <br />
            <Link to="/terms">Terms of Service</Link> and{" "}
            <Link to="/privacy">Privacy Policy</Link>.
          </div>
        </div>
      </section>
    </main>
  );
}

export default AuthPage;
