# Docker Troubleshooting

This document provides solutions to common Docker-related issues and general troubleshooting guidance.

## `db` Service Fails to Start

### Issue 1: Incorrect Dockerfile Instructions

**Symptom:** The `db` service fails to build, and the logs show errors related to `apt-get` or package installation.

**Cause:** The `database/Dockerfile` was using Debian-based commands and repositories on an Ubuntu-based image (`mcr.microsoft.com/mssql/server:2022-latest` is based on Ubuntu 22.04).

**Solution:** The `database/Dockerfile` was corrected to use the appropriate Ubuntu repositories and commands.

```diff
- RUN curl https://packages.microsoft.com/config/debian/12/prod.list > /etc/apt/sources.list.d/mssql-release.list
+ RUN curl https://packages.microsoft.com/config/ubuntu/22.04/prod.list > /etc/apt/sources.list.d/mssql-release.list
```

### Issue 2: Missing Environment Variables

**Symptom:** The `db` service starts and then immediately exits. The `docker-compose up` command shows a warning like `The "DB_PASSWORD" variable is not set`.

**Cause:** The `docker-compose.yml` file requires a `DB_PASSWORD` environment variable to be set for the `db` service. This variable is not defined in the environment.

**Solution:** Create a `.env` file in the root of the project. You can copy the `.env.example` file to create it:

```bash
cp .env.example .env
```

Ensure that the variables in the `.env` file are set to appropriate values for your environment.

## General Docker Troubleshooting

If you encounter issues with a Docker container, here are some general steps to diagnose the problem:

1.  **Check Container Logs:** The first step is always to check the logs of the container that is failing.
    ```bash
    docker-compose logs <service_name>
    ```
    Replace `<service_name>` with the name of the service from your `docker-compose.yml` file (e.g., `db`, `backend`).

2.  **Inspect the Dockerfile:** Ensure that the Dockerfile for the service is using the correct base image and that all commands are compatible with the base image's operating system.

3.  **Verify Environment Variables:** Check that all required environment variables are set. These are often defined in a `.env` file or passed directly to the `docker-compose` command.

4.  **Rebuild the Image:** If you've made changes to a Dockerfile or the application code, you may need to rebuild the Docker image.
    ```bash
    docker-compose up --build
    ```
    To rebuild a specific service:
    ```bash
    docker-compose up --build <service_name>
    ```

5.  **Enter the Container:** For more in-depth debugging, you can get a shell inside the running container.
    ```bash
    docker-compose exec <service_name> /bin/bash
    ```
    This allows you to inspect the filesystem, run commands, and check the environment inside the container.
