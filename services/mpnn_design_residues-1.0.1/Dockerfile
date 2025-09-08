# syntax=docker/dockerfile:1

FROM --platform=linux/amd64 nvidia/cuda:11.8.0-base-ubuntu22.04
ADD --chown=root:root --chmod=755 https://github.com/dauparas/ProteinMPNN.git#v1.0.1 /usr/local/ProteinMPNN

# Install base utilities
RUN apt-get update \
    && apt-get install -y build-essential \
    && apt-get install -y wget \
    && apt-get clean \
    && apt-get install python3 -y\
    && apt-get install python3-pip -y\
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip
RUN pip install \
    numpy==1.26.3 torch==2.0.0+cu118 torchvision==0.15.1+cu118 torchaudio==2.0.1 \
    --index-url https://download.pytorch.org/whl/cu118
RUN pip install biopython

ENV PYTHONPATH=/usr/local/ProteinMPNN
ENV PROTEIN_MPNN=/usr/local/ProteinMPNN
