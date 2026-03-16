FROM node:20-slim

WORKDIR /app

COPY package*.json ./
RUN npm ci --include=dev

COPY . .

EXPOSE 5173

CMD ["npx", "vite", "--host"]
