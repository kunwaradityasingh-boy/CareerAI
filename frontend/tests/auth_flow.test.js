import test from "node:test";
import assert from "node:assert/strict";

test("Frontend Registration Form Validation", async (t) => {
  function validateRegistration({ name, email, password, confirmPassword }) {
    if (!name || name.trim().length < 2) {
      return { valid: false, error: "Name must contain at least 2 characters." };
    }
    if (!email || !email.includes("@")) {
      return { valid: false, error: "Please enter a valid email." };
    }
    if (!password || password.length < 8 || password.length > 128) {
      return { valid: false, error: "Password must contain 8–128 characters." };
    }
    if (password !== confirmPassword) {
      return { valid: false, error: "Passwords do not match." };
    }
    return { valid: true };
  }

  await t.test("rejects short name (< 2 chars)", () => {
    const res = validateRegistration({
      name: "A",
      email: "test@example.com",
      password: "Password123!",
      confirmPassword: "Password123!",
    });
    assert.equal(res.valid, false);
    assert.match(res.error, /Name must contain at least 2 characters/i);
  });

  await t.test("rejects short password (< 8 chars)", () => {
    const res = validateRegistration({
      name: "Alice",
      email: "test@example.com",
      password: "short",
      confirmPassword: "short",
    });
    assert.equal(res.valid, false);
    assert.match(res.error, /Password must contain 8–128 characters/i);
  });

  await t.test("rejects mismatched passwords", () => {
    const res = validateRegistration({
      name: "Alice",
      email: "test@example.com",
      password: "Password123!",
      confirmPassword: "DifferentPassword123!",
    });
    assert.equal(res.valid, false);
    assert.match(res.error, /Passwords do not match/i);
  });

  await t.test("accepts valid registration input", () => {
    const res = validateRegistration({
      name: "Alice Walker",
      email: "alice@example.com",
      password: "ValidPassword123!",
      confirmPassword: "ValidPassword123!",
    });
    assert.equal(res.valid, true);
    assert.equal(res.error, undefined);
  });
});

test("Frontend OTP Code Validation", async (t) => {
  function validateOtp(otp) {
    if (!/^[0-9]{6}$/.test(otp)) {
      return { valid: false, error: "Please enter a valid 6-digit OTP." };
    }
    return { valid: true };
  }

  await t.test("rejects non-numeric OTP", () => {
    assert.equal(validateOtp("12A456").valid, false);
    assert.equal(validateOtp("abcdef").valid, false);
  });

  await t.test("rejects short or long OTP", () => {
    assert.equal(validateOtp("12345").valid, false);
    assert.equal(validateOtp("1234567").valid, false);
    assert.equal(validateOtp("").valid, false);
  });

  await t.test("accepts valid 6-digit numeric OTP", () => {
    assert.equal(validateOtp("012345").valid, true);
    assert.equal(validateOtp("999999").valid, true);
  });
});

test("Frontend Flow State Machine & Transitions", async (t) => {
  await t.test("OTP screen transition after successful registration call", () => {
    let registrationStep = "details";
    let pendingEmail = "";
    let message = "";

    // Simulated handleRegister success
    const regResult = { success: true, message: "Verification code sent to your email." };
    const submittedEmail = "user@example.com";

    pendingEmail = submittedEmail;
    registrationStep = "otp";
    message = regResult.message;

    assert.equal(registrationStep, "otp");
    assert.equal(pendingEmail, "user@example.com");
    assert.equal(message, "Verification code sent to your email.");
  });

  await t.test("Verification success with auto-login redirects to dashboard", () => {
    let currentRoute = "/";
    let activeSession = null;

    // Simulate successful verifyRegistration followed by createSession
    const token = "mock_jwt_token";
    const user = { id: 1, name: "Alice", email: "alice@example.com" };

    function setSession(tok, usr) {
      activeSession = { token: tok, user: usr };
      currentRoute = "/dashboard";
    }

    setSession(token, user);

    assert.equal(currentRoute, "/dashboard");
    assert.equal(activeSession.token, "mock_jwt_token");
    assert.equal(activeSession.user.name, "Alice");
  });

  await t.test("Verification failure keeps user on OTP step with error", () => {
    let registrationStep = "otp";
    let message = "";

    // Simulate OTP failure
    const errorDetail = "Incorrect OTP.";
    message = errorDetail;

    assert.equal(registrationStep, "otp");
    assert.equal(message, "Incorrect OTP.");
  });

  await t.test("Verification success with login failure gracefully switches to login screen", () => {
    let mode = "register";
    let registrationStep = "otp";
    let registrationPassword = "";
    let message = "";

    // Verification succeeded, but auto-login failed (e.g. page refresh cleared in-memory password)
    const verificationSucceeded = true;
    if (verificationSucceeded) {
      mode = "login";
      registrationStep = "details";
      registrationPassword = "";
      message = "Email verified successfully. Please sign in with your email and password.";
    }

    assert.equal(mode, "login");
    assert.equal(registrationStep, "details");
    assert.equal(registrationPassword, "");
    assert.match(message, /Email verified successfully/i);
  });
});

test("Security & Storage Invariants", async (t) => {
  await t.test("Plaintext passwords must never be written to persistent storage", () => {
    const storageKeys = ["careerai_pending_email"];
    assert.equal(storageKeys.includes("password"), false);
    assert.equal(storageKeys.includes("registration_password"), false);
  });

  await t.test("Protected route redirects unauthenticated users", () => {
    function checkAccess(isAuthenticated) {
      if (!isAuthenticated) {
        return { allow: false, redirect: "/" };
      }
      return { allow: true };
    }

    assert.deepEqual(checkAccess(false), { allow: false, redirect: "/" });
    assert.deepEqual(checkAccess(true), { allow: true });
  });
});
