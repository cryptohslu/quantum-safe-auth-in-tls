#!/bin/sh
set -euo pipefail

# This scripts prepares the generate.yml file

liboqs_version=0.10.1
oqsprovider_version=0.6.1

working_path=$(pwd)
tmpdir=$(mktemp -d)
cd $tmpdir

echo -n "Downloading liboqs and oqs-provider."
curl -Lso oqs.tar.gz https://github.com/open-quantum-safe/liboqs/archive/refs/tags/$liboqs_version.tar.gz
echo -n "."
curl -Lso oqsprovider.tar.gz https://github.com/open-quantum-safe/oqs-provider/archive/refs/tags/$oqsprovider_version.tar.gz
echo -n "."
echo "done"

echo -n "Extracting tarballs..."
tar -xf oqs.tar.gz
tar -xf oqsprovider.tar.gz
echo "done"

echo -n "Modifying generate.yml..."
cd oqs-provider-$oqsprovider_version
sed -i -e 's/enable: false/enable: true/g' oqs-template/generate.yml
echo "done"

echo -n "Copying generate.yml to working directory..."
cp oqs-template/generate.yml "$working_path"/generate.yml
echo "done"

echo -n "Deleting temporary files..."
cd "$working_path"
rm -rf $tmpdir
echo "done"
