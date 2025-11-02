/**
 * Converts a hex color and opacity value to a hex color with alpha channel
 * @param {string} hexColor - Hex color code (e.g., '#ffffff')
 * @param {number} opacity - Opacity value between 0 and 1
 * @returns {string} Hex color with alpha channel (e.g., '#ffffffd9')
 */
export function hexColorWithOpacity(hexColor, opacity) {
  // Validate hex color format
  if (!hexColor || typeof hexColor !== 'string' || !hexColor.startsWith('#') || hexColor.length !== 7) {
    console.warn(`Invalid hex color format: ${hexColor}, expected format: #RRGGBB`)
    return hexColor // Return original value if invalid
  }
  
  // Clamp opacity between 0 and 1
  const clampedOpacity = Math.max(0, Math.min(1, opacity))
  
  const alpha = Math.round(clampedOpacity * 255)
    .toString(16)
    .padStart(2, '0')
  return `${hexColor}${alpha}`
}

/**
 * Converts a hex color to rgba format
 * @param {string} hex - Hex color code (e.g., '#ffffff')
 * @param {number} opacity - Opacity value between 0 and 1
 * @returns {string} RGBA color string (e.g., 'rgba(255,255,255,0.9)')
 */
export function hexToRgba(hex, opacity) {
  // Validate hex color format
  if (!hex || typeof hex !== 'string' || !hex.startsWith('#') || hex.length !== 7) {
    console.warn(`Invalid hex color format: ${hex}, expected format: #RRGGBB`)
    return `rgba(0,0,0,${opacity})` // Return black with opacity as fallback
  }
  
  // Clamp opacity between 0 and 1
  const clampedOpacity = Math.max(0, Math.min(1, opacity))
  
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `rgba(${r},${g},${b},${clampedOpacity})`
}
