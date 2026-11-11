FROM node:24-alpine AS deps
WORKDIR /app
COPY package.json ./
RUN npm install -g npm@12.2.0 && npm install

FROM deps AS dev
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev"]

FROM deps AS build
COPY . .
RUN npm run build
