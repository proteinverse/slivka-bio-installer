FROM debian:bullseye-slim

RUN apt update && \
    apt install -y "mafft=7.475-1"
ENTRYPOINT ["mafft"]
