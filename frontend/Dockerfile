FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
COPY vite.config.* ./
RUN npm install

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
