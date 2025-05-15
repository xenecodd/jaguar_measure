#!/bin/bash

set -euo pipefail

GREEN="\033[0;32m"
RED="\033[0;31m"
NC="\033[0m"

# Get the IP address of the host machine
echo -e "${GREEN}Detecting host machine IP address...${NC}"
IP_ADDRESS=$(ip route get 1 | awk '{print $7; exit}')

# Is the IP address valid?
if [[ -z "$IP_ADDRESS" ]]; then
    echo -e "${RED}Failed to detect IP address.${NC}"
    exit 1
fi

# Write the IP address to the .env file
touch .env || echo "Creating .env file..."
echo "IP_ADDRESS=$IP_ADDRESS" > .env
echo -e "${GREEN}IP address saved to .env: $IP_ADDRESS${NC}"

# Start with Docker Compose
echo -e "${GREEN}Starting Docker containers...${NC}"
if sudo docker compose up -d; then
    echo -e "${GREEN}Docker containers started successfully.${NC}"
else
    echo -e "${RED}Failed to start Docker containers.${NC}"
    exit 1
fi

# Informational messages
echo -e "\n${GREEN}Useful commands:${NC}"
echo -e "  ${GREEN}Stop containers:${NC}         sudo docker compose down"
echo -e "  ${GREEN}View logs:${NC}               sudo docker compose logs -f"
echo -e "  ${GREEN}Access web interface:${NC}    http://$IP_ADDRESS:3000"
