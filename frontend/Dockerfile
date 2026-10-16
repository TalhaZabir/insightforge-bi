FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
# NEXT_PUBLIC_* is baked in at build time: pass --build-arg to override.
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

FROM node:20-alpine
WORKDIR /app
COPY --from=deps /app/.next/standalone ./
COPY --from=deps /app/.next/static ./.next/static
EXPOSE 3000
CMD ["node", "server.js"]
