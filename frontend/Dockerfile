# ---- Stage 1: build — Node compiles the React app to static files ----
FROM node:22.12.0-alpine3.21 AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build

# ---- Stage 2: serve — nginx only. No Node, no node_modules, no source. ----
FROM nginx:1.27.3-alpine AS runtime
COPY nginx/nginx.conf /etc/nginx/nginx.conf
# A template: at container START, nginx's entrypoint replaces ${BACKEND_URL}
# from the environment. The same image works in Compose, Kubernetes or anywhere.
COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
RUN rm -f /etc/nginx/conf.d/default.conf \
 && chown -R nginx:nginx /etc/nginx/conf.d /var/cache/nginx /usr/share/nginx/html
ENV BACKEND_URL=http://backend:8000
USER nginx
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD ["wget", "-q", "-O", "/dev/null", "http://127.0.0.1:8080/healthz"]
