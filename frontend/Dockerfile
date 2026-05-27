FROM node:20-slim

WORKDIR /app

# Copy package.json and install dependencies
COPY package.json .
RUN npm install

# Copy source code
COPY . .

# Expose Vite dev server port
EXPOSE 3000

# Start Vite server
CMD ["npm", "run", "dev"]
