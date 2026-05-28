/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        // Apple-style color system
        apple: {
          blue: '#007AFF',
          'blue-light': '#E8F1FE',
          green: '#34C759',
          'green-light': '#E8F8EC',
          orange: '#FF9500',
          'orange-light': '#FFF3E0',
          red: '#FF3B30',
          'red-light': '#FFE8E6',
          purple: '#AF52DE',
          'purple-light': '#F5E8FC',
          teal: '#5AC8FA',
          yellow: '#FFCC00',
          gray: {
            50: '#F5F5F7',
            100: '#E8E8ED',
            200: '#D2D2D7',
            300: '#AEAEB2',
            400: '#8E8E93',
            500: '#636366',
            600: '#48484A',
            700: '#3A3A3C',
            800: '#2C2C2E',
            900: '#1C1C1E',
          },
        },
        primary: {
          DEFAULT: "#007AFF",
          50: '#E8F1FE',
          100: '#D1E3FD',
          500: '#007AFF',
          600: '#0051D5',
          700: '#003BB3',
          foreground: "#FFFFFF",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "#FF3B30",
          foreground: "#FFFFFF",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        success: '#34C759',
        warning: '#FF9500',
        error: '#FF3B30',
      },
      fontSize: {
        '2xs': ['11px', { lineHeight: '14px', letterSpacing: '-0.01em' }],
        'xs': ['12px', { lineHeight: '16px', letterSpacing: '-0.01em' }],
        'sm': ['13px', { lineHeight: '20px', letterSpacing: '-0.01em' }],
        'base': ['14px', { lineHeight: '22px', letterSpacing: '-0.01em' }],
        'lg': ['16px', { lineHeight: '24px', letterSpacing: '-0.02em' }],
        'xl': ['18px', { lineHeight: '26px', letterSpacing: '-0.02em' }],
        '2xl': ['22px', { lineHeight: '28px', letterSpacing: '-0.02em' }],
        '3xl': ['28px', { lineHeight: '32px', letterSpacing: '-0.03em' }],
      },
      borderRadius: {
        '2xl': '16px',
        '3xl': '20px',
        '4xl': '24px',
        xl: "12px",
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
        xs: "calc(var(--radius) - 6px)",
      },
      boxShadow: {
        xs: "0 1px 2px rgba(0,0,0,0.04)",
        // Apple-style layered shadows
        'apple': '0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.03)',
        'apple-hover': '0 2px 6px rgba(0,0,0,0.06), 0 8px 24px rgba(0,0,0,0.05)',
        'apple-lg': '0 4px 12px rgba(0,0,0,0.08), 0 16px 48px rgba(0,0,0,0.04)',
        'button': '0 1px 2px rgba(0,122,255,0.2), 0 4px 8px rgba(0,122,255,0.15)',
        'button-hover': '0 2px 4px rgba(0,122,255,0.25), 0 8px 16px rgba(0,122,255,0.2)',
        'inner-light': 'inset 0 1px 0 rgba(255,255,255,0.8)',
      },
      backdropBlur: {
        'apple': '20px',
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
        "caret-blink": {
          "0%,70%,100%": { opacity: "1" },
          "20%,50%": { opacity: "0" },
        },
        "breathe": {
          "0%, 100%": { boxShadow: "0 0 0px rgba(0, 122, 255, 0)" },
          "50%": { boxShadow: "0 0 20px rgba(0, 122, 255, 0.15)" },
        },
        "shimmer": {
          "0%": { transform: "translateX(-100%)" },
          "100%": { transform: "translateX(200%)" },
        },
        "pulse-dot": {
          "0%, 100%": { opacity: "1", transform: "scale(1)" },
          "50%": { opacity: "0.6", transform: "scale(0.85)" },
        },
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "fade-in": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        "scale-in": {
          "0%": { opacity: "0", transform: "scale(0.96)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        "caret-blink": "caret-blink 1.25s ease-out infinite",
        "breathe": "breathe 3s ease-in-out infinite",
        "shimmer": "shimmer 2s ease-in-out infinite",
        "pulse-dot": "pulse-dot 2s ease-in-out infinite",
        "fade-up": "fade-up 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards",
        "fade-in": "fade-in 0.3s ease-out forwards",
        "scale-in": "scale-in 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards",
      },
      transitionTimingFunction: {
        'apple': 'cubic-bezier(0.16, 1, 0.3, 1)',
        'apple-spring': 'cubic-bezier(0.34, 1.56, 0.64, 1)',
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}
