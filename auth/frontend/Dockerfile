# Микрофронтенд «Авторизация» — собирается отдельно (контекст = корень репо).
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json .npmrc ./
COPY services/shell/package.json services/shell/
COPY services/vacations/frontend/package.json services/vacations/frontend/
COPY services/structure/frontend/package.json services/structure/frontend/
COPY services/auth/frontend/package.json services/auth/frontend/
RUN npm install --no-audit --no-fund --registry=https://nexus.sogaz.ru/repository/npm-proxy-registry.npmjs.org/
COPY . .
RUN node node_modules/webpack/bin/webpack.js --mode production --config services/auth/frontend/webpack.config.js
FROM nginx:alpine
COPY --from=build /app/services/auth/frontend/dist /usr/share/nginx/html
COPY --from=build /app/services/auth/frontend/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
