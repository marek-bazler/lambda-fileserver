# Local Development Setup

## Quick Start

```bash
# Option 1: Using Make (recommended)
make local-setup    # Creates virtual environment
make local-start    # Starts everything

# Option 2: Manual setup
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r local/requirements.txt
docker-compose up -d
./local/setup_local.sh
python local/run_local.py
```

## Troubleshooting

### Docker Permission Denied
If you see "permission denied while trying to connect to the docker API":

```bash
# Option 1: Add your user to docker group (recommended)
sudo usermod -aG docker $USER
newgrp docker  # Or logout/login

# Option 2: Use sudo
sudo docker-compose up -d
sudo ./local/setup_local.sh
```

### Dependency Conflicts
If you see boto3/botocore version conflicts:
- The virtual environment (.venv) isolates dependencies
- Don't use your conda base environment
- Run `make clean` then `make local-setup` to start fresh

### LocalStack Not Starting
```bash
# Check Docker is running
systemctl status docker

# Check LocalStack logs
docker-compose logs localstack

# Restart everything
docker-compose down -v
docker-compose up -d
```

### Port Already in Use
- LocalStack: 4566
- API Server: 5000
- Web UI: 8080

Check with: `lsof -i :5000` or `netstat -an | grep 5000`

### AWS CLI Not Found
```bash
# Install AWS CLI
pip install awscli
# Or: sudo apt install awscli
```
