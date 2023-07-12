#!/bin/bash
set -e

if [ -z "${FTP_DIR}" ]; then
  echo "FTP_DIR is not set. Please set it in your docker-compose.yaml file."
  exit 1
fi

chown -R user:user "${FTP_DIR}"
chown -R "${FTP_USER}:${FTP_USER}" "${FTP_DIR}"

exec "$@"
