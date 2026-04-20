# Deployment Guide

This project can be deployed on a Linux cloud server with a reverse proxy in front of the Spring Boot backend and the built frontend files.

If you want the simplest hosted setup for this repository, use:

- `frontend/` on Vercel
- `backend/` on Render

## Recommended Server Setup

- Ubuntu 22.04 or later
- Java 17
- Node.js 20
- Nginx
- A domain name is recommended but optional

## 1. Clone The Repository

```bash
git clone https://github.com/Hongufree/tomato_system.git
cd tomato_system
```

## 2. Configure The DeepSeek API Key

Set the environment variable before starting the backend:

```bash
export DEEPSEEK_API_KEY="your-deepseek-api-key"
```

If you want the variable to persist for a service account, place it in `/etc/environment`, a `systemd` unit, or your process manager configuration.

## 3. Build The Backend

```bash
cd backend
chmod +x mvnw
./mvnw clean package -DskipTests
```

After a successful build, the jar file will be created in:

```bash
backend/target/magic_conch_backend-0.0.1-SNAPSHOT.jar
```

## 4. Run The Backend

Quick start:

```bash
cd backend
export DEEPSEEK_API_KEY="your-deepseek-api-key"
java -jar target/magic_conch_backend-0.0.1-SNAPSHOT.jar
```

The backend listens on port `8082` by default.

## 5. Build The Frontend

```bash
cd frontend
npm install
npm run build
```

The built static files will be generated in:

```bash
frontend/dist
```

## 6. Serve The Frontend With Nginx

Example Nginx server block:

```nginx
server {
    listen 80;
    server_name your-domain-or-server-ip;

    root /path/to/tomato_system/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /chat/ {
        proxy_pass http://127.0.0.1:8082;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Reload Nginx after updating the config:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## 7. Run The Backend As A systemd Service

Example unit file: `/etc/systemd/system/tomato-backend.service`

```ini
[Unit]
Description=Tomato Expert System Backend
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/tomato_system/backend
Environment=DEEPSEEK_API_KEY=your-deepseek-api-key
ExecStart=/usr/bin/java -jar /path/to/tomato_system/backend/target/magic_conch_backend-0.0.1-SNAPSHOT.jar
SuccessExitStatus=143
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable tomato-backend
sudo systemctl start tomato-backend
sudo systemctl status tomato-backend
```

## 8. Verify Deployment

Backend API check:

```bash
curl "http://127.0.0.1:8082/chat/generate?prompt=Give%20one%20short%20tomato%20watering%20tip"
```

Frontend check:

- Open `http://your-domain-or-server-ip/`
- Submit a text question from the chat page
- Confirm the page can receive a DeepSeek-backed reply

## Notes

- The previous local image-model workflow is no longer used for inference.
- The current deployed path is text-based consultation through the DeepSeek API.
- If you later need HTTPS, add Certbot or your cloud provider's load balancer SSL configuration in front of Nginx.

## Render Alternative

This repository includes a root-level `render.yaml` for deploying the backend from GitHub to Render.

Recommended Render settings:

- Service type: `Web Service`
- Runtime: `Docker`
- Dockerfile path: `./backend/Dockerfile`
- Docker build context: `./backend`

Required Render environment variables:

- `DEEPSEEK_API_KEY`
- `APP_CORS_ALLOWED_ORIGIN_PATTERNS=http://localhost:5173,https://*.vercel.app`

After Render assigns a backend URL such as:

```bash
https://tomato-backend.onrender.com
```

set the Vercel frontend variable to:

```bash
VITE_API_BASE_URL=https://tomato-backend.onrender.com
```
