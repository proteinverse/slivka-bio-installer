# syntax=docker/dockerfile:1

FROM alpine:3.21 AS sav_gol-build

RUN apk add --no-cache build-base
ADD --checksum=sha256:cd6662505a2e411218f5d34ccb8bf206a6148b6c79b1cc8e4fa4dc11dfd00534 \
    https://www.pks.mpg.de/~tisean/TISEAN_3.0.1.tar.gz /etc/src/
RUN tar -xvzf /etc/src/TISEAN_3.0.1.tar.gz -C /etc/src/
WORKDIR /etc/src/Tisean_3.0.1
ENV CC="gcc --std=c89"
RUN ./configure
WORKDIR /etc/src/Tisean_3.0.1/source_c
RUN make sav_gol

FROM alpine:3.21 AS disembl-build

RUN apk add --no-cache build-base patch
ADD --checksum=sha256:34b1eb1f388f36a6d6ff208130f0ee4e368047fff7d70b40eaf7e4aa1660858c \
    http://dis.embl.de/DisEMBL-1.4.tgz /etc/src/
RUN tar -xvzf /etc/src/DisEMBL-1.4.tgz -C /etc/src/
ADD build-data/DisEMBL.patch /etc/src/DisEMBL-1.4/DisEMBL.py.patch
WORKDIR /etc/src/DisEMBL-1.4
RUN gcc -O3 disembl.c -o disembl
RUN patch DisEMBL.py DisEMBL.py.patch

FROM alpine:3.21

RUN apk add --no-cache python3 py3-biopython
RUN addgroup -S disembl && adduser -S -s /bin/sh -G disembl disembl
COPY --from=sav_gol-build --chown=disembl:disembl --chmod=555 /etc/src/Tisean_3.0.1/source_c/sav_gol /usr/local/bin/sav_gol
COPY --from=disembl-build --chown=disembl:disembl --chmod=555 /etc/src/DisEMBL-1.4/disembl /usr/local/bin/jensen_net
COPY --from=disembl-build --chown=disembl:disembl --chmod=555 /etc/src/DisEMBL-1.4/DisEMBL.py /usr/local/bin/DisEMBL
USER disembl
ENTRYPOINT ["/usr/bin/env", "python3", "/usr/local/bin/DisEMBL"]
