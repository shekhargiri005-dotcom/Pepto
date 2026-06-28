# ============================================================
# Pepto Frontend — Multi-Stage Docker Build
# Stage 1: builder (Node + Vite)  |  Stage 2: nginx:alpine
# ============================================================

# ── Stage 1: builder ─────────────────────────────────────────
FROM node:20-alpine AS builder

LABEL maintainer="Pepto Engineering <engineering@pepto.app>"
LABEL description="Pepto Pet Services Marketplace — Frontend Builder"

# Add build tools required by some native Node packages
RUN apk add --no-cache libc6-compat python3 make g++

WORKDIR /app

# Copy package manifests first to maximise layer caching
COPY package.json package-lock.json* ./

# Install all dependencies (including devDeps needed for the build)
RUN npm ci --frozen-lockfile

# Copy the rest of the source
COPY . .

# Accept build-time environment variables
ARG VITE_API_BASE_URL=http://localhost:5000
ARG VITE_STRIPE_PUBLISHABLE_KEY
ARG VITE_SOCKET_URL=http://localhost:5000
ARG VITE_MAPBOX_TOKEN
ARG VITE_CLOUDINARY_CLOUD_NAME

ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_STRIPE_PUBLISHABLE_KEY=$VITE_STRIPE_PUBLISHABLE_KEY \
    VITE_SOCKET_URL=$VITE_SOCKET_URL \
    VITE_MAPBOX_TOKEN=$VITE_MAPBOX_TOKEN \
    VITE_CLOUDINARY_CLOUD_NAME=$VITE_CLOUDINARY_CLOUD_NAME

# Build the React application for production
RUN npm run build


# ── Stage 2: nginx production image ──────────────────────────
FROM nginx:1.27-alpine AS production

LABEL maintainer="Pepto Engineering <engineering@pepto.app>"
LABEL description="Pepto Pet Services Marketplace — Frontend Production"
LABEL version="1.0.0"

# Remove default nginx content
RUN rm -rf /usr/share/nginx/html/*

# Copy the compiled React app from the builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy our custom nginx configuration (handles React Router try_files)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# nginx runs as the built-in `nginx` user (uid 101) — already non-root
# Adjust permissions so the nginx worker can read the files
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chmod -R 755 /usr/share/nginx/html && \
    # Allow nginx to write its cache / temp directories
    chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    touch /var/run/nginx.pid && \
    chown nginx:nginx /var/run/nginx.pid

EXPOSE 80

# Health-check on the nginx level
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD wget -qO- http://localhost/health || exit 1

USER nginx

CMD ["nginx", "-g", "daemon off;"]
