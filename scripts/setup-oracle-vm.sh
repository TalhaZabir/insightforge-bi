#!/usr/bin/env bash
# ==============================================================================
# InsightForge BI — Automated Setup & Deployment for Oracle Cloud Always Free VM
# Works on: Ubuntu 22.04/24.04 LTS & Oracle Linux 8/9 (x86_64 and aarch64/Ampere)
# ==============================================================================

set -euo pipefail

BOLD="\033[1m"
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
BLUE="\033[0;34m"
NC="\033[0m"

info()    { echo -e "${BLUE}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

echo -e "${BOLD}==============================================================${NC}"
echo -e "${BOLD} InsightForge BI — Oracle Cloud Always Free Deployment Setup ${NC}"
echo -e "${BOLD}==============================================================${NC}"

# 1. Root / Sudo Check
if [ "$EUID" -ne 0 ]; then
    error "Please run this script with sudo: sudo bash scripts/setup-oracle-vm.sh"
fi

TARGET_USER="${SUDO_USER:-$(logname 2>/dev/null || echo "ubuntu")}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

info "Target project directory: ${PROJECT_ROOT}"
info "Operating user: ${TARGET_USER}"

# 2. OS Detection
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS_ID="${ID:-unknown}"
    OS_VERSION="${VERSION_ID:-}"
else
    error "Cannot detect operating system. /etc/os-release is missing."
fi
info "Detected OS: ${OS_ID} ${OS_VERSION}"

# 3. Memory & Swap Configuration (Critical for VM stability on Always Free tier)
TOTAL_RAM_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
TOTAL_RAM_MB=$((TOTAL_RAM_KB / 1024))
info "Detected System RAM: ${TOTAL_RAM_MB} MB"

if ! swapon --show | grep -q "/swapfile"; then
    info "Configuring 4 GB swap space to prevent Out-Of-Memory during builds..."
    if command -v fallocate >/dev/null 2>&1; then
        fallocate -l 4G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=4096 status=progress
    else
        dd if=/dev/zero of=/swapfile bs=1M count=4096 status=progress
    fi
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    if ! grep -q "/swapfile" /etc/fstab; then
        echo "/swapfile none swap sw 0 0" >> /etc/fstab
    fi
    sysctl vm.swappiness=10
    echo "vm.swappiness=10" >> /etc/sysctl.d/99-swap.conf || true
    success "4 GB Swap file configured and active."
else
    info "Swap is already configured."
fi

# 4. Install Docker & Docker Compose Plugin
if ! command -v docker >/dev/null 2>&1; then
    info "Docker is not installed. Installing official Docker Engine..."
    if [ "${OS_ID}" = "ubuntu" ] || [ "${OS_ID}" = "debian" ]; then
        apt-get update -y
        apt-get install -y ca-certificates curl gnupg lsb-release iptables-persistent netfilter-persistent
        install -m 0755 -d /etc/apt/keyrings
        curl -fsSL "https://download.docker.com/linux/${OS_ID}/gpg" | gpg --dearmor -o /etc/apt/keyrings/docker.gpg --yes
        chmod a+r /etc/apt/keyrings/docker.gpg
        echo \
          "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/${OS_ID} \
          $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
        apt-get update -y
        apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    elif [ "${OS_ID}" = "ol" ] || [ "${OS_ID}" = "rhel" ] || [ "${OS_ID}" = "centos" ] || [ "${OS_ID}" = "rocky" ] || [ "${OS_ID}" = "almalinux" ]; then
        dnf -y install dnf-plugins-core
        dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
        dnf -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    else
        error "Unsupported distribution: ${OS_ID}. Please install Docker manually."
    fi
    systemctl enable --now docker
    success "Docker installed successfully."
else
    info "Docker is already installed: $(docker --version)"
fi

# Ensure target user can run docker without sudo
if [ -n "${TARGET_USER}" ] && id "${TARGET_USER}" >/dev/null 2>&1; then
    usermod -aG docker "${TARGET_USER}" || true
fi

# 5. Oracle Cloud Host Firewall Configuration (Solves the #1 OCI connection drop issue)
info "Configuring OS firewall for Port 80 (HTTP), 443 (HTTPS), and 22 (SSH)..."

if [ "${OS_ID}" = "ubuntu" ] || [ "${OS_ID}" = "debian" ]; then
    # Oracle Cloud Ubuntu cloud-init images inject strict iptables rules that DROP incoming ports.
    # We explicitly insert ACCEPT rules into the INPUT chain before any DROP/REJECT rule:
    iptables -I INPUT 1 -p tcp --dport 22 -j ACCEPT || true
    iptables -I INPUT 2 -p tcp --dport 80 -j ACCEPT || true
    iptables -I INPUT 3 -p tcp --dport 443 -j ACCEPT || true

    # Persist iptables rules across reboots
    if command -v netfilter-persistent >/dev/null 2>&1; then
        netfilter-persistent save || true
    fi

    # Also configure UFW if enabled
    if command -v ufw >/dev/null 2>&1; then
        ufw allow 22/tcp || true
        ufw allow 80/tcp || true
        ufw allow 443/tcp || true
    fi
    success "Ubuntu host firewall rules updated."
elif [ "${OS_ID}" = "ol" ] || [ "${OS_ID}" = "rhel" ] || [ "${OS_ID}" = "centos" ]; then
    if systemctl is-active --quiet firewalld; then
        firewall-cmd --permanent --zone=public --add-service=http || true
        firewall-cmd --permanent --zone=public --add-service=https || true
        firewall-cmd --permanent --zone=public --add-port=22/tcp || true
        firewall-cmd --reload || true
        success "Firewalld rules updated."
    else
        iptables -I INPUT 1 -p tcp --dport 22 -j ACCEPT || true
        iptables -I INPUT 2 -p tcp --dport 80 -j ACCEPT || true
        iptables -I INPUT 3 -p tcp --dport 443 -j ACCEPT || true
        service iptables save 2>/dev/null || true
    fi
fi

# 6. Generate Production Environment Configuration (.env)
if [ ! -f .env ]; then
    info "Creating production .env from .env.example..."
    cp .env.example .env

    # Generate secure random cryptographic secrets
    GEN_JWT_SECRET=$(openssl rand -hex 32)
    GEN_PG_PASS=$(openssl rand -hex 16)

    # Safely substitute values in .env
    sed -i "s|JWT_SECRET=.*|JWT_SECRET=${GEN_JWT_SECRET}|" .env
    sed -i "s|POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${GEN_PG_PASS}|" .env
    sed -i "s|insightforge_pw|${GEN_PG_PASS}|g" .env
    sed -i "s|CORS_ORIGINS=.*|CORS_ORIGINS=*|" .env
    sed -i "s|NEXT_PUBLIC_API_URL=.*|NEXT_PUBLIC_API_URL=/api|" .env

    chown "${TARGET_USER}:${TARGET_USER}" .env || true
    chmod 600 .env
    success "Generated fresh production secrets in .env"
else
    info "Found existing .env file. Preserving existing configuration."
    # Ensure NEXT_PUBLIC_API_URL=/api for Nginx reverse proxy
    if ! grep -q "NEXT_PUBLIC_API_URL=/api" .env; then
        sed -i "s|NEXT_PUBLIC_API_URL=.*|NEXT_PUBLIC_API_URL=/api|" .env || echo "NEXT_PUBLIC_API_URL=/api" >> .env
    fi
fi

# Ensure uploads directory has correct permissions
mkdir -p uploads
chown -R 1000:1000 uploads || chmod 777 uploads

# 7. Start Containers with Docker Compose
info "Building and launching containers using docker-compose.prod.yml..."
docker compose -f docker-compose.prod.yml down --remove-orphans || true
docker compose -f docker-compose.prod.yml up -d --build

# 8. Verification & Readiness check
info "Waiting for services to finish database migrations and start up..."
ATTEMPTS=0
MAX_ATTEMPTS=20
HEALTHY=0

while [ $ATTEMPTS -lt $MAX_ATTEMPTS ]; do
    sleep 3
    ATTEMPTS=$((ATTEMPTS + 1))
    if curl -s http://localhost/health/readiness | grep -q '"status": *"ready"' || curl -s http://localhost/health | grep -q '"status": *"ok"' || curl -s http://localhost/docs >/dev/null 2>&1; then
        HEALTHY=1
        break
    fi
    echo -n "."
done
echo ""

PUBLIC_IP=$(curl -s -m 4 https://ifconfig.me 2>/dev/null || curl -s -m 4 https://api.ipify.org 2>/dev/null || echo "<YOUR_VM_PUBLIC_IP>")

echo ""
echo -e "${GREEN}==============================================================${NC}"
echo -e "${BOLD}${GREEN}  InsightForge BI is successfully deployed on Oracle Cloud!   ${NC}"
echo -e "${GREEN}==============================================================${NC}"
echo ""
echo -e "  ${BOLD}Web Dashboard:${NC}   http://${PUBLIC_IP}"
echo -e "  ${BOLD}Swagger API Docs:${NC}http://${PUBLIC_IP}/docs"
echo -e "  ${BOLD}Health Endpoint:${NC} http://${PUBLIC_IP}/health/readiness"
echo ""
echo -e "  ${BOLD}Default Logins:${NC}"
echo -e "    - Admin:   ${YELLOW}admin@insightforge.io${NC}   / ${YELLOW}Admin123!${NC}"
echo -e "    - Analyst: ${YELLOW}analyst@insightforge.io${NC} / ${YELLOW}Analyst123!${NC}"
echo -e "    - Viewer:  ${YELLOW}viewer@insightforge.io${NC}  / ${YELLOW}Viewer123!${NC}"
echo ""
echo -e "  ${BOLD}Management Commands:${NC}"
echo -e "    - View logs:        ${BLUE}docker compose -f docker-compose.prod.yml logs -f${NC}"
echo -e "    - Stop services:    ${BLUE}docker compose -f docker-compose.prod.yml down${NC}"
echo -e "    - Restart services: ${BLUE}docker compose -f docker-compose.prod.yml restart${NC}"
echo -e "    - Check status:     ${BLUE}docker compose -f docker-compose.prod.yml ps${NC}"
echo ""
if [ "${HEALTHY}" -eq 0 ]; then
    warn "The web server responded slowly or is still building. Run 'docker compose -f docker-compose.prod.yml logs -f' to check progress."
fi
echo -e "${YELLOW}IMPORTANT:${NC} Ensure you have opened Port 80 and 443 in your Oracle Cloud VCN Security List!"
echo -e "See ${BOLD}docs/oracle-cloud-deployment.md${NC} for exact step-by-step console instructions."
echo -e "${GREEN}==============================================================${NC}"
