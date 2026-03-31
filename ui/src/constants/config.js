/**
 * AXIOM UI Configuration
 * 
 * Sources API base URL from environment or defaults to localhost.
 */

export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export const APP_CONFIG = {
  NAME: "AXIOM V4",
  VERSION: "4.0.0",
  REFRESH_INTERVAL_MS: 30000,
  WS_URL: API_BASE.replace("http", "ws") + "/ws",
};
