# Greenflow

## Nix Crash Course

### Introduction to Nix

Nix is a powerful package manager for Linux and other Unix systems that makes package management reliable and reproducible. It provides atomic upgrades and rollbacks, side-by-side installation of multiple versions of a package, multi-user package management and easy setup of build environments.

This documentation aims to help a beginner get started with a project using Nix and a `flake.nix` configuration file.

### Installing Nix

To begin, you will need to have [Nix installed](https://nixos.org/download.html).

```bash
sh <(curl -L https://nixos.org/nix/install) --daemon
```

The script will download and install the Nix package manager. After the installation process, you may need to add Nix to your `PATH`. The installer will provide instructions on how to do this, which usually involves adding a line to your `.bashrc`, `.bash_profile`, or `.zshrc`.

Ensure that Nix has been installed correctly by running:

```bash
`nix --version`
```

### Understanding the flake.nix file

The provided `flake.nix` file describes the inputs and outputs for the project. The `inputs` section lists the sources that the project depends on. The `outputs` section describes how these inputs should be used to build this project.

### Setting up the Nix Environment

This project uses a development environment defined by the [Devenv project](https://devenv.sh/). The development environment includes multiple packages such as `micromamba`, `alejandra`, `kubectl`, `kubernetes-helm`, `ruff`, `just`, `time`, `gcc`, `kube3d`, `atuin`, `fish` and `wrapHelm`.

After installing Nix and understanding the `flake.nix`, follow these steps:

1. Clone the project.
2. Navigate to the project directory in a terminal window.
3. To activate the development environment, run the following command:

```bash
./enter
init
```

### Conclusion

With this, you should have a basic understanding of Nix and how to use it with the given `flake.nix` file. If you have questions or encounter issues, you may want to check the Nix documentation or the documentation for the specific inputs in the `flake.nix` file.
