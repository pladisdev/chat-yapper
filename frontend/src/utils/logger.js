/**
 * Logging utility for Chat Yapper frontend
 * 
 * Detects if running in production (served from backend) vs development (Vite dev server)
 * and adjusts console logging accordingly:
 * - Production: Only show console.error
 * - Development: Show all console logs
 */

/**
 * Detect if we're running in production mode.
 * This happens when:
 * 1. The app is served from the backend (not Vite dev server)
 * 2. We're running as a built executable
 * 
 * We detect this by checking if we're on localhost with Vite dev ports
 */
function isProduction() {
  // If we're on localhost with Vite dev server ports, we're in development
  if (location.hostname === 'localhost' && 
      (location.port === '5173' || location.port === '5174')) {
    return false;
  }
  
  // Otherwise, we're likely in production (served from backend or .exe)
  return true;
}

/**
 * Conditional logging functions
 * In production: only errors are shown
 * In development: all logs are shown
 */
export const logger = {
  /**
   * Log informational messages (development only)
   */
  info: (...args) => {
    if (!isProduction()) {
      console.log(...args);
    }
  },

  /**
   * Log debug messages (development only) 
   */
  debug: (...args) => {
    if (!isProduction()) {
      console.log(...args);
    }
  },

  /**
   * Log warning messages (development only)
   */
  warn: (...args) => {
    if (!isProduction()) {
      console.warn(...args);
    }
  },

  /**
   * Log error messages (always shown)
   */
  error: (...args) => {
    console.error(...args);
  },

  /**
   * Get current environment info
   */
  getEnvironment: () => ({
    isProduction: isProduction(),
    hostname: location.hostname,
    port: location.port,
    mode: isProduction() ? 'production' : 'development'
  })
};

export default logger;