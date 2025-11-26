# Deployment Guide

Production deployment guide for Path Manager.

## Table of Contents

- [Deployment Overview](#deployment-overview)
- [NFS Deployment](#nfs-deployment)
- [CI/CD Integration](#cicd-integration)
- [Platform-Specific Deployment](#platform-specific-deployment)
- [High Availability](#high-availability)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

---

## Deployment Overview

### Architecture

```
┌──────────────┐
│ Git Repo     │  Schema YAML in version control
│ schema.yml   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   CI/CD      │  Compile on commit/merge
│   Pipeline   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Artifact   │  Store compiled schema
│  Repository  │  (Nexus/Artifactory)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│     NFS      │  Deploy to shared storage
│   /shared    │  Read-only, immutable
└──────┬───────┘
       │
       ├────────────┬────────────┬────────────┐
       ▼            ▼            ▼            ▼
   ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐
   │Client 1│  │Client 2│  │Client 3│  │Client N│
   └────────┘  └────────┘  └────────┘  └────────┘
```

### Recommended Setup

1. **Version Control**: Schema YAML in git
2. **Compilation**: Automated via CI/CD
3. **Distribution**: Artifact repository or NFS
4. **Clients**: Read compiled schema from shared location

---

## NFS Deployment

### Prerequisites

- NFS server configured and accessible
- Read/write access for deployment
- Read-only access for clients

### Step 1: Prepare NFS Mount

```bash
# On NFS server
sudo mkdir -p /exports/path-manager
sudo chown deploy:deploy /exports/path-manager

# Add to /etc/exports
echo "/exports/path-manager *(ro,sync,no_subtree_check)" | sudo tee -a /etc/exports
sudo exportfs -a

# On client machines
sudo mkdir -p /mnt/path-manager
echo "nfs-server:/exports/path-manager /mnt/path-manager nfs ro,hard,intr 0 0" | \
    sudo tee -a /etc/fstab
sudo mount -a
```

### Step 2: Deploy Schema

```bash
# Compile schema
python -m path_manager.compiler \
    schema_linux.yml \
    /tmp/schema.db \
    --format sqlite

# Verify compilation
ls -lh /tmp/schema.db

# Deploy to NFS with versioning
VERSION=$(date +%Y%m%d_%H%M%S)
DEPLOY_PATH="/exports/path-manager/schemas"

# Create versioned copy
cp /tmp/schema.db ${DEPLOY_PATH}/schema_${VERSION}.db

# Update symlink atomically
ln -sf schema_${VERSION}.db ${DEPLOY_PATH}/schema_latest.db

# Set read-only permissions
chmod 444 ${DEPLOY_PATH}/schema_${VERSION}.db
```

### Step 3: Client Configuration

```python
# In application config
from pathlib import Path
from path_manager.resolver import PathResolver

# Use latest version via symlink
SCHEMA_PATH = Path('/mnt/path-manager/schemas/schema_latest.db')

# Verify file exists and is readable
if not SCHEMA_PATH.exists():
    raise RuntimeError(f"Schema not found: {SCHEMA_PATH}")

# Create resolver
resolver = PathResolver.from_file(SCHEMA_PATH)
```

### NFS-Safe Features

Path Manager automatically uses NFS-safe features:

1. **SQLite Immutable Mode**: Opens with `immutable=1` flag
2. **Read-Only**: No write operations
3. **No Locking**: Concurrent reads without conflicts
4. **Memory-Mapped I/O**: MsgPack backend uses mmap

```python
# SQLite automatically uses immutable mode
store = SQLiteStore('/mnt/path-manager/schema.db')
# Opens with: file:///mnt/path-manager/schema.db?immutable=1
```

---

## CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/compile-schema.yml
name: Compile Schema

on:
  push:
    branches: [main]
    paths:
      - 'schema*.yml'
  pull_request:
    paths:
      - 'schema*.yml'

jobs:
  compile:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install -e .

      - name: Compile Linux schema
        run: |
          python -m path_manager.compiler \
            examples/schema_linux.yml \
            schema_linux.db \
            --format sqlite

      - name: Compile Windows schema
        run: |
          python -m path_manager.compiler \
            examples/schema_windows.yml \
            schema_windows.db \
            --format sqlite

      - name: Validate schemas
        run: |
          python -m pytest tests/test_compiler_and_stores.py -v

      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: compiled-schemas
          path: |
            schema_linux.db
            schema_windows.db

  deploy:
    needs: compile
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
      - uses: actions/download-artifact@v3
        with:
          name: compiled-schemas

      - name: Deploy to NFS
        run: |
          VERSION=$(date +%Y%m%d_%H%M%S)

          # Copy to NFS
          scp schema_linux.db \
            deploy@nfs-server:/exports/path-manager/schemas/schema_linux_${VERSION}.db

          # Update symlink
          ssh deploy@nfs-server \
            "ln -sf schema_linux_${VERSION}.db \
             /exports/path-manager/schemas/schema_linux_latest.db"

          # Set permissions
          ssh deploy@nfs-server \
            "chmod 444 /exports/path-manager/schemas/schema_linux_${VERSION}.db"
```

### GitLab CI

```yaml
# .gitlab-ci.yml
stages:
  - build
  - test
  - deploy

variables:
  SCHEMA_DIR: "/exports/path-manager/schemas"

compile_schemas:
  stage: build
  image: python:3.10
  script:
    - pip install -e .
    - python -m path_manager.compiler examples/schema_linux.yml schema_linux.db
    - python -m path_manager.compiler examples/schema_windows.yml schema_windows.db
  artifacts:
    paths:
      - schema_linux.db
      - schema_windows.db
    expire_in: 1 week

test_schemas:
  stage: test
  image: python:3.10
  dependencies:
    - compile_schemas
  script:
    - pip install -e ".[dev]"
    - pytest tests/ -v

deploy_production:
  stage: deploy
  only:
    - main
  dependencies:
    - compile_schemas
  script:
    - export VERSION=$(date +%Y%m%d_%H%M%S)

    - |
      # Deploy Linux schema
      scp schema_linux.db deploy@nfs-server:${SCHEMA_DIR}/schema_linux_${VERSION}.db
      ssh deploy@nfs-server "ln -sf schema_linux_${VERSION}.db ${SCHEMA_DIR}/schema_linux_latest.db"
      ssh deploy@nfs-server "chmod 444 ${SCHEMA_DIR}/schema_linux_${VERSION}.db"

    - |
      # Deploy Windows schema
      scp schema_windows.db deploy@nfs-server:${SCHEMA_DIR}/schema_windows_${VERSION}.db
      ssh deploy@nfs-server "ln -sf schema_windows_${VERSION}.db ${SCHEMA_DIR}/schema_windows_latest.db"
      ssh deploy@nfs-server "chmod 444 ${SCHEMA_DIR}/schema_windows_${VERSION}.db"
```

### Jenkins Pipeline

```groovy
// Jenkinsfile
pipeline {
    agent any

    environment {
        SCHEMA_DIR = '/exports/path-manager/schemas'
        VERSION = sh(script: 'date +%Y%m%d_%H%M%S', returnStdout: true).trim()
    }

    stages {
        stage('Setup') {
            steps {
                sh 'pip install -e .'
            }
        }

        stage('Compile') {
            parallel {
                stage('Linux Schema') {
                    steps {
                        sh '''
                            python -m path_manager.compiler \
                                examples/schema_linux.yml \
                                schema_linux.db \
                                --format sqlite
                        '''
                    }
                }
                stage('Windows Schema') {
                    steps {
                        sh '''
                            python -m path_manager.compiler \
                                examples/schema_windows.yml \
                                schema_windows.db \
                                --format sqlite
                        '''
                    }
                }
            }
        }

        stage('Test') {
            steps {
                sh 'pytest tests/ -v --junitxml=test-results.xml'
            }
            post {
                always {
                    junit 'test-results.xml'
                }
            }
        }

        stage('Deploy') {
            when {
                branch 'main'
            }
            steps {
                sh '''
                    # Deploy Linux schema
                    scp schema_linux.db deploy@nfs-server:${SCHEMA_DIR}/schema_linux_${VERSION}.db
                    ssh deploy@nfs-server \
                        "ln -sf schema_linux_${VERSION}.db ${SCHEMA_DIR}/schema_linux_latest.db && \
                         chmod 444 ${SCHEMA_DIR}/schema_linux_${VERSION}.db"

                    # Deploy Windows schema
                    scp schema_windows.db deploy@nfs-server:${SCHEMA_DIR}/schema_windows_${VERSION}.db
                    ssh deploy@nfs-server \
                        "ln -sf schema_windows_${VERSION}.db ${SCHEMA_DIR}/schema_windows_latest.db && \
                         chmod 444 ${SCHEMA_DIR}/schema_windows_${VERSION}.db"
                '''
            }
        }
    }

    post {
        success {
            slackSend color: 'good', message: "Schema deployed: ${VERSION}"
        }
        failure {
            slackSend color: 'danger', message: "Schema deployment failed"
        }
    }
}
```

---

## Platform-Specific Deployment

### Linux/Unix Deployment

```bash
#!/bin/bash
# deploy_linux.sh

set -e

SCHEMA_FILE="examples/schema_linux.yml"
OUTPUT_DB="schema_linux.db"
DEPLOY_DIR="/mnt/shared/path-manager"
VERSION=$(date +%Y%m%d_%H%M%S)

echo "Compiling Linux schema..."
python -m path_manager.compiler $SCHEMA_FILE $OUTPUT_DB --format sqlite

echo "Deploying to $DEPLOY_DIR..."
cp $OUTPUT_DB ${DEPLOY_DIR}/schema_linux_${VERSION}.db

echo "Updating symlink..."
ln -sf schema_linux_${VERSION}.db ${DEPLOY_DIR}/schema_linux_latest.db

echo "Setting permissions..."
chmod 444 ${DEPLOY_DIR}/schema_linux_${VERSION}.db

echo "Deployment complete: schema_linux_${VERSION}.db"

# Cleanup old versions (keep last 10)
cd $DEPLOY_DIR
ls -t schema_linux_*.db | tail -n +11 | xargs -r rm
```

### Windows Deployment

```powershell
# deploy_windows.ps1

$ErrorActionPreference = "Stop"

$SchemaFile = "examples\schema_windows.yml"
$OutputDb = "schema_windows.db"
$DeployDir = "\\server\shared\path-manager"
$Version = Get-Date -Format "yyyyMMdd_HHmmss"

Write-Host "Compiling Windows schema..."
python -m path_manager.compiler $SchemaFile $OutputDb --format sqlite

Write-Host "Deploying to $DeployDir..."
Copy-Item $OutputDb "$DeployDir\schema_windows_$Version.db"

Write-Host "Updating symlink..."
$LinkPath = "$DeployDir\schema_windows_latest.db"
if (Test-Path $LinkPath) {
    Remove-Item $LinkPath
}
New-Item -ItemType SymbolicLink -Path $LinkPath -Target "schema_windows_$Version.db"

Write-Host "Setting read-only..."
Set-ItemProperty "$DeployDir\schema_windows_$Version.db" -Name IsReadOnly -Value $true

Write-Host "Deployment complete: schema_windows_$Version.db"

# Cleanup old versions (keep last 10)
Get-ChildItem "$DeployDir\schema_windows_*.db" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -Skip 10 |
    Remove-Item
```

### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install path-manager
COPY . .
RUN pip install -e .

# Compile schemas
RUN python -m path_manager.compiler examples/schema_linux.yml /schemas/schema_linux.db
RUN python -m path_manager.compiler examples/schema_windows.yml /schemas/schema_windows.db

# Set read-only
RUN chmod 444 /schemas/*.db

# Volume for schema access
VOLUME ["/schemas"]

CMD ["python", "-c", "import time; time.sleep(999999)"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  path-manager:
    build: .
    volumes:
      - schemas:/schemas:ro

  application:
    image: your-app
    volumes:
      - schemas:/mnt/schemas:ro
    environment:
      - SCHEMA_PATH=/mnt/schemas/schema_linux.db

volumes:
  schemas:
```

---

## High Availability

### Load Balancing

For high-traffic environments, deploy multiple NFS servers:

```bash
# HAProxy configuration
# /etc/haproxy/haproxy.cfg

frontend nfs_frontend
    bind *:2049
    mode tcp
    default_backend nfs_servers

backend nfs_servers
    mode tcp
    balance roundrobin
    server nfs1 nfs1.example.com:2049 check
    server nfs2 nfs2.example.com:2049 check
    server nfs3 nfs3.example.com:2049 check
```

### Replication

Replicate schemas across data centers:

```bash
#!/bin/bash
# replicate_schemas.sh

PRIMARY="/mnt/nfs-primary/path-manager"
SECONDARY="/mnt/nfs-secondary/path-manager"

# Rsync with verification
rsync -avz --checksum --delete \
    $PRIMARY/schemas/ \
    $SECONDARY/schemas/

# Verify checksums
cd $PRIMARY/schemas
sha256sum *.db > checksums.txt

cd $SECONDARY/schemas
sha256sum -c $PRIMARY/schemas/checksums.txt
```

### Caching

Implement local caching for faster access:

```python
from pathlib import Path
import shutil
from path_manager.resolver import PathResolver

class CachedResolver:
    def __init__(self, nfs_path: Path, cache_dir: Path):
        self.nfs_path = nfs_path
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Copy to local cache
        cached_schema = self.cache_dir / nfs_path.name
        if not cached_schema.exists():
            shutil.copy2(nfs_path, cached_schema)

        # Use cached version
        self.resolver = PathResolver.from_file(cached_schema)

    def __getattr__(self, name):
        return getattr(self.resolver, name)

# Usage
resolver = CachedResolver(
    Path('/mnt/path-manager/schema_latest.db'),
    Path('/tmp/path-manager-cache')
)
```

---

## Monitoring

### Health Checks

```python
# health_check.py
from path_manager.resolver import PathResolver
from pathlib import Path
import sys

def health_check(schema_path: str) -> bool:
    """Check if schema is accessible and valid."""
    try:
        schema = Path(schema_path)

        # Check file exists
        if not schema.exists():
            print(f"ERROR: Schema not found: {schema_path}")
            return False

        # Check readable
        if not schema.is_file():
            print(f"ERROR: Not a file: {schema_path}")
            return False

        # Try to load
        resolver = PathResolver.from_file(schema)

        # Try basic operation
        kinds = list(resolver.store.iter_all_kinds())
        if not kinds:
            print(f"WARNING: No kinds found in schema")

        resolver.close()

        print(f"OK: Schema healthy ({len(kinds)} kinds)")
        return True

    except Exception as e:
        print(f"ERROR: Health check failed: {e}")
        return False

if __name__ == '__main__':
    schema_path = sys.argv[1] if len(sys.argv) > 1 else '/mnt/path-manager/schema_latest.db'
    success = health_check(schema_path)
    sys.exit(0 if success else 1)
```

### Monitoring Script

```bash
#!/bin/bash
# monitor_schemas.sh

SCHEMA_DIR="/mnt/path-manager/schemas"
LOG_FILE="/var/log/path-manager/monitor.log"
ALERT_EMAIL="ops@example.com"

check_schema() {
    local schema=$1

    # Check file exists
    if [ ! -f "$schema" ]; then
        echo "ERROR: Schema missing: $schema" | tee -a $LOG_FILE
        return 1
    fi

    # Check readable
    if [ ! -r "$schema" ]; then
        echo "ERROR: Schema not readable: $schema" | tee -a $LOG_FILE
        return 1
    fi

    # Run health check
    if ! python health_check.py "$schema"; then
        echo "ERROR: Health check failed: $schema" | tee -a $LOG_FILE
        return 1
    fi

    return 0
}

# Check both schemas
ERRORS=0

if ! check_schema "${SCHEMA_DIR}/schema_linux_latest.db"; then
    ERRORS=$((ERRORS + 1))
fi

if ! check_schema "${SCHEMA_DIR}/schema_windows_latest.db"; then
    ERRORS=$((ERRORS + 1))
fi

# Alert if errors
if [ $ERRORS -gt 0 ]; then
    echo "Schema monitoring detected $ERRORS error(s)" | \
        mail -s "Path Manager Alert" $ALERT_EMAIL
    exit 1
fi

echo "$(date): All schemas healthy" >> $LOG_FILE
exit 0
```

### Prometheus Metrics

```python
# metrics.py
from prometheus_client import Gauge, Counter, start_http_server
from path_manager.resolver import PathResolver
import time

# Metrics
schema_size = Gauge('path_manager_schema_size_bytes', 'Schema file size')
schema_kinds = Gauge('path_manager_schema_kinds', 'Number of kinds')
resolve_time = Gauge('path_manager_resolve_time_seconds', 'Path resolve time')
resolve_errors = Counter('path_manager_resolve_errors_total', 'Resolve errors')

def collect_metrics(schema_path: str):
    """Collect metrics from schema."""
    try:
        # File size
        schema_size.set(Path(schema_path).stat().st_size)

        # Number of kinds
        with PathResolver.from_file(schema_path) as resolver:
            kinds = list(resolver.store.iter_all_kinds())
            schema_kinds.set(len(kinds))

            # Measure resolve time
            start = time.time()
            resolver.get_path('proj_root', root='/test', proj='demo')
            resolve_time.set(time.time() - start)

    except Exception as e:
        resolve_errors.inc()
        print(f"Metrics collection error: {e}")

if __name__ == '__main__':
    start_http_server(8000)

    while True:
        collect_metrics('/mnt/path-manager/schema_latest.db')
        time.sleep(60)
```

---

## Troubleshooting

### Common Issues

#### Issue: "File not found" on NFS

**Symptoms:**
```
FileNotFoundError: /mnt/path-manager/schema_latest.db
```

**Solutions:**
1. Check NFS mount: `mount | grep path-manager`
2. Verify file exists on server: `ls -l /exports/path-manager`
3. Check network connectivity: `ping nfs-server`
4. Remount if stale: `sudo umount /mnt/path-manager && sudo mount -a`

#### Issue: SQLite "database is locked"

**Symptoms:**
```
sqlite3.OperationalError: database is locked
```

**Solutions:**
1. Verify immutable mode is enabled (should be automatic)
2. Check file permissions: `ls -l schema.db`
3. Ensure no write operations in code
4. Use MsgPack format instead

#### Issue: Slow schema loading

**Symptoms:**
- Long startup times
- High NFS latency

**Solutions:**
1. Use local caching (see Caching section)
2. Reduce NFS mount options: `mount -o noatime,nodiratime`
3. Use MsgPack with mmap
4. Deploy schema closer to clients

#### Issue: Schema version mismatch

**Symptoms:**
```
ValidationError: Unknown kind 'new_kind'
```

**Solutions:**
1. Check symlink: `ls -l /mnt/path-manager/schema_latest.db`
2. Force refresh cache (if using caching)
3. Verify deployment completed
4. Check client is using correct schema path

### Debug Mode

Enable debug logging:

```python
import logging
from path_manager.resolver import PathResolver

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('path_manager')

resolver = PathResolver.from_file('schema.db')
# ... debug output will show detailed operations ...
```

### Validation Tools

```bash
# Verify schema integrity
sqlite3 schema.db "PRAGMA integrity_check;"

# List all kinds
sqlite3 schema.db "SELECT name FROM kinds;"

# Check field definitions
sqlite3 schema.db "SELECT name, regex FROM fields;"

# Verify ambiguities
sqlite3 schema.db "SELECT * FROM ambiguities;"
```

---

## Best Practices

1. **Always version schemas** - Use timestamps or semantic versioning
2. **Test before deploy** - Run full test suite in CI/CD
3. **Use symlinks** - For atomic updates
4. **Monitor health** - Regular health checks and alerts
5. **Keep backups** - Retain old versions for rollback
6. **Document changes** - Schema changelog in git
7. **Gradual rollout** - Test in staging first
8. **Read-only permissions** - Prevent accidental modifications
9. **Use caching** - For performance in high-latency environments
10. **Plan for failures** - Have rollback procedures ready
