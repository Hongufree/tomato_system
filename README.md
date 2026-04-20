# Tomato Expert System

This repository contains the source code for a tomato-growing expert system with a Vue frontend and a Spring Boot backend. The current version uses the DeepSeek cloud API for inference and no longer depends on a local model runtime.

## Stack

- Frontend: Vue 3 + Vite + Element Plus
- Backend: Spring Boot 3 + Java 17
- AI provider: DeepSeek API

## Repository Layout

- `frontend/`: web client
- `backend/`: Spring Boot API
- `service/`: legacy local Python service kept only for reference
- `scripts/`: helper scripts from the original portable bundle

## What Is Not Committed

This repository ignores machine-specific and large local files, including:

- `models/`
- `python_env/`
- `runtime/`
- `frontend/node_modules/`
- `frontend/dist/`
- `backend/target/`
- local logs
- local `.env` files

## Environment Variables

The backend reads the DeepSeek API key from an environment variable:

```powershell
$env:DEEPSEEK_API_KEY="your-deepseek-api-key"
```

Linux/macOS:

```bash
export DEEPSEEK_API_KEY="your-deepseek-api-key"
```

## Local Development

Backend:

```powershell
cd backend
./mvnw.cmd spring-boot:run
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

Default local ports:

- Frontend: `5173`
- Backend: `8082`

## Production Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for a Linux cloud deployment guide with:

- Java and Node installation
- backend build and startup
- frontend build output hosting
- Nginx reverse proxy example
- environment variable setup

This repository also includes [render.yaml](render.yaml) for easier Render backend deployment from GitHub.

## Vercel Frontend Deployment

This repository is best deployed with:

- `frontend/` on Vercel
- `backend/` on a Java-friendly platform such as Render or a cloud server

In Vercel:

1. Import the GitHub repository
2. Set the Root Directory to `frontend`
3. Set the build command to `npm run build`
4. Set the output directory to `dist`
5. Add `VITE_API_BASE_URL` as an environment variable pointing to your deployed backend URL

For the backend, set `APP_CORS_ALLOWED_ORIGIN_PATTERNS` to allow your Vercel domains, for example:

```bash
APP_CORS_ALLOWED_ORIGIN_PATTERNS=http://localhost:5173,https://*.vercel.app
```

## Render Backend Deployment

This repository includes a root-level `render.yaml` so Render can create the backend service with:

- `runtime`: `docker`
- `dockerfilePath`: `./backend/Dockerfile`
- `dockerContext`: `./backend`

After the backend is live on Render, copy the public backend URL into the Vercel environment variable:

```bash
VITE_API_BASE_URL=https://your-render-service.onrender.com
```

## Security Notes

- Do not commit real API keys or server-specific secrets.
- Keep `DEEPSEEK_API_KEY` in environment variables or your deployment platform secret manager.
- Rebuild dependencies on the server from `pom.xml` and `package.json` instead of uploading local runtime bundles.
