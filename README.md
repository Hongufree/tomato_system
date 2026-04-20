# Tomato Portable Bundle

This repository contains the frontend and backend source code for the tomato expert system, prepared for GitHub upload and cloud deployment.

## Included

- `backend/`: Spring Boot backend
- `frontend/`: Vue + Vite frontend
- `service/`: local Python service scripts kept for reference
- `scripts/`: helper start scripts

## Excluded From Git

The following large or machine-specific folders are ignored and should not be uploaded to GitHub:

- `models/`
- `python_env/`
- `runtime/`
- `frontend/node_modules/`
- `frontend/dist/`
- `backend/target/`
- local log files

## DeepSeek Configuration

The backend now reads the API key from the `DEEPSEEK_API_KEY` environment variable.

Example on Windows PowerShell:

```powershell
$env:DEEPSEEK_API_KEY="your-deepseek-api-key"
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

## GitHub Upload Notes

Before pushing to GitHub:

1. Keep only source code and documentation in the repository.
2. Do not commit model files, local Python environments, runtime bundles, build artifacts, or secrets.
3. If you need cloud deployment, recreate dependencies on the server from `pom.xml` and `package.json`.

