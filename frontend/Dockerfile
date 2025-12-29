# Build stage
FROM node:18-alpine as builder

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install all dependencies (including dev dependencies for build)
RUN npm ci

# Copy source code
COPY . .

# Accept build arguments for environment variables
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_ANON_KEY
ARG VITE_AGENT_ENDPOINT
ARG VITE_ENABLE_STREAMING
ARG VITE_LANGFUSE_HOST_WITH_PROJECT

# Set environment variables from build args
ENV VITE_SUPABASE_URL=${VITE_SUPABASE_URL}
ENV VITE_SUPABASE_ANON_KEY=${VITE_SUPABASE_ANON_KEY}
ENV VITE_AGENT_ENDPOINT=${VITE_AGENT_ENDPOINT}
ENV VITE_ENABLE_STREAMING=${VITE_ENABLE_STREAMING}
ENV VITE_LANGFUSE_HOST_WITH_PROJECT=${VITE_LANGFUSE_HOST_WITH_PROJECT}

# Build the application
RUN npm run build

# Production stage
# Note: nginx is used here to serve static files within the container
# Caddy (or another reverse proxy) would sit in front of this container
FROM nginx:alpine

# Install dumb-init for proper signal handling
RUN apk add --no-cache dumb-init

# Create non-root user
RUN addgroup -g 1001 -S appuser && \
    adduser -S appuser -u 1001

# Copy nginx configuration
COPY --from=builder /app/nginx.conf /etc/nginx/nginx.conf

# Copy built application
COPY --from=builder /app/dist /usr/share/nginx/html

# Create nginx cache and run directories
RUN mkdir -p /var/cache/nginx /var/run/nginx && \
    chown -R appuser:appuser /var/cache/nginx /var/run/nginx /usr/share/nginx/html

# Expose port
EXPOSE 8080

# Switch to non-root user
USER appuser

# Use dumb-init to handle signals properly
ENTRYPOINT ["dumb-init", "--"]

# Start nginx
CMD ["nginx", "-g", "daemon off;"]