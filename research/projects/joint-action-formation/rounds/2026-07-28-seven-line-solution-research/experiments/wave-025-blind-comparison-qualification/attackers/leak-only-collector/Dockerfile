FROM node:20-slim

WORKDIR /app
COPY --chown=node:node collector.js /app/collector.js

USER node
ENTRYPOINT ["node", "/app/collector.js"]

