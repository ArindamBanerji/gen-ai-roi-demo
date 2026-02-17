# Setup Directory

This directory contains infrastructure setup files, configuration scripts, and environment setup guides for the SOC Copilot Demo.

## Purpose

Place all infrastructure setup and configuration materials here, including:

- **Colab Notebooks** - Google Colab notebooks for GCP resource provisioning
- **Setup Scripts** - Shell scripts for environment configuration
- **Infrastructure as Code** - Terraform, CloudFormation, or similar templates
- **Configuration Files** - Service account keys, configuration templates
- **Setup Guides** - Step-by-step setup documentation

## Typical Files

### Colab Notebooks
```
ciso_setup_notebook_v1.ipynb       # GCP + Neo4j + Vertex AI setup
bigquery_setup.ipynb               # BigQuery dataset and table creation
firestore_setup.ipynb              # Firestore collections setup
```

### Shell Scripts
```
setup_backend.sh                   # Backend environment setup
setup_frontend.sh                  # Frontend dependencies installation
create_venv.sh                     # Python virtual environment creation
```

### Infrastructure Templates
```
terraform/
  ├── main.tf                      # Main Terraform configuration
  ├── neo4j.tf                     # Neo4j Aura provisioning
  └── variables.tf                 # Terraform variables

gcp/
  ├── cloud-run.yaml               # Cloud Run deployment config
  └── iam-policies.json            # IAM role definitions
```

### Configuration Templates
```
.env.example                       # Environment variable template
neo4j-config.yaml                  # Neo4j connection settings
vertex-ai-config.json              # Vertex AI configuration
```

## Setup Workflow

### 1. Initial Setup (First Time)

```bash
# 1. Navigate to setup directory
cd support/setup

# 2. Run Colab notebook (in Google Colab)
# Open: ciso_setup_notebook_v1.ipynb
# Follow notebook instructions to create GCP resources

# 3. Download service account key
# Save to: support/setup/service-account-key.json
# ⚠️ DO NOT commit this file to git!

# 4. Copy environment template
cp .env.example ../../.env

# 5. Fill in environment variables
# Edit ../../.env with your GCP project details

# 6. Run setup script
./setup_backend.sh
./setup_frontend.sh
```

### 2. Database Setup

```bash
# 1. Seed Neo4j database
cd ../../backend
python seed_neo4j.py

# 2. Verify connection
python -c "from app.db.neo4j import neo4j_client; neo4j_client.connect()"
```

### 3. Verification

```bash
# 1. Test backend
cd ../../backend
uvicorn app.main:app --reload --port 8000

# 2. Test frontend
cd ../frontend
npm run dev

# 3. Open browser
# Navigate to: http://localhost:5173
```

## Environment Variables

### Required Variables

```bash
# GCP Project
PROJECT_ID=soc-copilot-demo
REGION=us-central1

# Neo4j Aura
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-secure-password

# Vertex AI
VERTEX_AI_LOCATION=us-central1

# Optional: BigQuery (if using real data instead of mocks)
BIGQUERY_DATASET=soc
```

### Security Notes

⚠️ **Never commit these files to git:**
- Service account keys (*.json)
- `.env` files with real credentials
- Neo4j passwords
- API keys

✅ **Always:**
- Use `.env.example` as a template
- Store credentials in secret management (GCP Secret Manager)
- Rotate keys regularly
- Use least-privilege IAM roles

## Common Setup Issues

### Issue 1: Neo4j Connection Fails

**Symptoms:**
```
ConnectionError: Failed to connect to Neo4j
```

**Solutions:**
- Verify `NEO4J_URI` in `.env` is correct
- Check Neo4j Aura instance is running
- Ensure IP whitelist includes your IP (or use 0.0.0.0/0 for testing)
- Verify username/password are correct

### Issue 2: Vertex AI Permission Denied

**Symptoms:**
```
PermissionDenied: 403 User does not have permission
```

**Solutions:**
- Enable Vertex AI API in GCP console
- Grant service account `Vertex AI User` role
- Verify `PROJECT_ID` matches your GCP project
- Check service account key is valid

### Issue 3: Python Dependencies Fail

**Symptoms:**
```
ModuleNotFoundError: No module named 'fastapi'
```

**Solutions:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Setup Script Templates

### Backend Setup Script

Create `setup_backend.sh`:

```bash
#!/bin/bash
set -e

echo "Setting up SOC Copilot backend..."

# Create virtual environment
cd ../../backend
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Verify installation
python -c "import fastapi; print(f'FastAPI {fastapi.__version__} installed')"

echo "✓ Backend setup complete!"
```

### Frontend Setup Script

Create `setup_frontend.sh`:

```bash
#!/bin/bash
set -e

echo "Setting up SOC Copilot frontend..."

# Navigate to frontend
cd ../../frontend

# Install dependencies
npm install

# Verify installation
npm list react --depth=0

echo "✓ Frontend setup complete!"
```

## Cloud Resource Checklist

Before running the demo, ensure these resources are created:

- [ ] GCP Project created
- [ ] Neo4j Aura instance provisioned
- [ ] Service account created with required roles
- [ ] Service account key downloaded
- [ ] Vertex AI API enabled
- [ ] Neo4j database seeded with demo data
- [ ] Environment variables configured in `.env`
- [ ] Backend dependencies installed
- [ ] Frontend dependencies installed
- [ ] Backend health check passes (GET /)
- [ ] Frontend loads (http://localhost:5173)

## Cleanup

To tear down resources after demo:

```bash
# 1. Delete Neo4j Aura instance (via web console)
# 2. Delete GCP project (or disable APIs)
# 3. Revoke service account keys
# 4. Remove local credentials
rm support/setup/service-account-key.json
rm .env
```

## Reference

- [Neo4j Aura Setup](https://neo4j.com/cloud/aura/)
- [Vertex AI Setup](https://cloud.google.com/vertex-ai/docs/start/introduction-unified-platform)
- [Google Cloud Setup](https://cloud.google.com/sdk/docs/install)

---

**Related Files:**
- Main README: [../README.md](../README.md)
- Project Structure: [../../PROJECT_STRUCTURE.md](../../PROJECT_STRUCTURE.md)

**Last Updated:** February 6, 2026
