# Use a recent CUDA image if you have an NVIDIA GPU on the host
FROM nvidia/cuda:12.2.0-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y git curl wget build-essential python3 python3-pip && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY ./requirements.txt /app/requirements.txt
RUN python3 -m pip install --upgrade pip
RUN pip install -r /app/requirements.txt

# copy project files
COPY ./app /app

EXPOSE 8000
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
