# Use official Node.js image as base
FROM node:18-alpine

# Set working directory
WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./

# Install dependencies
RUN npm ci

# Copy all source files
COPY . .

# Expose Vite's default dev port
EXPOSE 5173

# Start the dev server
CMD ["npm", "run", "dev", "--", "--host"]
