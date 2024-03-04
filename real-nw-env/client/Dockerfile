##################################################################################
##	INTELLECTUAL PROPERTY NOTE						##
##										##
##	Large parts of this Dockerfile originate from the 			##
##	Open Quantum Safe "OpenSSL3" Demo [1] and were adapted to the 		##
##	needs of the Master's thesis by	Joshua Drexel at			##
##	Lucerne University of Applied Sciences and Arts				##
##										##
##	[1] https://github.com/open-quantum-safe/oqs-demos/tree/main/openssl3	##
##################################################################################

# Multi-stage build: First the full builder image:

ARG INSTALLDIR_OPENSSL=/opt/openssl32
ARG OPENSSL_BRANCH="openssl-3.2.0"
ARG INSTALLDIR_LIBOQS=/opt/liboqs
ARG LIBOQS_BRANCH="0.9.0"
ARG OQSPROVIDER_BRANCH="0.5.2"
ARG INSTALLDIR_STIMER=/opt/stimer

# Path to dir containing s_timer.c
ARG SOURCEDIR_STIMER=../../tls-client

# Compile with all the available optimizations for the native architecture
ARG LIBOQS_BUILD_DEFINES="-DOQS_DIST_BUILD=OFF"

# Define the degree of parallelism when building the image; leave the number away only if you know what you are doing
# Why hardcoding this instead of using nproc?
ARG MAKE_DEFINES="-j 8"

ARG SIG_ALG="dilithium3"
ARG DEFAULT_GROUPS="x25519_kyber768"

FROM alpine:3.19 as buildopenssl
# Take in all global args
ARG INSTALLDIR_OPENSSL
ARG OPENSSL_BRANCH
ARG INSTALLDIR_LIBOQS
ARG LIBOQS_BRANCH
ARG OQSPROVIDER_BRANCH
ARG LIBOQS_BUILD_DEFINES
ARG MAKE_DEFINES
ARG SIG_ALG

LABEL version="1"
ENV DEBIAN_FRONTEND noninteractive

RUN apk update && \
    apk upgrade

# Get all software packages required for builing openssl
RUN apk add build-base \
            linux-headers \
            libtool \
            automake \
            autoconf \
            make \
            git \
            wget

# get current openssl sources
RUN mkdir /optbuild && \
    cd /optbuild && \
    git clone --depth 1 --branch ${OPENSSL_BRANCH} https://github.com/openssl/openssl.git

# build OpenSSL3
WORKDIR /optbuild/openssl
RUN LDFLAGS="-Wl,-rpath -Wl,${INSTALLDIR_OPENSSL}/lib64" ./config shared --prefix=${INSTALLDIR_OPENSSL} && \
    make ${MAKE_DEFINES} && \
    make install && \
    if [ -d ${INSTALLDIR_OPENSSL}/lib64 ]; then ln -s ${INSTALLDIR_OPENSSL}/lib64 ${INSTALLDIR_OPENSSL}/lib; fi && \
    if [ -d ${INSTALLDIR_OPENSSL}/lib ]; then ln -s ${INSTALLDIR_OPENSSL}/lib ${INSTALLDIR_OPENSSL}/lib64; fi

FROM alpine:3.19 as buildliboqs
# Take in all global args
ARG INSTALLDIR_OPENSSL
ARG OPENSSL_BRANCH
ARG INSTALLDIR_LIBOQS
ARG LIBOQS_BRANCH
ARG OQSPROVIDER_BRANCH
ARG LIBOQS_BUILD_DEFINES
ARG MAKE_DEFINES
ARG SIG_ALG

LABEL version="1"
ENV DEBIAN_FRONTEND noninteractive

# Get all software packages required for builing liboqs:
RUN apk add build-base \
            linux-headers \
            libtool \
            automake \
            autoconf \
            cmake \
            ninja \
            make \
            git \
            wget

# Get OpenSSL image (from cache)
COPY --from=buildopenssl ${INSTALLDIR_OPENSSL} ${INSTALLDIR_OPENSSL}

RUN mkdir /optbuild && \
    cd /optbuild && \
    git clone --depth 1 --branch ${LIBOQS_BRANCH} https://github.com/open-quantum-safe/liboqs

WORKDIR /optbuild/liboqs
RUN mkdir build && \
    cd build && \
    cmake -G"Ninja" .. \
          -DOPENSSL_ROOT_DIR=${INSTALLDIR_OPENSSL} ${LIBOQS_BUILD_DEFINES} \
          -DCMAKE_INSTALL_PREFIX=${INSTALLDIR_LIBOQS} && \
    ninja install

FROM alpine:3.19 as buildoqsprovider
# Take in all global args
ARG INSTALLDIR_OPENSSL
ARG OPENSSL_BRANCH
ARG INSTALLDIR_LIBOQS
ARG LIBOQS_BRANCH
ARG OQSPROVIDER_BRANCH
ARG LIBOQS_BUILD_DEFINES
ARG MAKE_DEFINES
ARG SIG_ALG
ARG DEFAULT_GROUPS

LABEL version="1"
ENV DEBIAN_FRONTEND noninteractive
ENV LIBOQS_SRC_DIR=${INSTALLDIR_LIBOQS}

# Get all software packages required for builing oqsprovider
RUN apk add build-base \
            linux-headers \
            libtool \
            cmake \
            ninja \
            git \
            wget \
            python3 \
            py3-jinja2 \
            py3-yaml \
            py3-tabulate && \
        ln -sf python3 /usr/bin/python

RUN mkdir /optbuild && \
    cd /optbuild && \
    git clone --depth 1 --branch ${OQSPROVIDER_BRANCH} https://github.com/open-quantum-safe/oqs-provider.git

# Get openssl32 and liboqs
COPY --from=buildopenssl ${INSTALLDIR_OPENSSL} ${INSTALLDIR_OPENSSL}
COPY --from=buildliboqs ${INSTALLDIR_LIBOQS} ${INSTALLDIR_LIBOQS}
COPY --from=buildliboqs /optbuild/liboqs/docs/ ${INSTALLDIR_LIBOQS}/docs

# Activate more signature algorithms than default
COPY generate.yml /optbuild/oqs-provider/oqs-template/
WORKDIR /optbuild/oqs-provider
RUN python3 oqs-template/generate.py

# build & install provider
RUN liboqs_DIR=${INSTALLDIR_LIBOQS} \
    cmake \
        -DOPENSSL_ROOT_DIR=${INSTALLDIR_OPENSSL} \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_PREFIX_PATH=${INSTALLDIR_OPENSSL} \
        -S . -B _build && \
    cmake --build _build  && \
    cmake --install _build

# Install oqsprovider.so and change default config to enable oqs-provider
RUN cp _build/lib/oqsprovider.so ${INSTALLDIR_OPENSSL}/lib64/ossl-modules && \
    sed -i "s/default = default_sect/default = default_sect\noqsprovider = oqsprovider_sect/g" ${INSTALLDIR_OPENSSL}/ssl/openssl.cnf && \
    sed -i "s/\[default_sect\]/\[default_sect\]\nactivate = 1\n\[oqsprovider_sect\]\nactivate = 1\n/g" ${INSTALLDIR_OPENSSL}/ssl/openssl.cnf && \
    sed -i "s/providers = provider_sect/providers = provider_sect\nssl_conf = ssl_sect\n\n\[ssl_sect\]\nsystem_default = system_default_sect\n\n\[system_default_sect\]\nGroups = \$ENV\:\:DEFAULT_GROUPS\n/g" ${INSTALLDIR_OPENSSL}/ssl/openssl.cnf && \
    sed -i "s/HOME\t\t\t= ./HOME           = .\nDEFAULT_GROUPS = "${DEFAULT_GROUPS}"/g" ${INSTALLDIR_OPENSSL}/ssl/openssl.cnf

WORKDIR ${INSTALLDIR_OPENSSL}/bin
# set path to use 'new' openssl. Dyn libs have been properly linked in to match
ENV PATH="${INSTALLDIR_OPENSSL}/bin:${PATH}"


FROM alpine:3.19 as buildstimer
# Take in all global args
ARG INSTALLDIR_OPENSSL
ARG INSTALLDIR_STIMER
ARG SOURCEDIR_STIMER

LABEL version="1"
ENV DEBIAN_FRONTEND noninteractive

# Get all software packages required for builing s_timer
RUN apk add build-base \
            linux-headers \
            argp-standalone \
            openssl-dev

COPY --from=buildoqsprovider ${INSTALLDIR_OPENSSL} ${INSTALLDIR_OPENSSL}

ENV PATH="${INSTALLDIR_OPENSSL}/bin:${PATH}"
ENV LD_LIBRARY_PATH="${INSTALLDIR_OPENSSL}/lib:${LD_LIBRARY_PATH}"

RUN mkdir ${INSTALLDIR_STIMER}
COPY ${SOURCEDIR_STIMER}/s_timer.c ${INSTALLDIR_STIMER}/s_timer.c

WORKDIR ${INSTALLDIR_STIMER}
RUN gcc -Wall -Wextra -Wpedantic -O3 s_timer.c -o s_timer -lssl -lcrypto -largp


## second stage: Only create minimal image without build tooling and intermediate build results generated above:
FROM alpine:3.19 as dev
# Take in all global args
ARG INSTALLDIR_OPENSSL
ARG INSTALLDIR_STIMER

# Install python3
RUN apk add python3 && \
    ln -sf python3 /usr/bin/python

# Only retain the ${INSTALLDIR_OPENSSL} and ${INSTALLDIR_STIMER}/s_timer in the final image
COPY --from=buildoqsprovider ${INSTALLDIR_OPENSSL} ${INSTALLDIR_OPENSSL}

RUN mkdir ${INSTALLDIR_STIMER}

COPY --from=buildstimer ${INSTALLDIR_STIMER}/s_timer ${INSTALLDIR_STIMER}/s_timer

# set path to use 'new' openssl. Dyn libs have been properly linked in to match
ENV PATH="${INSTALLDIR_OPENSSL}/bin:${PATH}"
ENV LD_LIBRARY_PATH="${INSTALLDIR_OPENSSL}/lib:${LD_LIBRARY_PATH}"

# Get certificates
RUN mkdir /pqc-tls-tests /pqc-tls-tests/pki
COPY ./pki/ /pqc-tls-tests/pki

# Get run-benchmark script
COPY run-bench_real-nw-assessmnt.py /pqc-tls-tests/run-bench_real-nw-assessmnt.py

# Prepare directory for the results-files
RUN mkdir /pqc-tls-tests/testresults

FROM dev

WORKDIR /pqc-tls-tests

STOPSIGNAL SIGTERM
