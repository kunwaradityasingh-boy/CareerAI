const HEALTH_URL = "http://127.0.0.1:8000/health";
const INTERVAL = 5000;

let wasHealthy = false;

async function checkHealth() {
  try {
    const response = await fetch(HEALTH_URL);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();

    if (data.status !== "healthy" || data.database !== "connected") {
      throw new Error("Backend or database is unhealthy");
    }

    if (!wasHealthy) {
      console.log("HEALTH: Backend healthy | PostgreSQL connected");
      wasHealthy = true;
    }
  } catch (error) {
    console.log(`HEALTH WARNING: ${error.message}`);
    wasHealthy = false;
  }
}

console.log("HEALTH: Waiting for Backend...");

checkHealth();
setInterval(checkHealth, INTERVAL);
