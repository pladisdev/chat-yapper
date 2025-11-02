/**
 * Color utility functions for Chat Yapper frontend
 */

/**
 * Converts a hex color and opacity value to a hex color with opacity
 * @param {string} color - Hex color code (e.g., '#000000')
 * @param {number} opacity - Opacity value between 0 and 1
 * @returns {string} Hex color with opacity (e.g., '#000000D9')
 */
export function hexColorWithOpacity(color, opacity) {
  const hexOpacity = Math.round(opacity * 255).toString(16).padStart(2, '0');
  return `${color}${hexOpacity}`;
}

export default { hexColorWithOpacity };
