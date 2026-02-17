# Support Directory

This directory contains supporting files for the SOC Copilot Demo project that aren't part of the core application code.

## Directory Structure

```
support/
├── setup/          # Infrastructure setup and configuration
├── docs/           # Design documents and specifications
└── scripts/        # Utility scripts for development and testing
```

## Purpose

The `support/` directory keeps infrastructure, documentation, and utility files organized separately from the main application code. This makes it easier to:

- Find setup instructions and configuration files
- Access design specifications and technical documentation
- Run utility scripts without cluttering the main codebase
- Maintain a clean separation between application code and supporting materials

## Directory Details

### `setup/`
**Purpose:** Infrastructure setup, deployment configurations, and environment setup scripts.

**Typical Contents:**
- Colab notebooks for GCP setup
- Cloud infrastructure templates
- Database initialization scripts
- Docker configurations
- Environment setup guides

See [setup/README.md](setup/README.md) for details.

### `docs/`
**Purpose:** Design documents, technical specifications, and architectural documentation.

**Typical Contents:**
- Build specifications (e.g., `vc_demo_build_spec_ciso_v1.md`)
- Architecture diagrams
- API documentation
- Design decision records
- Demo scripts and talking points

See [docs/README.md](docs/README.md) for details.

### `scripts/`
**Purpose:** Utility scripts for development, testing, and data management.

**Typical Contents:**
- Database seeding scripts
- Test data generators
- Demo reset scripts
- Data migration utilities
- Performance testing tools

See [scripts/README.md](scripts/README.md) for details.

---

## Usage Guidelines

### What Belongs in `support/`?

✅ **Include:**
- Setup and configuration files
- Design documentation
- Utility scripts
- Demo preparation materials
- Infrastructure code (IaC)
- Testing utilities

❌ **Don't Include:**
- Application source code (use `backend/` or `frontend/`)
- Environment variables (use `.env` in project root)
- Dependencies (use `requirements.txt` or `package.json`)
- Build outputs or compiled files

### When to Add New Files

**Setup Scripts:** Add to `support/setup/` when:
- Creating new infrastructure setup procedures
- Adding cloud resource provisioning scripts
- Documenting environment configuration

**Documentation:** Add to `support/docs/` when:
- Writing design specifications
- Creating architecture diagrams
- Documenting demo workflows
- Recording design decisions

**Utility Scripts:** Add to `support/scripts/` when:
- Building data seeding tools
- Creating test utilities
- Adding demo reset functionality
- Developing migration scripts

---

## Quick Reference

### Common Tasks

**Set up the project for first time:**
```bash
# See support/setup/README.md for setup instructions
cd support/setup
# Follow setup guide
```

**Seed demo data:**
```bash
# See support/scripts/README.md for available scripts
cd support/scripts
python seed_demo_data.py
```

**Read design specs:**
```bash
# See support/docs/README.md for documentation index
cd support/docs
cat vc_demo_build_spec_ciso_v1.md
```

### File Organization Examples

**Example 1: New Colab Setup Notebook**
- Create: `support/setup/gcp_neo4j_setup.ipynb`
- Document in: `support/setup/README.md`

**Example 2: New Demo Script**
- Create: `support/docs/15_minute_demo_script.md`
- Document in: `support/docs/README.md`

**Example 3: New Test Data Generator**
- Create: `support/scripts/generate_test_alerts.py`
- Document in: `support/scripts/README.md`

---

## Maintenance

### Keep It Organized

- Update README files when adding new scripts or documents
- Use descriptive filenames with dates/versions when appropriate
- Archive outdated files to an `archive/` subdirectory
- Document dependencies for scripts in their respective README files

### Version Control

- Commit support files to git
- Add large binary files (like dataset CSVs) to `.gitignore`
- Use meaningful commit messages for documentation updates

---

## Related Documentation

- [PROJECT_STRUCTURE.md](../PROJECT_STRUCTURE.md) - Application code structure
- [PROJECT_COMPLETE.md](../PROJECT_COMPLETE.md) - Project completion summary
- [README.md](../README.md) - Main project README

---

**Last Updated:** February 6, 2026
**Maintainer:** Development Team
