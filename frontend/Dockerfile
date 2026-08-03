FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json pnpm-lock.yaml* pnpm-workspace.yaml .npmrc ./
RUN corepack enable && pnpm install --frozen-lockfile=false

FROM node:22-alpine AS builder
WORKDIR /app
ARG NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8100/api/v1
ARG NEXT_PUBLIC_AVATAR_MODEL_URL=/models/Female_Adult_01_facial_1024.glb
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_AVATAR_MODEL_URL=$NEXT_PUBLIC_AVATAR_MODEL_URL
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN corepack enable && pnpm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
