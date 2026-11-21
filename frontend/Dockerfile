FROM node:22-bookworm-slim AS dev

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]

FROM dev AS build

# "same-origin" makes the browser call /api on this host. See apiBase() in src/api.ts.
ENV VITE_API_BASE_URL=same-origin
RUN npm run build

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
