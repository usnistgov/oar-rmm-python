# NIST Resource Metadata Management (RMM) API

A Python-based implementation of the NIST Resource Metadata Management service, providing RESTful APIs to manage and query metadata for various NIST resources including datasets, papers, code, patents, and more.

## Table of Contents

- [Overview](#overview)
- [System Requirements](#system-requirements)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Configuration](#configuration)
  - [Environment Variables](#environment-variables)
  - [Remote Configuration](#remote-configuration)
  - [Local File Configuration](#local-file-configuration)
- [Running the Application](#running-the-application)
- [API Endpoints](#api-endpoints)
- [Development](#development)
- [Testing](#testing)

## Overview

The Resource Metadata Management (RMM) API provides a metadata catalog service for NIST research outputs. It allows searching, querying, and managing metadata for:

- Scientific datasets
- Research papers
- Software/code repositories
- Patents
- API specifications
- Taxonomies and controlled vocabularies
- Version information

The service uses MongoDB for data storage and offers a flexible configuration system to adapt to different environments.

## System Requirements

- Python 3.12+
- MongoDB 4.0+
- Virtual environment tool (venv, pipenv, or conda)

## Project Structure

```
.
├── app/                    # Application code
│   ├── __init__.py
│   ├── .env                # Local environment variables
│   ├── config.py           # Configuration handling
│   ├── database.py         # Database connection management
│   ├── index.html          # Homepage template
│   ├── main.py             # FastAPI application entry point
│   ├── certificates/       # SSL certificates for secure connections
│   ├── crud/               # CRUD operations for each resource type
│   ├── middleware/         # Request processing and metrics middleware
│   ├── routers/            # API route definitions
│   └── scripts/            # Utility scripts for data population
├── db/                     # Database files and fixtures
├── docs/                   # Documentation
├── scripts/                # Utility scripts
└── tests/                  # Test suite
```

## Installation

### Step 1: Clone the repository

```bash
git clone https://github.com/usnistgov/oar-rmm-python.git
cd oar-rmm-python
```

### Step 2: Create a virtual environment

Using Python's built-in venv:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

Or using Conda:

```bash
conda create -n rmm-api python=3.12.9
conda activate rmm-api
```

### Step 3: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Set up MongoDB

Ensure MongoDB is running locally on the default port (27017) or update the configuration to point to your MongoDB instance.

## Configuration

The application supports multiple configuration sources in the following order of precedence:

1. Remote configuration server (if enabled)
2. Local configuration file (if specified)
3. Environment variables
4. Default values

### Environment Variables

Create or modify the .env file in the app directory:

```
MONGO_URI=mongodb://localhost:27017
DB_NAME=oar-rmm
MONGO_URI_METRICS=
METRICS_DB_NAME=oar-rmm-metrics
USE_REMOTE_CONFIG=false
REMOTE_CONFIG_URL=http://localhost:8084/oar-rmm/local
```

Key environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `MONGO_URI` | MongoDB connection string | `mongodb://localhost:27017` |
| `DB_NAME` | Database name | `oar-rmm` |
| `MONGO_URI_METRICS` | Separate MongoDB for metrics (optional) | same as `MONGO_URI` |
| `METRICS_DB_NAME` | Metrics database name | `oar-rmm-metrics` |
| `USE_REMOTE_CONFIG` | Enable remote config | `false` |
| `REMOTE_CONFIG_URL` | URL for remote config server | `None` |
| `LOCAL_CONFIG_FILE` | Path to local config file | `None` |

### Remote Configuration

The application can fetch configuration from a Spring Cloud Config compatible server:

1. Set `USE_REMOTE_CONFIG=true` in your environment or .env file
2. Set `REMOTE_CONFIG_URL` to point to your config server (e.g., `http://config-server:8084/oar-rmm/local`)

You can test the remote configuration without starting the application:

```bash
python scripts/fetch_remote_config.py http://config-server:8084/oar-rmm/local
```

To fetch and save the configuration for later use:

```bash
python scripts/fetch_remote_config.py http://config-server:8084/oar-rmm/local -o app/config.json
```

### Local File Configuration

To use a previously saved configuration file:

1. Set `LOCAL_CONFIG_FILE` environment variable to point to your JSON config file
2. Ensure `USE_REMOTE_CONFIG` is set to `false` or unset

## Running the Application

### Development mode

```bash
# Start with default configuration (environment variables)
./start.sh

# Start with remote configuration
export USE_REMOTE_CONFIG=true
export REMOTE_CONFIG_URL=http://config-server:8084/oar-rmm/local
./start.sh

# Start with a local configuration file
export LOCAL_CONFIG_FILE=app/config.json
./start.sh
```

### Production mode

For production, use a WSGI server like Gunicorn:

```bash
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app
```

## API Endpoints

The application provides the following main endpoints:

- `/records` - Dataset metadata
- `/papers` - Scientific paper metadata
- `/code` - Software code repository metadata
- `/patents` - Patent metadata
- `/apis` - API specifications metadata
- `/taxonomy` - Taxonomy/vocabulary management
- `/fields` - Metadata field definitions
- `/versions` - Version information
- `/releasesets` - Release set information

For full API documentation, navigate to docs when the application is running.

## Development

### Adding a new resource type

1. Create a new model in `app/models/`
2. Create a CRUD class in crud
3. Create a router in routers
4. Add the router to main.py

### Code Style

Follow PEP 8 guidelines for Python code. Use docstrings for all functions and classes.

## Testing

Run the test suite:

```bash
pytest tests/
```

Run specific tests:

```bash
pytest tests/test_record.py
```

## Troubleshooting

### Configuration Issues

If you're having issues with configuration loading, check:

1. The application logs for configuration source information
2. Run with `--log-level debug` for more detailed logging
3. Test remote configuration access using the fetch script:

```bash
python scripts/fetch_remote_config.py http://config-server:8084/oar-rmm/local
```

### Database Connectivity

If MongoDB connection fails:
1. Ensure MongoDB is running and accessible
2. Verify credentials and connection strings in your configuration
3. Check network connectivity and firewall rules if using a remote MongoDB

---
