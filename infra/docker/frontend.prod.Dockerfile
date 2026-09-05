# Production frontend image: build stage + nginx static serve (non-root).
FROM node:24-alpine AS builder
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci || npm install
COPY frontend/ ./
RUN npm run build

FROM nginx:1.27-alpine AS runtime
RUN adduser -D -u 10002 static && \
    mkdir -p /var/cache/nginx /var/run /etc/nginx/conf.d && \
    chown -R static:static /usr/share/nginx/html /var/cache/nginx /var/run
COPY --from=builder /app/dist /usr/share/nginx/html
COPY infra/nginx/frontend.conf /etc/nginx/conf.d/default.conf
USER static
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost:8080/healthz || exit 1
CMD ["nginx", "-g", "daemon off;"]
