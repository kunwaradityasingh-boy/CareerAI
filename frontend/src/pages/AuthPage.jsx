import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";

import {
  loginUser,
  registerUser,
  verifyRegistration,
  resendRegistrationOtp,
  getCurrentUser,
} from "../../services/authService";

import { useAuth } from "../context/useAuth";

const PENDING_EMAIL_STORAGE_KEY = "careerai_pending_email";

function getInitialPendingEmail(initialMode) {
  try {
    if (initialMode === "register") {
      return sessionStorage.getItem(PENDING_EMAIL_STORAGE_KEY) || "";
    }
  } catch {
    // Storage unavailable
  }
  return "";
}

function AuthPage({ initialMode = "login" }) {
  const [initialPending] = useState(() => getInitialPendingEmail(initialMode));

  const [mode, setMode] = useState(initialMode);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(
    initialPending ? "Please enter the 6-digit code sent to your email." : "",
  );

  const [registrationStep, setRegistrationStep] = useState(
    initialPending ? "otp" : "details",
  );
  const [pendingEmail, setPendingEmail] = useState(initialPending);
  const [registrationPassword, setRegistrationPassword] = useState("");
  const [resendCooldown, setResendCooldown] = useState(0);

  const navigate = useNavigate();
  const { setSession } = useAuth();

  const isRegister = mode === "register";
  const isOtpStep = registrationStep === "otp";

  useEffect(() => {
    if (resendCooldown <= 0) return;

    const timer = setInterval(() => {
      setResendCooldown((prev) => (prev <= 1 ? 0 : prev - 1));
    }, 1000);

    return () => clearInterval(timer);
  }, [resendCooldown]);

  function changeMode(nextMode) {
    setMode(nextMode);
    setRegistrationStep("details");
    setPendingEmail("");
    setRegistrationPassword("");
    setMessage("");
    setShowPassword(false);
    setResendCooldown(0);

    try {
      sessionStorage.removeItem(PENDING_EMAIL_STORAGE_KEY);
    } catch {
      // Storage unavailable
    }
  }

  function getErrorMessage(error, fallback) {
    const detail = error.response?.data?.detail;

    if (typeof detail === "string") {
      return detail;
    }

    if (Array.isArray(detail)) {
      return detail.map((item) => item.msg).join(" ");
    }

    return fallback;
  }

  async function createSession(email, password) {
    const tokenData = await loginUser({ email, password });

    const userData = await getCurrentUser(tokenData.access_token);

    setSession(tokenData.access_token, userData);

    setRegistrationPassword("");
    setPendingEmail("");

    navigate("/dashboard", { replace: true });
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
        const result = await registerUser({
          name,
          email,
          password,
        });

        setPendingEmail(email);
        setRegistrationPassword(password);
        setRegistrationStep("otp");
        setResendCooldown(60);

        try {
          sessionStorage.setItem(PENDING_EMAIL_STORAGE_KEY, email);
        } catch {
          // Storage unavailable
        }

        setMessage(result.message || "OTP sent. Please check your email.");
        return;
      }

      await createSession(email, password);
    } catch (error) {
      setMessage(
        getErrorMessage(error, "Unable to connect. Please try again."),
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleResendOtp() {
    if (!pendingEmail || loading || resendCooldown > 0) return;

    setLoading(true);
    setMessage("");

    try {
      const result = await resendRegistrationOtp({ email: pendingEmail });
      setMessage(result.message || "A new verification code has been sent.");
      setResendCooldown(60);
    } catch (error) {
      setMessage(
        getErrorMessage(error, "Failed to resend code. Please try again."),
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleOtpSubmit(event) {
    event.preventDefault();
    setMessage("");

    const formData = new FormData(event.currentTarget);
    const otp = String(formData.get("otp") || "").trim();

    if (!/^[0-9]{6}$/.test(otp)) {
      setMessage("Please enter a valid 6-digit OTP.");
      return;
    }

    setLoading(true);

    let verificationSucceeded = false;

    try {
      await verifyRegistration({
        email: pendingEmail,
        otp,
      });

      verificationSucceeded = true;

      try {
        sessionStorage.removeItem(PENDING_EMAIL_STORAGE_KEY);
      } catch {
        // Storage unavailable
      }

      await createSession(pendingEmail, registrationPassword);
    } catch (error) {
      if (verificationSucceeded) {
        setMode("login");
        setRegistrationStep("details");
        setRegistrationPassword("");

        setMessage(
          "Email verified successfully. Please sign in with your email and password.",
        );
      } else {
        setMessage(
          getErrorMessage(error, "OTP verification failed. Please try again."),
        );
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
            <h2>
              {isOtpStep
                ? "Verify your email"
                : isRegister
                  ? "Create your account"
                  : "Welcome back"}
            </h2>

            <p>
              {isOtpStep
                ? `Enter the 6-digit code sent to ${pendingEmail}.`
                : isRegister
                  ? "Start building a smarter career plan today."
                  : "Sign in to continue your career journey."}
            </p>
          </div>

          {!isOtpStep && (
            <div className="auth-tabs">
              <button
                type="button"
                className={!isRegister ? "active" : ""}
                onClick={() => changeMode("login")}
                disabled={loading}
              >
                Sign In
              </button>

              <button
                type="button"
                className={isRegister ? "active" : ""}
                onClick={() => changeMode("register")}
                disabled={loading}
              >
                Create Account
              </button>
            </div>
          )}

          {isOtpStep ? (
            <form className="form-fields" onSubmit={handleOtpSubmit}>
              <div className="field">
                <label htmlFor="otp">Email verification code</label>

                <input
                  id="otp"
                  name="otp"
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]{6}"
                  minLength={6}
                  maxLength={6}
                  placeholder="Enter 6-digit OTP"
                  autoComplete="one-time-code"
                  required
                  autoFocus
                />
              </div>

              {message && (
                <div className="form-message" role="alert">
                  {message}
                </div>
              )}

              <button
                type="submit"
                className="submit-button"
                disabled={loading}
              >
                {loading ? "Verifying..." : "Verify & Continue →"}
              </button>

              <button
                type="button"
                className="secondary-link-button"
                onClick={handleResendOtp}
                disabled={loading || resendCooldown > 0}
              >
                {resendCooldown > 0
                  ? `Resend code in ${resendCooldown}s`
                  : "Resend verification code"}
              </button>

              <button
                type="button"
                className="secondary-link-button"
                onClick={() => changeMode("login")}
                disabled={loading}
              >
                Back to Sign In
              </button>
            </form>
          ) : (
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

              <button
                type="submit"
                className="submit-button"
                disabled={loading}
              >
                {loading
                  ? "Please wait..."
                  : isRegister
                    ? "Create Account →"
                    : "Sign In →"}
              </button>
            </form>
          )}

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
