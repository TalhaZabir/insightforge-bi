#!/usr/bin/env bash
# ==============================================================================
# Helper: Fix Oracle Cloud OS-Level Firewall Rules (Port 80, 443, 22)
# ==============================================================================

set -euo pipefail

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root: sudo bash scripts/oracle-firewall.sh"
    exit 1
fi

echo "Opening TCP ports 22, 80, 443 in OS iptables..."

# Insert at top of INPUT chain
iptables -I INPUT 1 -p tcp --dport 22 -j ACCEPT || true
iptables -I INPUT 2 -p tcp --dport 80 -j ACCEPT || true
iptables -I INPUT 3 -p tcp --dport 443 -j ACCEPT || true

if command -v netfilter-persistent >/dev/null 2>&1; then
    netfilter-persistent save || true
fi

if command -v ufw >/dev/null 2>&1; then
    ufw allow 22/tcp || true
    ufw allow 80/tcp || true
    ufw allow 443/tcp || true
fi

if command -v firewall-cmd >/dev/null 2>&1 && systemctl is-active --quiet firewalld; then
    firewall-cmd --permanent --zone=public --add-service=http || true
    firewall-cmd --permanent --zone=public --add-service=https || true
    firewall-cmd --permanent --zone=public --add-port=22/tcp || true
    firewall-cmd --reload || true
fi

echo "OS firewall successfully configured!"
