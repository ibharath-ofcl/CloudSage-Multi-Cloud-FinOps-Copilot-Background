# syntax=docker/dockerfile:1.4
# ==============================================================================
# CloudSage Frontend Multi-Stage Production Dockerfile
# Stage 1: Build production React + Vite bundle
# Stage 2: Serve static assets via hardened Nginx server
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Build Stage
# ------------------------------------------------------------------------------
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependency manifests
COPY package.json package-lock.json* ./

# Install dependencies (use npm ci if lockfile exists, fallback to npm install)
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

# Copy frontend source code
COPY . .

# Build production bundle
RUN npm run build

# ------------------------------------------------------------------------------
# Stage 2: Production Nginx Runtime
# ------------------------------------------------------------------------------
FROM nginx:1.27-alpine AS production

LABEL maintainer="CloudSage FinOps Team <devops@cloudsage.internal>" \
      description="CloudSage Multi-Cloud FinOps Copilot Frontend Static Web Server" \
      version="0.15.0"

# Remove default nginx static assets
RUN rm -rf /usr/share/nginx/html/*

# Copy compiled static assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Configure directory permissions
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chmod -R 755 /usr/share/nginx/html && \
    chown -R nginx:nginx /var/cache/nginx /var/log/nginx /etc/nginx/conf.d

EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:80/healthz || exit 1

CMD ["nginx", "-g", "daemon off;"]

