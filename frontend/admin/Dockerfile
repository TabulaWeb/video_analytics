# Node.js base image
FROM node:22-alpine

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies (npm ci + memory limit for low-RAM VPS)
ENV NODE_OPTIONS=--max-old-space-size=1024
RUN npm ci

# Copy application code
COPY . .

# Expose port
EXPOSE 3000

# Run development server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
