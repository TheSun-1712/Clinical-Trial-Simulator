FROM python:3.11-slim

# Install system dependencies and Node.js
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the repository
COPY . /app/

# Install python project and dependencies
RUN pip install --no-cache-dir -e .[train]

# Build the frontend
WORKDIR /app/frontend
RUN npm install && npm run build

# Final workspace setup
WORKDIR /app

# Start the environment API and UI
# We run on 0.0.0.0:8000 as specified in openenv.yaml
CMD ["uvicorn", "server.openenv_api:app", "--host", "0.0.0.0", "--port", "8000"]
