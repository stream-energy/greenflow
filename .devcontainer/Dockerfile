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
ENV TZ="Europe/Paris"

RUN --mount=type=cache,target=/var/cache/pacman pacman-key --init
RUN --mount=type=cache,target=/var/cache/pacman yes | pacman -Sy archlinux-keyring && yes | pacman -Su
RUN --mount=type=cache,target=/var/cache/pacman pacman -Syu --noconfirm
RUN --mount=type=cache,target=/var/cache/pacman pacman -Syu --noconfirm sudo base-devel fish direnv git curl docker openssh
RUN --mount=type=cache,target=/var/cache/pacman pacman -Syu --noconfirm lsd ripgrep fzf bat prettyping
# RUN --mount=type=cache,target=/var/cache/pacman pacman -Syu --noconfirm python python-poetry
RUN --mount=type=cache,target=/var/cache/pacman pacman -Syu --noconfirm kubectl helm helmfile
RUN --mount=type=cache,target=/var/cache/pacman pacman -Syu --noconfirm pyenv
# RUN --mount=type=cache,target=/var/cache/pacman pacman -Syu --noconfirm nix

RUN groupadd -g ${USER_GID} ${USERNAME} && \
  useradd -u ${USER_UID} -g ${USER_GID} -m -s /usr/bin/fish -d /home/${USERNAME} ${USERNAME} && \
  echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME && \
  chown ${USERNAME}:${USERNAME} "/home/${USERNAME}/.bashrc"

RUN --mount=type=cache,target=/home/${USERNAME}/.pyenv sudo -u ${USERNAME} pyenv install 3.9.13
RUN --mount=type=cache,target=/home/${USERNAME}/.pyenv sudo -u ${USERNAME} pyenv global 3.9.13

WORKDIR /home/${USERNAME}

RUN sudo usermod -a -G docker g
RUN groupadd -g ${DOCKER_GID} host_docker
RUN sudo usermod -a -G ${DOCKER_GID} g

COPY --from=ext-preloader /ext-preloader /usr/bin/ext-preloader

COPY .devcontainer/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh
ENTRYPOINT [ "/docker-entrypoint.sh" ]

COPY .devcontainer/direnv.toml /etc/
RUN sudo -u ${USERNAME} mkdir -p /home/g/.config/direnv
# ENV XDG_CONFIG_HOME=/home/g/.config
COPY .devcontainer/direnv.toml /home/g/.config/direnv/direnv.toml

# COPY .devcontainer/nix.conf /etc/nix/nix.conf
# COPY .devcontainer/envrc /etc/envrc
# COPY .devcontainer/bash.bashrc /etc/bash.bashrc
# ENV ENV="/etc/envrc" BASH_ENV="/etc/envrc"


# RUN sudo usermod -a -G nix-users g
# RUN sudo -u ${USERNAME} nix-channel --add https://nixos.org/channels/nixpkgs-unstable
# RUN sudo -u ${USERNAME} nix-channel --update
# ARG NIX_INSTALL_SCRIPT=https://nixos.org/nix/install
# RUN curl -L ${NIX_INSTALL_SCRIPT} | sudo -u ${USERNAME} NIX_INSTALLER_NO_MODIFY_PROFILE=1 sh
# COPY .devcontainer/devcontainer.sh /etc/profile.d/devcontainer.sh

# RUN sudo -HEu ${USERNAME} nix-env -if https://github.com/nix-community/lorri/archive/canon.tar.gz

RUN cut -f1 -d':' < /etc/group | xargs -l sudo gpasswd -a g
WORKDIR /home/${USERNAME}
RUN sudo -u ${USERNAME} git clone https://aur.archlinux.org/yay-bin
WORKDIR /home/${USERNAME}/yay-bin


USER ${USER_UID}:${DOCKER_GID}
RUN makepkg -si --noconfirm
RUN yay -S --noconfirm rancher-k3d-bin
ADD https://api.github.com/repos/reisub0/dot-devcontainer/git/refs/heads/main /tmp/version.json
RUN --mount=type=cache,target=/home/${USERNAME}/.dot git clone --bare https://github.com/reisub0/dot-devcontainer ~/.dot
RUN --mount=type=cache,target=/home/${USERNAME}/.dot git --git-dir=$HOME/.dot --work-tree=$HOME pull
RUN --mount=type=cache,target=/home/${USERNAME}/.dot git --git-dir=$HOME/.dot --work-tree=$HOME checkout -f
RUN bash ~/install.sh

ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
