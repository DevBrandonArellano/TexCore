# Use the official Microsoft SQL Server image as the base
FROM mcr.microsoft.com/mssql/server:2022-latest

# Switch to root user to install packages
USER root

# Install system dependencies required for the ODBC driver and tools
RUN apt-get update && apt-get install -y curl gnupg

# Add Microsoft's official repository for the ODBC driver
RUN curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /usr/share/keyrings/microsoft-prod.gpg
RUN curl https://packages.microsoft.com/config/ubuntu/22.04/prod.list > /etc/apt/sources.list.d/mssql-release.list

# Install the mssql-tools18 package
# The 'ACCEPT_EULA' is required for unattended installation
RUN apt-get update && ACCEPT_EULA=Y apt-get install -y mssql-tools18

# Switch back to the default mssql user
USER mssql
