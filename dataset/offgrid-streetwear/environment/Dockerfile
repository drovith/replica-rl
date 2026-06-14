FROM python:3.12-slim
WORKDIR /app

RUN pip install --no-cache-dir playwright==1.60.0 \
 && playwright install --with-deps chromium
RUN apt-get update \
 && apt-get install -y --no-install-recommends fonts-noto-color-emoji fonts-liberation \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir open-clip-torch==3.3.0 scipy==1.17.1 pillow==12.2.0 numpy==2.4.6

ENV D2C_CLIP_CACHE=/opt/clip
RUN mkdir -p /opt/clip \
 && python -c "import open_clip; open_clip.create_model_and_transforms('ViT-B-32', pretrained='openai', cache_dir='/opt/clip')" \
 && chmod -R a+rX /opt/clip

COPY design ./design
COPY assets ./assets
