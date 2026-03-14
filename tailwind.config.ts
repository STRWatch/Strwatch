import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'green-deep': '#1a4d2e',
        'green-brand': '#2d7a4f',
        'green-bright': '#4db87a',
        'green-pale': '#e8f5ee',
        'green-light': '#c8ecd8',
        'ink': '#0f1a0a',
        'border-brand': '#d8e8cf',
        'off-white': '#f7f9f5',
      },
    },
  },
  plugins: [],
}
export default config
