# Build with Node, serve with nginx. node_modules lives only inside the build stage, never in
# the OneDrive project folder (CONTEXT.md section 11).
FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY tsconfig.json vite.config.ts index.html ./
COPY public ./public
COPY src ./src
# The world map's street style (D-068): empty for OpenFreeMap, "offline" for local files only, or a style URL.
ARG LP_BASEMAP_STYLE=""
ENV VITE_LP_BASEMAP_STYLE=$LP_BASEMAP_STYLE
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
