#!/bin/bash

#
## Setup script to install oqs-provider and the required OpenSSL and liboqs versions
#

# Install dependencies
sudo apt install -y astyle cmake gcc git ninja-build libssl-dev python3-pytest python3-pytest-xdist unzip xsltproc doxygen graphviz python3-yaml valgrind

cd ~

# Get the source code
git clone -b 0.5.2 https://github.com/open-quantum-safe/oqs-provider.git
cd oqs-provider

# Set OpenSSL and liboqs versions
export LIBOQS_BRANCH="0.9.0"
export OPENSSL_BRANCH="openssl-3.2.0"

# Build oqs-provider (along with OpenSSL and liboqs)
bash scripts/fullbuild.sh

# Install oqs-provider
cmake --install _build
