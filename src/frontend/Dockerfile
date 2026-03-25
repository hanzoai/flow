FROM node:20-alpine as frontend_build
ARG BACKEND_URL
WORKDIR /app

COPY ./package.json ./package-lock.json ./tsconfig.json ./vite.config.ts ./index.html ./tailwind.config.js ./postcss.config.js ./prettier.config.js /app/
RUN npm install
COPY ./src /app/src
RUN npm run build

FROM ghcr.io/hanzoai/static:latest
COPY --from=frontend_build /app/build/ /srv