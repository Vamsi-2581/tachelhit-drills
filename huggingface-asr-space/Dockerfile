# Docker Space so /transcribe and /align are first-class FastAPI routes served by uvicorn
# (not Gradio-mounted routes subject to Gradio's catch-all / CSRF protection).
FROM python:3.10-slim

# ffmpeg + libsndfile for librosa to decode audio out of mp4/wav; build tools for the
# few NeMo dependencies that compile.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libsndfile1 build-essential git \
    && rm -rf /var/lib/apt/lists/*

# Run as the non-root "user" expected by HF Spaces, with a writable HF cache.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface \
    NEMO_CACHE_DIR=/home/user/.cache/torch/NeMo

WORKDIR /home/user/app

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir Cython "numpy<2.0.0" \
    && pip install --no-cache-dir torch torchaudio --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

COPY --chown=user . .

EXPOSE 7860
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
