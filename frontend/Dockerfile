# Gunakan Node.js sebagai base image
FROM node:20
# Set working directory
WORKDIR /app

# Copy file package.json dan package-lock.json
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy semua file ke dalam image
COPY . .

# Expose port default Vite (5173)
EXPOSE 5173

# Jalankan aplikasi dalam mode development
CMD ["npm", "run", "dev", "--", "--host"]