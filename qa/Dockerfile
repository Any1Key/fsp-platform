FROM mcr.microsoft.com/playwright:v1.55.1-noble
WORKDIR /workspace
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts
COPY . .
CMD ["npm", "test"]
