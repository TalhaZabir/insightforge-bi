# Deploying InsightForge BI to Oracle Cloud Always Free VM

This guide provides a step-by-step walkthrough to deploy the **InsightForge BI & Analytics Platform** to an **Oracle Cloud Infrastructure (OCI) Always Free VM** using Docker and an automated production Nginx reverse proxy.

---

## Architecture Overview

```
                          Internet / Users
                                 │
                                 ▼
                     Oracle Cloud VCN Firewall
                   (Security List: Port 80, 443)
                                 │
                                 ▼
                 Host OS Firewall (iptables / ufw)
                                 │
                                 ▼
                   ┌───────────────────────────┐
                   │       Nginx Container     │
                   │        (Ports 80/443)     │
                   └─────────────┬─────────────┘
                                 │
            ┌────────────────────┴────────────────────┐
            ▼                                         ▼
   /api/*, /docs, /health/*                           /*
┌───────────────────────────────┐         ┌──────────────────────────────┐
│       FastAPI Backend         │         │      Next.js Frontend        │
│   (Port 8000 - Internal)      │         │    (Port 3000 - Internal)    │
└───────────────┬───────────────┘         └──────────────────────────────┘
                │
                ▼
┌───────────────────────────────┐
│     PostgreSQL Database       │
│   (Port 5432 - Internal)      │
│  [Persistent Volume: pgdata]  │
└───────────────────────────────┘
```

- **Security First**: PostgreSQL (5432), FastAPI (8000), and Next.js (3000) are **never exposed to the public internet**.
- **Unified Origin**: Nginx serves the frontend on `/` and routes `/api/*` to the backend. This eliminates CORS issues and lets you access the entire platform on standard port 80 (or 443 with SSL).
- **100% Always Free**: Runs comfortably within Oracle Cloud's free tier.

---

## Step 1: Create the Always Free Compute Instance in OCI

1. Log into your **[Oracle Cloud Infrastructure Console](https://cloud.oracle.com/)**.
2. Open the navigation menu (top-left burger icon) and go to **Compute** → **Instances**.
3. Click the blue **Create Instance** button.
4. Configure the instance settings:
   - **Name**: `insightforge-bi` (or any name you prefer).
   - **Placement**: Keep default Availability Domain (ensure it shows *"Always Free Eligible"*).
   - **Image and Shape**:
     - Click **Change Shape**.
     - Choose **Ampere** (Arm processor) → select **`VM.Standard.A1.Flex`**.
     - Allocate **2 to 4 OCPUs** and **12 to 24 GB RAM** (Oracle provides up to 4 OCPUs and 24 GB RAM free forever).
     - *Alternative (if Ampere is out of capacity in your region)*: Select **Specialty and legacy** → **`VM.Standard.E2.1.Micro`** (AMD 1 OCPU, 1 GB RAM — our automated script will configure a 4 GB swapfile to ensure stability).
     - **Image**: Select **Canonical Ubuntu 22.04** or **24.04** (Recommended) or **Oracle Linux 9**.
   - **Networking**:
     - Select **Create new virtual cloud network** (or choose your existing VCN).
     - Make sure **Assign a public IPv4 address** is checked (**Yes**).
   - **Add SSH keys**:
     - Select **Generate a key pair for me**.
     - Click **Save private key** to download the `.key` file (e.g. `ssh-key.key`). Save this file on your local machine (e.g. in `C:\Users\<your-user>\.ssh\oci-key.key`).
     - *(Optional)* Click **Save public key** as well.
   - **Boot volume**:
     - Keep default (47 GB) or check *Use in-transit encryption* and set up to 200 GB (Always Free includes 200 GB free block storage).
5. Click **Create** at the bottom.
6. The instance status will show **PROVISIONING** (orange), then change to **RUNNING** (green) within 1–2 minutes.
7. Copy the **Public IP Address** displayed on the instance details page (e.g., `129.146.xxx.xxx`).

---

## Step 2: Open Ingress Ports in the OCI Virtual Cloud Network (VCN)

> [!IMPORTANT]
> Oracle Cloud blocks all incoming traffic except SSH (Port 22) by default. You **MUST** open Port 80 and Port 443 in the OCI Security List, otherwise you will not be able to access the web application from your browser.

1. On your instance details page in OCI Console, scroll down to the **Primary VNIC** section.
2. Click on the link under **Subnet** (e.g., `Public Subnet-XXXX`).
3. Click on **Default Security List for XXXX**.
4. Under the **Ingress Rules** tab, click **Add Ingress Rules**.
5. Fill in:
   - **Stateless**: Leave unchecked.
   - **Source Type**: `CIDR`
   - **Source CIDR**: `0.0.0.0/0` (allows public internet access)
   - **IP Protocol**: `TCP`
   - **Source Port Range**: Leave blank (All)
   - **Destination Port Range**: `80,443`
   - **Description**: `InsightForge HTTP and HTTPS`
6. Click **Add Ingress Rules**.

---

## Step 3: Connect to the VM via SSH from Windows

1. Open **PowerShell** on your local machine.
2. Fix private key file permissions (Windows OpenSSH requires strict permissions):
   ```powershell
   icacls "C:\Users\<YourUser>\Downloads\ssh-key.key" /inheritance:r
   icacls "C:\Users\<YourUser>\Downloads\ssh-key.key" /grant:r "$($env:USERNAME):(R)"
   ```
3. Connect to the instance:
   ```powershell
   # If you selected Ubuntu:
   ssh -i "C:\Users\<YourUser>\Downloads\ssh-key.key" ubuntu@<YOUR_VM_PUBLIC_IP>

   # If you selected Oracle Linux:
   ssh -i "C:\Users\<YourUser>\Downloads\ssh-key.key" opc@<YOUR_VM_PUBLIC_IP>
   ```
4. Type `yes` when prompted to verify the host key fingerprint. You are now logged into your Oracle Cloud VM!

---

## Step 4: Transfer the Code to the VM

Choose either **Method A (Git)** or **Method B (Direct SCP Copy)**:

### Method A: Via Git (Recommended if pushed to GitHub/GitLab)
On the Oracle VM terminal:
```bash
git clone <YOUR_REPOSITORY_URL> insightforge
cd insightforge
```

### Method B: Via SCP from Local Windows Machine
In your local Windows PowerShell terminal:
```powershell
# In the directory containing the project:
scp -i "C:\Users\<YourUser>\Downloads\ssh-key.key" -r "f:\End-to-End Business Intelligence & Analytics Platform" ubuntu@<YOUR_VM_PUBLIC_IP>:~/insightforge
```
Then on the VM:
```bash
cd ~/insightforge
```

---

## Step 5: Run the Automated Deployment Script

Once inside the `insightforge` folder on your VM, execute the automated setup script with `sudo`:

```bash
sudo bash scripts/setup-oracle-vm.sh
```

### What this script handles automatically:
1. **Installs Docker & Docker Compose** (official Docker repositories for Ubuntu or Oracle Linux).
2. **Configures 4 GB Swap**: Prevents memory spikes from crashing builds.
3. **Solves the Oracle Cloud OS Firewall Trap**: Automatically inserts `iptables` and `ufw`/`firewalld` rules for TCP ports 80, 443, and 22, persisting them across reboots.
4. **Generates Production Secrets**: Creates `.env` with cryptographically random `JWT_SECRET` and `POSTGRES_PASSWORD`.
5. **Configures Nginx Reverse Proxy**: Binds `NEXT_PUBLIC_API_URL=/api`.
6. **Launches Docker Stack**: Runs database migrations, populates demo accounts and calendar seeds, and verifies health checks.

---

## Step 6: Verify and Access Your Deployment

Once the script completes, open your web browser and navigate to:

- **Web Dashboard**: `http://<YOUR_VM_PUBLIC_IP>`
- **Interactive API Docs (Swagger)**: `http://<YOUR_VM_PUBLIC_IP>/docs`
- **Health Check**: `http://<YOUR_VM_PUBLIC_IP>/health/readiness`

### Default Demo Credentials:
| Role | Email | Password |
|---|---|---|
| **Admin** | `admin@insightforge.io` | `Admin123!` |
| **Analyst** | `analyst@insightforge.io` | `Analyst123!` |
| **Viewer** | `viewer@insightforge.io` | `Viewer123!` |

---

## Step 7: (Optional) Adding a Custom Domain & Free SSL (HTTPS)

If you have a domain name (e.g., `bi.yourdomain.com`):

1. **Set up DNS**: Add an **A Record** in your DNS registrar pointing to `<YOUR_VM_PUBLIC_IP>`.
2. **Obtain SSL Certificate with Certbot**:
   On your Oracle VM:
   ```bash
   sudo docker compose -f docker-compose.prod.yml run --rm certbot certonly \
     --webroot --webroot-path=/var/www/certbot \
     -d bi.yourdomain.com --email your-email@example.com --agree-tos --no-eff-email
   ```
3. Update `nginx/nginx.conf` with your SSL certificates and reload Nginx:
   ```bash
   sudo docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
   ```

---

## Day-to-Day Operations & Maintenance

| Action | Command |
|---|---|
| View real-time container logs | `sudo docker compose -f docker-compose.prod.yml logs -f` |
| View backend logs only | `sudo docker compose -f docker-compose.prod.yml logs -f backend` |
| View Nginx access/error logs | `sudo docker compose -f docker-compose.prod.yml logs -f nginx` |
| Restart all services | `sudo docker compose -f docker-compose.prod.yml restart` |
| Stop all services | `sudo docker compose -f docker-compose.prod.yml down` |
| Update code & rebuild | `git pull && sudo docker compose -f docker-compose.prod.yml up -d --build` |
| Backup database to SQL file | `sudo docker compose -f docker-compose.prod.yml exec postgres pg_dump -U insightforge insightforge > backup_$(date +%F).sql` |
| Restore database | `cat backup.sql \| sudo docker compose -f docker-compose.prod.yml exec -T postgres psql -U insightforge -d insightforge` |

---

## Troubleshooting Oracle Cloud Deployments

### 1. Connection Refused / Timeout on Port 80 in Browser
- **Check OCI VCN Ingress Rules**: Ensure Port 80 is added in the Default Security List for `0.0.0.0/0`.
- **Check Host Firewall**: Run `sudo bash scripts/oracle-firewall.sh` on the VM. Oracle Cloud's default Ubuntu images block all ports except 22 via raw `iptables` rules.
- **Check Docker Status**: Run `sudo docker compose -f docker-compose.prod.yml ps` to confirm all 4 containers (`nginx`, `frontend`, `backend`, `postgres`) are `Up`.

### 2. Frontend shows "Network Error" or cannot connect to API
- In production, all API calls go to `/api/*` on the same host through Nginx.
- Check backend logs: `sudo docker compose -f docker-compose.prod.yml logs backend`.
- Check if readiness endpoint is returning `{"status":"ok"}`:
  ```bash
  curl http://localhost/health/readiness
  ```

### 3. Out of Memory (OOM) during `docker compose build`
- Ensure swap is active: run `free -h` and verify that `Swap` shows at least 4.0G.
- If swap is missing, run:
  ```bash
  sudo fallocate -l 4G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
  ```
