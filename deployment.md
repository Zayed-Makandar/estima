# Deployment Guide for Estima (AlmaLinux)

This guide provides the exact commands to set up the environment on your AlmaLinux server.
The issue you faced (`anyio==4.12.0` not found) is because your local machine uses a newer Python version (likely 3.10+), while the server is running Python 3.8. Many modern libraries (including `anyio` 4.6+) have dropped support for Python 3.8.

To fix this, we will install **Python 3.11** on the server.

## 1. Install Python 3.11
Run the following commands on your server:

```bash
# Update system packages
sudo dnf update -y

# Install Python 3.11
sudo dnf install python3.11 python3.11-pip python3.11-devel -y

# Verify installation
python3.11 --version
```

## 2. Set Up Virtual Environment

Navigate to your project directory (`/home/kumar/estima` or similar) and recreate the virtual environment using Python 3.11.

```bash
# Go to project directory
cd ~/estima

# Remove the old Python 3.8 venv (optional but recommended)
rm -rf .venv

# Create a new venv with Python 3.11
python3.11 -m venv .venv

# Activate the venv
source .venv/bin/activate

# Upgrade pip (Good practice)
pip install --upgrade pip
```

## 3. Install Dependencies
Now that you are running Python 3.11, the packages from your specific `requirements1.txt` (including `anyio==4.12.0`) should install correctly.

```bash
# Install the requirements
pip install -r requirements1.txt
```

## 4. Install Playwright Browsers
Since your app uses Playwright, you need to install the browser binaries.

```bash
playwright install chromium
playwright install-deps chromium
```

## 5. Run the Application
You can now run the application using `uvicorn` (or `gunicorn` for production).

```bash
# Example run command
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

---

## 6. Build the Frontend (Vite)
On your local machine, you have `node_modules`. On the server, you need to install Node.js and build the production assets.

```bash
# 1. Install Node.js (Version 18 or 20 recommended)
sudo dnf module enable nodejs:20 -y
sudo dnf install nodejs -y

# 2. Go to frontend directory
cd ~/estima/frontend

# 3. Install dependencies
npm install

# 4. Build for production
# This creates a 'dist' folder
npm run build
```

## 7. Setup Environment Variables
Create a `.env` file in the `backend` folder.

```bash
cd ~/estima/backend
nano .env
```
Paste your production settings (Database URL, Secret Keys, etc.) inside.

## 8. Serve with Nginx (Production)
Instead of running `npm run dev`, we serve the `dist` folder via Nginx and proxy API requests to the Python backend.

```bash
# Install Nginx
sudo dnf install nginx -y
sudo systemctl enable --now nginx

# Configure Nginx
sudo nano /etc/nginx/conf.d/estima.conf
```

**Template for `estima.conf`:**
```nginx
server {
    listen 80;
    server_name your_domain_or_ip;

    # Frontend Static Files
    location / {
        root /home/kumar/estima/frontend/dist;
        index index.html;
        try_files $uri /index.html;
    }

    # Backend API Proxy
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 9. Run Backend as a Service (Systemd)
To keep the backend running after you close the terminal:

```bash
sudo nano /etc/systemd/system/estima-backend.service
```

Paste this:
```ini
[Unit]
Description=Estima Backend
After=network.target

[Service]
User=kumar
WorkingDirectory=/home/kumar/estima
ExecStart=/home/kumar/estima/.venv/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now estima-backend
sudo systemctl restart nginx
```
