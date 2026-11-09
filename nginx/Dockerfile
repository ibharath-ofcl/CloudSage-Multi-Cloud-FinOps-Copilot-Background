FROM nginx:1.27-alpine

LABEL maintainer="CloudSage FinOps Team <devops@cloudsage.internal>" \
      description="CloudSage Multi-Cloud FinOps Copilot Ingress Reverse Proxy" \
      version="0.15.0"

COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:80/healthz || exit 1

CMD ["nginx", "-g", "daemon off;"]

