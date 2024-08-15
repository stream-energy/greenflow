# Requirements

## Local Project Setup

Setting up the GreenFlow project locally is streamlined thanks to the use of Nix for dependency management and environment configuration. This approach ensures consistency across different development environments and simplifies the setup process.

### Prerequisites

Before you begin, ensure you have the following installed on your system:

1. **Nix**: We use the Determinate Systems Nix installer for a consistent setup.
2. **direnv** (optional, recommended): This tool automatically loads and unloads environment variables based on the current directory.
3. **Docker**: Required for running Docker Compose to set up Tailscale, Caddy, Prometheus, Victoria Metrics, and Grafana.
4. **Docker Compose**: Used to manage multi-container Docker applications.

### Installation Steps

1. **Install Nix** (if not already installed):

   Use the Determinate Systems Nix installer by running the following command in your terminal:

   ```bash
   curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix | sh -s -- install
   ```

2. **Install `direnv`**:

   Installation methods may vary depending on your operating system. For most Unix-like systems, you can use your package manager. For example:

   - On macOS with Homebrew:
     ```bash
     brew install direnv
     ```
   - On Ubuntu or Debian:
     ```bash
     sudo apt-get install direnv
     ```

   For other systems, refer to the [direnv installation guide](https://direnv.net/docs/installation.html).

3. **Install Docker**:

   Follow the [official Docker installation guide](https://docs.docker.com/get-docker/) for your operating system.

4. **Install Docker Compose**:

   Follow the [official Docker Compose installation guide](https://docs.docker.com/compose/install/) for your operating system.

5. **Clone the GreenFlow repository**:

   ```bash
   git clone https://github.com/autolyticus/greenflow.git
   cd greenflow
   ```

6. **Set up direnv**:

   ```bash
   direnv allow
   ```

   This command should automatically download and set up all required dependencies, including Ansible, Python, and any other project-specific tools.

### Verifying the Setup

After running `nix develop`, your environment should be ready for GreenFlow development. You can verify the setup by running:

```bash
python --version
ansible --version
```

These commands should display the versions of Python and Ansible specified in the project's Nix configuration.

### Automatic Environment Activation

With `direnv` properly set up, the Nix environment will automatically activate when you enter the project directory and deactivate when you leave it. This ensures that you're always using the correct versions of tools and dependencies for the GreenFlow project.

### Troubleshooting

If you encounter any issues during the setup process:

1. Ensure that Nix and direnv are correctly installed and configured.
2. Check that your `.envrc` file is properly set up and allowed by direnv.
3. If changes are made to the Nix configuration, you may need to run `nix develop` again to update the environment.

### flake.nix Configuration

The `flake.nix` file in the project root provides a clear definition of the dependencies and environment setup for the GreenFlow project. It includes:

-   **Nix Packages**: A list of packages required for the project, such as `micromamba`, `kubectl`, `kubernetes-helm`, and more.
-   **Scripts**: Scripts for resetting the environment and setting up dependencies.
-   **Environment Variables**: Configuration for environment variables and shell hooks.

This configuration ensures that all necessary tools and dependencies are available and correctly set up for the GreenFlow project.

### Additional Tools

If you do not have networking access to expose your local experiment machine to the Kubernetes cluster, you will need to set up Tailscale, Caddy, Victoria Metrics, and Grafana using Docker Compose from `$PROJECT_ROOT/deploy` [here](./prometheus-setup.md).
