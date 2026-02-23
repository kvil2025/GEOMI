import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
    plugins: [react()],
    server: {
        port: 5173,
        proxy: {
            '/wfs': 'http://localhost:8000',
            '/dem': 'http://localhost:8000',
            '/intersection': 'http://localhost:8000',
            '/profile': 'http://localhost:8000',
            '/health': 'http://localhost:8000',
        },
    },
});
