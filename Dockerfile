# CPU reference image. The service binds to 127.0.0.1 inside the container by default; to reach it from the host
# run with --network host (Linux) or pass --host 0.0.0.0 and publish the port to 127.0.0.1 only:
#   docker run --rm -p 127.0.0.1:8765:8765 -v "$PWD/footage:/footage:ro" -v sg_work:/work scenegap-edge --host 0.0.0.0
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 SG_WORKDIR=/work HF_HOME=/work/hf
WORKDIR /app
COPY requirements.txt requirements-ml.txt ./
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir -r requirements-ml.txt
COPY scenegap ./scenegap
COPY web ./web
COPY eval/results/calibration.json ./eval/results/calibration.json
RUN useradd -m sg && mkdir -p /work && chown sg /work
USER sg
EXPOSE 8765
ENTRYPOINT ["python", "-m", "scenegap", "--device", "cpu"]
