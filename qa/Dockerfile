FROM mcr.microsoft.com/playwright:v1.55.0-noble
WORKDIR /workspace
COPY package.json ./
RUN npm install
COPY . .
CMD ["npm", "test"]
