#!/usr/bin/env sh

# PYENV_ROOT=/home/g/.pyenv
pyenv install -s mambaforge
pyenv global mambaforge
pip install -U pip
pip install poetry

# PIP="${PYENV_ROOT}/versions/$(cat /home/g/.pyenv/version)/bin/pip"
# "$PIP" install --upgrade pip
# "$PIP" install poetry

echo "
username: $GRID5000_USERNAME
password: $GRID5000_PASSWORD
" > ~/.python-grid5000.yaml

chmod 600 ~/.python-grid5000.yaml
# sudo cp ca2019.grid5000.fr.pem /etc/ca-certificates/trust-source/anchors/
sudo cp api-proxy-lille-grid5000-fr-chain.pem /etc/ca-certificates/trust-source/anchors/api-proxy-lille-grid5000-fr-chain.crt
# sudo cp api-proxy-lille-grid5000-fr-chain.pem /usr/local/share/ca-certificates/api-grid5000-fr.crt
# sudo update-ca-certificates
sudo trust extract-compat
sudo update-ca-trust

sudo pacman -Sy --noconfirm rsync just

helm repo add grafana https://grafana.github.io/helm-charts
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

pushd /workspaces/greenflow
    git submodule update --init --recursive
popd

pushd /workspaces/greenflow/charts/theodolite/helm
    helm dep build
popd
pushd /workspaces/greenflow/charts/prometheus-community/charts/kube-prometheus-stack
    helm dep build
popd
