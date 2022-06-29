# See here for image contents: https://github.com/microsoft/vscode-dev-containers/tree/v0.238.0/containers/debian/.devcontainer/base.Dockerfile

# [Choice] Debian version (use bullseye on local arm64/Apple Silicon): bullseye, buster
FROM ghcr.io/xtruder/nix-devcontainer:latest
# ** [Optional] Uncomment this section to install additional packages. **
# RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
#     && apt-get -y install --no-install-recommends <your-package-list-here>
ARG DOCKER_GID=959
RUN sudo groupadd -g ${DOCKER_GID} docker && sudo usermod -a -G docker ${USERNAME} 
