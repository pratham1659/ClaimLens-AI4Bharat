# frontend/Dockerfile
# Multi-stage Dockerfile for ClaimLens Frontend
# Supports both LOCAL (development) and PROD (production) builds
#
# Build targets:
#   local - Development with hot-reload (React dev server)
#   prod  - Optimized production build (nginx)

# ============================================
# BASE STAGE - Common setup
# ============================================
FROM node:20-alpine AS base

WORKDIR /app

# Copy package files
COPY package*.json ./

# ============================================
# LOCAL STAGE - Development build
# ============================================
FROM base AS local

# Install all dependencies (including devDependencies)
RUN npm install

# Copy source code (will be overridden by volume mount in dev)
COPY . .

# Environment variables for development
ENV REACT_APP_API_URL=http://localhost:8000/api/v1
ENV CHOKIDAR_USEPOLLING=true
ENV WATCHPACK_POLLING=true
ENV WDS_SOCKET_PORT=0

EXPOSE 3000

# Start development server with hot-reload
CMD ["npm", "start"]

# ============================================
# BUILD STAGE - Build production assets
# ============================================
FROM base AS builder

# Install dependencies
RUN npm ci --only=production=false

# Copy source code
COPY . .

# Build the application
RUN npm run build

# ============================================
# PROD STAGE - Production build with nginx
# ============================================
FROM nginx:alpine AS prod

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets from builder stage
# Note: Create React App uses 'build' folder, Vite uses 'dist'
# We copy both to handle either case
COPY --from=builder /app/build /usr/share/nginx/html
# Uncomment below if using Vite:
# COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
