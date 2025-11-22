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

### Dependency Conflicts
If you see boto3/botocore version conflicts:
- The virtual environment (.venv) isolates dependencies
- Don't use your conda base environment
- Run `make clean` then `make local-setup` to start fresh

### Port Already in Use
- LocalStack: 4566
- API Server: 5000
- Web UI: 8080

Check with: `lsof -i :5000` or `netstat -an | grep 5000`

### Docker Issues
```bash
docker-compose down -v  # Stop and remove volumes
docker-compose up -d    # Start fresh
```
