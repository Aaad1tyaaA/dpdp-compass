FROM node:20-alpine
WORKDIR /app
# Install deps first (better layer caching)
COPY package.json package-lock.json* ./
RUN npm install
# App source (compose also bind-mounts ./frontend:/app for live dev updates)
COPY . .
EXPOSE 3000
ENV VITE_API_URL=http://localhost:8000
CMD ["npm","run","dev","--","--host","0.0.0.0","--port","3000"]
