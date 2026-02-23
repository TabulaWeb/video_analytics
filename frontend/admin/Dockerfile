# Node.js base image
FROM node:22-alpine

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies (memory limit for 2GB RAM VPS; npm install more tolerant than npm ci)
ENV NODE_OPTIONS=--max-old-space-size=768
RUN npm config set fetch-retries 5 fetch-timeout 120000 && \
    npm install --no-audit --no-fund --legacy-peer-deps

# Copy application code
COPY . .

# Expose port
EXPOSE 3000

# Run development server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
