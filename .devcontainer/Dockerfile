FROM golang:1.17 as ext-preloader

ADD .devcontainer/ext-preloader /src
WORKDIR /src
RUN go build -o /ext-preloader main.go 

FROM docker.io/library/archlinux:latest

# Setup environment variables
ENV USERNAME=g
ENV USER_UID=1000
ENV USER_GID=${USER_UID}
ENV DOCKER_GID=959

RUN --mount=type=cache,target=/var/cache/pacman pacman -Syu --noconfirm
RUN --mount=type=cache,target=/var/cache/pacman pacman -Syu --noconfirm sudo base-devel fish direnv git curl docker
RUN --mount=type=cache,target=/var/cache/pacman pacman -Syu --noconfirm lsd ripgrep fzf
RUN --mount=type=cache,target=/var/cache/pacman pacman -Syu --noconfirm python python-poetry
RUN --mount=type=cache,target=/var/cache/pacman pacman -Syu --noconfirm kubectl helm helmfile
# RUN --mount=type=cache,target=/var/cache/pacman pacman -Syu --noconfirm nix

RUN groupadd -g ${USER_GID} ${USERNAME} && \
  useradd -u ${USER_UID} -g ${USER_GID} -m -s /usr/bin/fish -d /home/${USERNAME} ${USERNAME} && \
  echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME && \
  chown ${USERNAME}:${USERNAME} "/home/${USERNAME}/.bashrc"

WORKDIR /home/${USERNAME}

RUN sudo usermod -a -G docker g

COPY --from=ext-preloader /ext-preloader /usr/bin/ext-preloader

COPY .devcontainer/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh
ENTRYPOINT [ "/docker-entrypoint.sh" ]

COPY .devcontainer/direnv.toml /etc/
RUN sudo -u ${USERNAME} mkdir -p /home/g/.config/direnv
# ENV XDG_CONFIG_HOME=/home/g/.config
COPY .devcontainer/direnv.toml /home/g/.config/direnv/direnv.toml

COPY .devcontainer/nix.conf /etc/nix/nix.conf
# RUN sudo usermod -a -G nix-users g
# RUN sudo -u ${USERNAME} nix-channel --add https://nixos.org/channels/nixpkgs-unstable
# RUN sudo -u ${USERNAME} nix-channel --update
ARG NIX_INSTALL_SCRIPT=https://nixos.org/nix/install
RUN curl -L ${NIX_INSTALL_SCRIPT} | sudo -u ${USERNAME} NIX_INSTALLER_NO_MODIFY_PROFILE=1 sh
COPY .devcontainer/devcontainer.sh /etc/profile.d/devcontainer.sh


USER ${USER_UID}:${USER_GID}
