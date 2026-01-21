# Use Node image for Astro
FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Build the Astro project
RUN npm run build

# Expose port
EXPOSE 4321

# Run the standalone Node server
CMD ["node", "./dist/server/entry.mjs"]
