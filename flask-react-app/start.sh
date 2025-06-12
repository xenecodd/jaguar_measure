#!/bin/bash

# Hata yönetimi ve strict mode
set -euo pipefail

# Renkli çıktı için değişkenler
GREEN="\033[0;32m"
RED="\033[0;31m"
YELLOW="\033[1;33m"
NC="\033[0m"

# === Zaman ayarlama fonksiyonu ===
set_time() {
    echo -e "${GREEN}Setting system time...${NC}"
    
    # UTC zamanını al
    datetime=$(curl -s https://api.api-ninjas.com/v1/worldtime?city=turkey | grep utc_datetime | cut -d '"' -f4 || echo "")
    
    # ISO 8601 formatını temizle (örnek: 2025-05-30T10:00:00.123456+00:00 => 2025-05-30 10:00:00)
    cleaned=$(echo "$datetime" | cut -d '.' -f1 | sed 's/T/ /')
    
    new_time=$(date -d "$cleaned" +"%Y-%m-%d %H:%M:%S" 2>/dev/null || echo "")
    
    if [[ -n "$new_time" ]]; then
        # Yeni zamanı sisteme ayarla (sudo gerekli)
        if sudo date -s "$new_time" >/dev/null 2>&1; then
            echo -e "${GREEN}System time set to: $new_time${NC}"
        else
            echo -e "${YELLOW}Warning: Could not set system time (permission issue?)${NC}"
        fi
    else
        echo -e "${YELLOW}Warning: Could not parse datetime${NC}"
    fi
}

# === Ana fonksiyon ===
main() {
    # Zaman ayarla
    set_time
    
    # Doğru dizine git
    PROJECT_DIR="/home/developer/Project/jaguar_measure/flask-react-app"
    
    if [[ ! -d "$PROJECT_DIR" ]]; then
        echo -e "${RED}Error: Project directory not found: $PROJECT_DIR${NC}"
        exit 1
    fi
    
    cd "$PROJECT_DIR"
    echo -e "${GREEN}Changed to directory: $(pwd)${NC}"
    
    # docker-compose.yml dosyası kontrolü
    if [[ ! -f "docker-compose.yaml" ]]; then
        echo -e "${RED}Error: docker-compose.yaml not found in current directory${NC}"
        exit 1
    fi
    
    # === IP adresi tespiti ===
    echo -e "${GREEN}Detecting host machine IP address...${NC}"
    TRIES=5
    DELAY=2
    IP_ADDRESS=""
    
    for i in $(seq 1 $TRIES); do
        # Birden fazla yöntem deneyelim
        IP_ADDRESS=$(ip route get 1.1.1.1 2>/dev/null | awk '{print $7; exit}' || \
                    hostname -I 2>/dev/null | awk '{print $1}' || \
                    ip addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v 127.0.0.1 | head -1 || \
                    echo "")
        
        if [[ -n "$IP_ADDRESS" && "$IP_ADDRESS" != "127.0.0.1" ]]; then
            echo -e "${GREEN}Detected IP address: $IP_ADDRESS${NC}"
            break
        fi
        
        echo -e "${YELLOW}Attempt $i: Network not ready or IP detection failed. Retrying in ${DELAY}s...${NC}"
        sleep $DELAY
    done
    
    if [[ -z "$IP_ADDRESS" || "$IP_ADDRESS" == "127.0.0.1" ]]; then
        echo -e "${RED}Failed to detect valid IP address after $TRIES attempts.${NC}"
        echo -e "${YELLOW}Using localhost as fallback...${NC}"
        IP_ADDRESS="localhost"
    fi
    
    # === .env dosyasına IP yaz ===
    echo -e "${GREEN}Saving IP address to .env file...${NC}"
    echo "IP_ADDRESS=$IP_ADDRESS" > .env
    echo -e "${GREEN}.env file updated with IP_ADDRESS=$IP_ADDRESS${NC}"
    
    # === Docker konteynerlerini başlat ===
    echo -e "${GREEN}Starting Docker containers...${NC}"
    
    # Docker ve docker-compose komutlarının varlığını kontrol et
    if ! command -v docker >/dev/null 2>&1; then
        echo -e "${RED}Error: Docker is not installed or not in PATH${NC}"
        exit 1
    fi
    
    # Docker servisinin çalışıp çalışmadığını kontrol et
    if ! sudo docker info >/dev/null 2>&1; then
        echo -e "${YELLOW}Docker service might not be running. Trying to start...${NC}"
        sudo systemctl start docker 2>/dev/null || true
        sleep 3
    fi
    
    # Docker Compose ile konteynerleri başlat
    if sudo docker compose up -d; then
        echo -e "${GREEN}Docker containers started successfully.${NC}"
    else
        echo -e "${RED}Failed to start Docker containers.${NC}"
        echo -e "${YELLOW}Checking if containers are already running...${NC}"
        sudo docker compose ps
        exit 1
    fi
    
    # === Konteyner durumunu kontrol et ===
    echo -e "${GREEN}Checking container status...${NC}"
    sleep 3
    sudo docker compose ps
    
    # === Kullanışlı bilgiler ===
    echo -e "\n${GREEN}=== Setup Complete ===${NC}"
    echo -e "${GREEN}Application should be accessible at: http://$IP_ADDRESS:3000${NC}"
    echo -e "\n${GREEN}Useful commands:${NC}"
    echo -e " ${GREEN}Stop containers:${NC} sudo docker compose down"
    echo -e " ${GREEN}View logs:${NC} sudo docker compose logs -f"
    echo -e " ${GREEN}Restart containers:${NC} sudo docker compose restart"
    echo -e " ${GREEN}View container status:${NC} sudo docker compose ps"
}

# === Hata yakalama ===
trap 'echo -e "${RED}Script failed at line $LINENO. Exit code: $?${NC}"; exit 1' ERR

# === Scripti çalıştır ===
main "$@"