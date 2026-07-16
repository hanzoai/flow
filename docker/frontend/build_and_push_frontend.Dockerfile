# syntax=docker/dockerfile:1
# Keep this syntax directive! It's used to enable Docker BuildKit

################################
# BUILDER-BASE
################################

# 1. force platform to the current architecture to increase build speed time on multi-platform builds
FROM --platform=$BUILDPLATFORM node:lts-bookworm-slim AS builder-base
COPY src/frontend /frontend

RUN cd /frontend && npm install && npm run build

################################
# RUNTIME
################################
FROM ghcr.io/hanzoai/static:latest AS runtime

LABEL org.opencontainers.image.title=flow-frontend
LABEL org.opencontainers.image.authors=['Hanzo Flow']
LABEL org.opencontainers.image.licenses=MIT
LABEL org.opencontainers.image.url=https://github.com/hanzoai/flow
LABEL org.opencontainers.image.source=https://github.com/hanzoai/flow

COPY --from=builder-base /frontend/build /srv
