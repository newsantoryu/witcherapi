#!/bin/bash
# Cyber-Visceral Link API Startup Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}[Cyber-Visceral Link]${NC} Starting API..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -r requirements.txt

# Create RAM disk log file if it doesn't exist
echo -e "${YELLOW}Setting up RAM disk log...${NC}"
sudo touch /dev/shm/witcher_events.log
sudo chmod 666 /dev/shm/witcher_events.log

# Start the API
echo -e "${GREEN}[Cyber-Visceral Link]${NC} API starting on http://0.0.0.0:8000"
echo -e "${GREEN}[Cyber-Visceral Link]${NC} WebSocket endpoint: ws://0.0.0.0:8000/ws"
echo -e "${GREEN}[Cyber-Visceral Link]${NC} API docs: http://0.0.0.0:8000/docs"
echo ""

# Run with uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
