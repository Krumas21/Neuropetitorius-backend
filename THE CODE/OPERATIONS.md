# Neuropetitorius Operations Guide

## Deployment

### Initial Server Setup

```bash
# Connect to Hetzner server
ssh root@your-server-ip

# Create deploy user
adduser deploy
usermod -aG sudo deploy

# Generate SSH key for deploy user
ssh-keygen -t ed25519 -C "deploy@neuropetitorius.eu"
# Copy public key to server

# Disable root login
nano /etc/ssh/sshd_config
# Set: PermitRootLogin no
# Set: PasswordAuthentication no

# Reload SSH
systemctl reload ssh

# Configure firewall
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw enable

# Install Docker
curl -fsSL https://get.docker.com | sh
usermod -aG docker deploy

# Configure swap (2GB)
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
# Add to /etc/fstab: /swapfile none swap sw 0 0

# Set timezone
timedatectl set-timezone UTC
# Install NTP
apt install -y chrony
systemctl enable chrony
```

### First Deployment

```bash
# SSH as deploy user
ssh deploy@your-server-ip

# Clone repository
git clone your-repo.git ~/neuropetitorius.eu
cd ~/neuropetitorius.eu

# Create production .env file
cp .env.example .env
nano .env  # Fill in all required values

# Start services
docker compose up -d

# Check status
docker compose ps
docker compose logs -f api
```

### Deployment Script Usage

```bash
# Deploy new version
./deploy.sh

# Deploy specific version
./deploy.sh v0.1.3

# Rollback to previous version
./deploy.sh --rollback
```

## Monitoring

### Health Check

```bash
curl https://api.neuropetitorius.eu/v1/health
```

### Logs

```bash
# API logs
docker compose logs -f api

# Caddy logs
docker compose logs -f caddy

# Database logs
docker compose logs -f postgres
```

### Metrics

```bash
# Get metrics (requires admin key)
curl -H "X-Admin-Key: your-admin-key" \
  https://api.neuropetitorius.eu/v1/admin/metrics
```

## Database

### Backup

```bash
# Manual backup
docker compose exec postgres pg_dump -U neuro neuro > backup_$(date +%Y%m%d).sql

# Restore
docker compose exec -T postgres psql -U neuro neuro < backup_20240101.sql
```

### Migrations

```bash
# Run migrations
docker compose exec api alembic upgrade head

# Rollback
docker compose exec api alembic downgrade -1
```

## Key Rotation

### API Keys

1. Generate new key: `python -c "import secrets; print('npk_' + secrets.token_urlsafe(32))"`
2. Update in database via admin API
3. Update partner credentials

### Database Password

1. Update `.env` with new password
2. Restart: `docker compose restart api`

### Gemini API Key

1. Update `.env` with new key
2. Restart: `docker compose restart api`

## Troubleshooting

### Service Down

```bash
# Check all containers
docker compose ps

# Check logs
docker compose logs --tail=100

# Restart service
docker compose restart api
```

### Database Connection Issues

```bash
# Check PostgreSQL
docker compose exec postgres pg_isready

# Check connections
docker compose exec postgres psql -U neuro -c "SELECT count(*) FROM pg_stat_activity;"
```

### Rate Limiting Issues

```bash
# Check Redis
docker compose exec redis redis-cli ping

# Check rate limit keys
docker compose exec redis redis-cli keys "limiter:*"
```

## Alerts

- **UptimeRobot**: Monitors `/v1/health` every 5 minutes
- **Sentry**: Error tracking at https://sentry.io

## Maintenance Window

1. Notify partners 24h in advance
2. Stop accepting new requests
3. Wait for active requests to complete
4. Backup database
5. Run migrations
6. Deploy new version
7. Verify health
8. Resume traffic