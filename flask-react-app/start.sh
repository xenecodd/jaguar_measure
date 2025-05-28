#!/bin/bash

# Zaman bilgisini WorldTimeAPI'den al
datetime=$(curl -s http://worldtimeapi.org/api/timezone/Etc/UTC | grep utc_datetime | cut -d '"' -f4)

# ISO 8601 formatından temizle
cleaned=$(echo "$datetime" | cut -d '.' -f1 | sed 's/T/ /')
# Sistemin saatini güncelle
sudo date -s "$cleaned"

set -euo pipefail

GREEN="\033[0;32m"
RED="\033[0;31m"
NC="\033[0m"
# Doğru dizine git
cd /home/developer/Project/jaguar_measure/flask-react-app  # docker-compose.yml buradaysa
# === Get IP address with retry logic ===
echo -e "${GREEN}Detecting host machine IP address...${NC}"

TRIES=5
DELAY=2
IP_ADDRESS=""

for i in $(seq 1 $TRIES); do
    IP_ADDRESS=$(ip route get 1.1.1.1 2>/dev/null | awk '{print $7; exit}' || true)
    if [[ -n "$IP_ADDRESS" ]]; then
        echo -e "${GREEN}Detected IP address: $IP_ADDRESS${NC}"
        break
    fi
    echo -e "${RED}Attempt $i: Network not ready. Retrying in ${DELAY}s...${NC}"
    sleep $DELAY
done

if [[ -z "$IP_ADDRESS" ]]; then
    echo -e "${RED}Failed to detect IP address after $TRIES attempts. Exiting.${NC}"
    exit 1
fi

# === Write IP to .env file ===
echo -e "${GREEN}Saving IP address to .env file...${NC}"
echo "IP_ADDRESS=$IP_ADDRESS" > .env

# === Start Docker containers ===
echo -e "${GREEN}Starting Docker containers...${NC}"
if sudo /usr/bin/docker compose up -d; then
    echo -e "${GREEN}Docker containers started successfully.${NC}"
else
    echo -e "${RED}Failed to start Docker containers.${NC}"
    exit 1
fi

# === Helpful output ===
echo -e "\n${GREEN}Useful commands:${NC}"
echo -e "  ${GREEN}Stop containers:${NC}         sudo docker compose down"
echo -e "  ${GREEN}View logs:${NC}               sudo docker compose logs -f"
echo -e "${GREEN}Opening browser to http://$IP_ADDRESS:3000${NC}"
