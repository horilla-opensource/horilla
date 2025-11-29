/** @type {import('tailwindcss').Config} */
module.exports = {
    prefix: 'tw-',
    corePlugins: {
        preflight: false,
    },
    content: [
        "./templates/**/*.html",
    ],
    theme: {
        extend: {
            colors: {
                marsel: {
                    50: '#f0fdf4',
                    100: '#dcfce7',
                    200: '#bbf7d0',
                    300: '#86efac',
                    400: '#4ade80',
                    500: '#22c55e',
                    600: '#16a34a',
                    700: '#15803d',
                    800: '#166534',
                    900: '#14532d',
                },
                primary: {
                    50: '#f0fdf4',
                    100: '#dcfce7',
                    200: '#bbf7d0',
                    300: '#86efac',
                    400: '#4ade80',
                    500: '#22c55e',
                    600: '#16a34a',
                    700: '#15803d',
                    800: '#166534',
                    900: '#14532d',
                    DEFAULT: '#15803d',
                },
                secondary: {
                    DEFAULT: '#1e293b', // Slate 800
                    light: '#334155',
                    dark: '#0f172a',
                }
            },
            fontFamily: {
                sans: ['Inter', 'sans-serif'],
                heading: ['Poppins', 'sans-serif'],
            },
            boxShadow: {
                'glass': '0 8px 32px 0 rgba(31, 38, 135, 0.37)',
            },
            backdropBlur: {
                'glass': '4px',
            }
        },
    },
    plugins: [
        require('@tailwindcss/forms'),
    ],
}
