FROM node:20-slim

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ .

# .env.production sets VITE_API_BASE_URL="" so the built bundle calls the API
# same-origin (nginx fronts both SPA and API) — no CORS needed in prod.
RUN npm run build
