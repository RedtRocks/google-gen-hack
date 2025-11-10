#!/bin/bash
# Azure App Service startup script

echo "Starting Legal Document Demystifier..."

# Ensure we're in the correct directory
cd /home/site/wwwroot

# Set Python path
export PYTHONPATH=/home/site/wwwroot:$PYTHONPATH

# Start the application
python main.py
