# Automated Deployment Setup Guide

This guide walks you through setting up automated deployment for the fotbollsplan-bevattning system using GitHub Actions.

## Overview

When you push changes to the `main` branch, GitHub Actions automatically:
1. Connects to your Raspberry Pi via SSH
2. Pulls the latest code
3. Updates Python dependencies
4. Restarts all services

## Prerequisites

- Raspberry Pi with fotbollsplan-bevattning installed (via `install_complete.py`)
- SSH access to your Raspberry Pi
- GitHub repository with the code
- A computer to run the setup commands (can be your development machine)

## Step-by-Step Setup

### Step 1: Generate SSH Key Pair

On your development machine (not the Raspberry Pi), generate a new SSH key:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/rpi_deploy_key -C "github-actions-deploy"
```

When prompted for a passphrase, **press Enter** (no passphrase needed for automation).

This creates two files:
- `~/.ssh/rpi_deploy_key` (private key - keep this secret!)
- `~/.ssh/rpi_deploy_key.pub` (public key - safe to share)

### Step 2: Install Public Key on Raspberry Pi

Copy the public key to your Raspberry Pi:

```bash
ssh-copy-id -i ~/.ssh/rpi_deploy_key.pub pi@<raspberry-pi-ip>
```

Replace `<raspberry-pi-ip>` with your Raspberry Pi's IP address (e.g., `192.168.1.100`).

**Test the connection:**
```bash
ssh -i ~/.ssh/rpi_deploy_key pi@<raspberry-pi-ip>
```

You should be able to log in without a password. Type `exit` to close the connection.

### Step 3: Configure sudo for Service Restarts

On the Raspberry Pi, allow the `pi` user to restart services without a password:

```bash
sudo visudo -f /etc/sudoers.d/bevattning-deploy
```

Add these lines (use arrow keys to navigate, `i` to insert text):

```
pi ALL=(ALL) NOPASSWD: /bin/systemctl restart bevattning-api
pi ALL=(ALL) NOPASSWD: /bin/systemctl restart display-manager
pi ALL=(ALL) NOPASSWD: /bin/systemctl restart bevattning-scheduler
pi ALL=(ALL) NOPASSWD: /bin/systemctl is-active bevattning-api
pi ALL=(ALL) NOPASSWD: /bin/systemctl is-active display-manager
pi ALL=(ALL) NOPASSWD: /bin/systemctl is-active bevattning-scheduler
```

Save and exit (press `Esc`, type `:wq`, press `Enter`).

**Test sudo configuration:**
```bash
sudo systemctl restart bevattning-api
```

This should work without asking for a password.

### Step 4: Add GitHub Secrets

1. Go to your GitHub repository in a web browser
2. Click **Settings** (top menu)
3. In the left sidebar, click **Secrets and variables** → **Actions**
4. Click **New repository secret**

Create these three secrets:

#### Secret 1: RPI_HOST
- **Name:** `RPI_HOST`
- **Value:** Your Raspberry Pi's IP address (e.g., `192.168.1.100`) or hostname (e.g., `bevattning.local`)

#### Secret 2: RPI_USER
- **Name:** `RPI_USER`
- **Value:** `pi` (or your Raspberry Pi username)

#### Secret 3: RPI_SSH_KEY
- **Name:** `RPI_SSH_KEY`
- **Value:** The **entire contents** of your private key file

To get the private key content, on your development machine run:
```bash
cat ~/.ssh/rpi_deploy_key
```

Copy the **entire output**, including:
```
-----BEGIN OPENSSH PRIVATE KEY-----
... (many lines of text) ...
-----END OPENSSH PRIVATE KEY-----
```

Paste this entire block into the secret value.

**Important:** Make sure you copy the **private key** (`rpi_deploy_key`), not the public key (`rpi_deploy_key.pub`).

### Step 5: Verify Setup

The GitHub Actions workflow is already configured in `.github/workflows/deploy.yml`.

To test it:

1. Make a small change to your code (e.g., add a comment)
2. Commit and push to the `main` branch:
   ```bash
   git add .
   git commit -m "Test automated deployment"
   git push origin main
   ```
3. Go to your GitHub repository → **Actions** tab
4. You should see a workflow run in progress
5. Click on it to view the deployment logs

If everything is configured correctly, you'll see:
- SSH connection successful
- Code pulled from git
- Dependencies installed
- Services restarted
- ✓ Deployment completed successfully!

## Troubleshooting

### "Permission denied (publickey)"
- Check that you copied the public key to the right Raspberry Pi
- Verify the RPI_HOST secret matches your Raspberry Pi's IP/hostname
- Test SSH connection manually: `ssh -i ~/.ssh/rpi_deploy_key pi@<rpi-ip>`

### "sudo: a password is required"
- Check that sudoers file is configured correctly
- Verify you're using the `pi` user (or update sudoers for your username)
- Test manually on Raspberry Pi: `sudo systemctl restart bevattning-api`

### "Project directory not found"
- The workflow expects the code at `/home/pi/fotbollsplan-bevattning`
- If your path is different, edit `.github/workflows/deploy.yml` and update the path

### Services not restarting
- Check that services are installed: `systemctl list-unit-files | grep bevattning`
- Check service status: `systemctl status bevattning-api`
- View service logs: `journalctl -u bevattning-api -n 50`

### Workflow fails with "Host key verification failed"
This should not happen with the current workflow, but if it does:
- Add your Raspberry Pi's SSH host key to GitHub's known hosts
- Or verify the `ssh-keyscan` command is running in the workflow

## Manual Deployment

If you need to deploy manually without GitHub Actions:

```bash
ssh pi@<raspberry-pi-ip>
cd /home/pi/fotbollsplan-bevattning
./scripts/deploy.sh
```

## Security Notes

- The private SSH key is stored securely in GitHub Secrets (encrypted)
- Never commit the private key to your repository
- The sudoers configuration only allows specific systemctl commands
- SSH key has no passphrase - keep your GitHub account secure with 2FA
- For production, consider using a dedicated deployment user instead of `pi`

## Alternative: Git Post-Receive Hook

If you prefer to deploy directly from the Raspberry Pi instead of using GitHub Actions:

```bash
cd /home/pi/fotbollsplan-bevattning
cp scripts/post-receive.sample .git/hooks/post-receive
chmod +x .git/hooks/post-receive
```

Then deployment happens automatically when you push:
```bash
git push origin main
```

**Note:** This requires git repository configuration on the Raspberry Pi itself.

## Need Help?

- Check GitHub Actions logs for detailed error messages
- See main README.md section "Automatic System Updates"
- See scripts/README.md for deployment script documentation
- Open an issue on GitHub if you need assistance
