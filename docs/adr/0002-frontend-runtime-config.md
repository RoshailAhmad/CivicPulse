# ADR 0002: Frontend runtime configuration through an nginx /api proxy

**Status:** Accepted

## Context

Vite bakes `import.meta.env` values into the JavaScript at build time. If the backend URL
is baked in, the frontend image only works in the environment it was built for, and we
lose build-once-deploy-many: the image tested in CI would not be the image deployed.

## Options considered

1. **Build-time `VITE_API_URL`.** Simple, but one image per environment. Rejected.
2. **`/config.js` generated at container start** from environment variables and loaded
   before the app. Works, but adds a startup script and a global variable, and still
   needs CORS because the browser calls a different origin.
3. **Proxy `/api` through nginx.** The app always calls the relative path `/api`. nginx,
   in the same container that serves the files, forwards `/api/` to the backend.

## Decision

Option 3. `frontend/src/api/client.ts` uses `const BASE = "/api"`.
`frontend/nginx/default.conf.template` contains `proxy_pass ${BACKEND_URL};`, and the
official nginx entrypoint fills in `BACKEND_URL` from the environment when the container
starts. Compose and Kubernetes both set it to `http://backend:8000`.

## Consequences

- One frontend image runs in Compose, in Kubernetes and anywhere else, unchanged.
- Browser and API share an origin, so no CORS configuration exists to get wrong.
- nginx sets `X-Forwarded-For` to the real client address (overwriting, not appending),
  so the Redis rate limiter sees each citizen's IP and a client can't fake one.
- nginx also forwards or creates `X-Request-ID`, so a request can be traced from the
  nginx access log into the backend's JSON logs.
- In Kubernetes the Ingress routes `/api` straight to the backend as well. Both paths
  work because the app only ever uses relative URLs.
