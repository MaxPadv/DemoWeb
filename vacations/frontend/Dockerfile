# Микрофронтенд «Отпуска» — собирается отдельно (контекст = корень репо).
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json .npmrc ./
COPY services/shell/package.json services/shell/
COPY services/vacations/frontend/package.json services/vacations/frontend/
COPY services/structure/frontend/package.json services/structure/frontend/
RUN npm install --no-audit --no-fund --registry=https://nexus.sogaz.ru/repository/npm-proxy-registry.npmjs.org/
COPY . .
RUN node node_modules/webpack/bin/webpack.js --mode production --config services/vacations/frontend/webpack.config.js
FROM nginx:alpine
COPY --from=build /app/services/vacations/frontend/dist /usr/share/nginx/html
COPY --from=build /app/services/vacations/frontend/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
