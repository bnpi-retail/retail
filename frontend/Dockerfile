#baseline
FROM node:21-alpine AS base
RUN mkdir -p /home/node/app
RUN chown -R node:node /home/node && chmod -R 770 /home/node
WORKDIR /home/node/app

# client build
FROM base AS builder-client
WORKDIR /home/node/app
COPY --chown=node:node . ./
USER node
RUN npm config set registry http://registry.npmjs.org/
RUN npm install --loglevel warn
EXPOSE 3000
CMD ["npm", "start"]