#!/bin/bash

echo "Setting up AI Engine Environment..."

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip and install requirements
echo "Upgrading pip..."
python -m pip install --upgrade pip

echo "Installing requirements..."
pip install -r requirements.txt

echo "Setup complete! To activate the environment, run 'source AI_Engine/venv/bin/activate'"
echo "To start Jupyter, run 'jupyter notebook'"
