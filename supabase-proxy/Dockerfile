FROM node:20-alpine
WORKDIR /app
# Build context is repo root when dockerfilePath is supabase-proxy/Dockerfile
COPY supabase-proxy/package.json supabase-proxy/server.js ./
EXPOSE 3000
ENV PORT=3000
CMD ["node", "server.js"]
