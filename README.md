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

## Security Notes

- Do not commit real API keys or server-specific secrets.
- Keep `DEEPSEEK_API_KEY` in environment variables or your deployment platform secret manager.
- Rebuild dependencies on the server from `pom.xml` and `package.json` instead of uploading local runtime bundles.
