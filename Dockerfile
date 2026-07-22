FROM python:3.14-slim
WORKDIR /app

RUN apt-get update && apt-get install -y curl gnupg && \
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y nodejs && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/web/package.json src/web/package-lock.json* src/web/
RUN cd src/web && npm install
COPY src/web/ src/web/
RUN cd src/web && npm run build && \
    cp -r .next/static .next/standalone/.next/ && \
    mkdir -p .next/standalone/public && \
    [ -d public ] && cp -r public/* .next/standalone/public/ 2>/dev/null || true

COPY . .

EXPOSE 7860
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
CMD ["/entrypoint.sh"]
