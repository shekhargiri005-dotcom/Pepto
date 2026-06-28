/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#6C63FF',
          50: '#F0EFFF',
          100: '#E1DEFF',
          200: '#C3BDFF',
          300: '#A59CFF',
          400: '#877BFF',
          500: '#6C63FF',
          600: '#4D42FF',
          700: '#2E21FF',
          800: '#1A0FE8',
          900: '#1209B5',
        },
        secondary: {
          DEFAULT: '#FF6584',
          50: '#FFF0F3',
          100: '#FFE1E7',
          200: '#FFC3CF',
          300: '#FFA5B7',
          400: '#FF879F',
          500: '#FF6584',
          600: '#FF3766',
          700: '#FF0948',
          800: '#DA0039',
          900: '#AC002D',
        },
        accent: {
          DEFAULT: '#43D9AD',
          50: '#EDFDF8',
          100: '#DBFBF1',
          200: '#B7F7E3',
          300: '#93F3D5',
          400: '#6FEFC7',
          500: '#43D9AD',
          600: '#28BF94',
          700: '#1E9573',
          800: '#146B52',
          900: '#0A4131',
        },
        dark: {
          bg: '#0F0F1A',
          card: '#1A1A2E',
          border: '#2D2D4E',
          hover: '#252542',
          elevated: '#16213E',
        },
        text: {
          primary: '#E2E8F0',
          secondary: '#94A3B8',
          muted: '#64748B',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['Inter', 'system-ui', 'sans-serif'],
      },
      animation: {
        'float': 'float 6s ease-in-out infinite',
        'float-delayed': 'float 6s ease-in-out 2s infinite',
        'float-slow': 'float 8s ease-in-out 1s infinite',
        'glow': 'glow 2s ease-in-out infinite',
        'slide-up': 'slideUp 0.3s ease-out',
        'slide-down': 'slideDown 0.3s ease-out',
        'fade-in': 'fadeIn 0.5s ease-out',
        'pulse-glow': 'pulseGlow 2s ease-in-out infinite',
        'skeleton': 'skeleton 1.5s ease-in-out infinite',
        'spin-slow': 'spin 3s linear infinite',
        'bounce-slow': 'bounce 3s infinite',
        'gradient': 'gradientShift 6s ease infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px) rotate(0deg)' },
          '33%': { transform: 'translateY(-15px) rotate(5deg)' },
          '66%': { transform: 'translateY(-8px) rotate(-3deg)' },
        },
        glow: {
          '0%, 100%': { boxShadow: '0 0 20px rgba(108, 99, 255, 0.3)' },
          '50%': { boxShadow: '0 0 40px rgba(108, 99, 255, 0.7)' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideDown: {
          '0%': { opacity: '0', transform: 'translateY(-20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        pulseGlow: {
          '0%, 100%': { opacity: '1', transform: 'scale(1)' },
          '50%': { opacity: '0.7', transform: 'scale(1.05)' },
        },
        skeleton: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        gradientShift: {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
        },
      },
      backgroundSize: {
        '300%': '300% 300%',
      },
      backdropBlur: {
        xs: '2px',
      },
      boxShadow: {
        'glass': '0 8px 32px rgba(0, 0, 0, 0.37)',
        'glow-primary': '0 0 30px rgba(108, 99, 255, 0.4)',
        'glow-secondary': '0 0 30px rgba(255, 101, 132, 0.4)',
        'glow-accent': '0 0 30px rgba(67, 217, 173, 0.4)',
        'card': '0 4px 24px rgba(0, 0, 0, 0.4)',
        'card-hover': '0 8px 40px rgba(108, 99, 255, 0.25)',
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.5rem',
        '4xl': '2rem',
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
        '128': '32rem',
      },
    },
  },
  plugins: [],
};
