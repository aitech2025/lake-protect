# Chromium-only browser test image (smaller than the all-browser Playwright image).
FROM node:24-bookworm-slim
WORKDIR /e2e
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund \
 && npx playwright install --with-deps chromium \
 && rm -rf /var/lib/apt/lists/* /root/.npm
COPY playwright.config.ts ./
COPY tests ./tests
CMD ["npx", "playwright", "test"]
