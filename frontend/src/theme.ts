/** Nexa design tokens — single source of truth for all colors, spacing, and typography. */

export const tokens = {
  color: {
    bg: {
      page: "#0d0d0d",
      card: "#1a1a1a",
      elevated: "#1f1f1f",
      input: "#1a1a1a",
      code: "#0d0d0d",
      hover: "#242424",
    },
    border: {
      default: "#333",
      light: "#222",
      dashed: "#444",
    },
    text: {
      primary: "#ddd",
      secondary: "#ccc",
      tertiary: "#888",
      muted: "#666",
      inverse: "#fff",
    },
    accent: {
      blue: "#2563EB",
      blueLight: "#60a5fa",
      green: "#22c55e",
      amber: "#d29922",
      purple: "#a78bfa",
    },
  },
  spacing: {
    xs: 4,
    sm: 8,
    md: 12,
    lg: 16,
    xl: 20,
    xxl: 24,
    xxxl: 32,
  },
  radius: {
    sm: 4,
    md: 6,
    lg: 8,
    xl: 10,
  },
  fontSize: {
    caption: 12,
    xs: 13,
    sm: 14,
    base: 16,
    md: 18,
    lg: 20,
    xl: 30,
  },
} as const;
