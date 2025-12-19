# Deployment Scripts

This directory contains scripts for automated deployment of the fotbollsplan-bevattning system.

## Files

### `deploy.sh`

Main deployment script that can be run manually or triggered by GitHub Actions.

**Features:**
- Pulls latest code from git repository
- Activates Python virtual environment
- Installs/updates dependencies
- Restarts systemd services
- Provides colored output and status reporting

**Usage:**
```bash
cd /home/pi/fotbollsplan-bevattning
./scripts/deploy.sh
```

**Environment Variables:**
- `PROJECT_DIR` - Project directory path (default: `/home/pi/fotbollsplan-bevattning`)

**Requirements:**
- Git repository must be configured
- Virtual environment must exist (`.venv`)
- User must have sudo privileges for systemctl commands

### `post-receive.sample`

Git post-receive hook template for automatic deployment on git push.

**Features:**
- Triggered automatically after `git push` to main branch
- Performs same deployment steps as `deploy.sh`
- Only runs on pushes to `main` branch

**Installation:**
```bash
cd /home/pi/fotbollsplan-bevattning
cp scripts/post-receive.sample .git/hooks/post-receive
chmod +x .git/hooks/post-receive
```

**Usage:**
After installation, deployment happens automatically when pushing to main:
```bash
git push origin main
```

**Note:** This approach requires the Raspberry Pi to be configured as a git remote.

## GitHub Actions Workflow

The `.github/workflows/deploy.yml` workflow automates deployment using these scripts.

**Workflow Configuration:**
1. Set up GitHub Secrets (RPI_HOST, RPI_USER, RPI_SSH_KEY)
2. Push to main branch
3. GitHub Actions connects via SSH and runs deployment

See README.md section "Automatic System Updates" for full setup instructions.

## Troubleshooting

### Script fails to find project directory
Ensure `PROJECT_DIR` environment variable is set correctly or that the default path exists:
```bash
export PROJECT_DIR=/path/to/fotbollsplan-bevattning
./scripts/deploy.sh
```

### Permission denied errors
Ensure the scripts are executable:
```bash
chmod +x scripts/deploy.sh
chmod +x scripts/post-receive.sample
```

### Service restart failures
Verify that the user has sudo privileges for systemctl commands:
```bash
sudo visudo -f /etc/sudoers.d/bevattning-deploy
```

Add required permissions (see README.md for details).

### Git pull fails
Ensure the repository has proper remote configuration:
```bash
git remote -v
git config --get remote.origin.url
```

## Security Considerations

- Scripts require sudo privileges for specific systemctl commands only
- SSH keys should be protected with proper permissions (600)
- GitHub Secrets are encrypted and never exposed in logs
- Post-receive hook runs with git user's privileges
