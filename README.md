# NeMo Data Designer SaaS API

A FastAPI-based SaaS application for generating synthetic datasets using NVIDIA's NeMo models. This service provides powerful data generation capabilities with support for multiple column types including samplers, expressions, LLM-based text/code generation, and validation columns.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Configuration](#configuration)
- [API Endpoints](#api-endpoints)
- [Usage Examples](#usage-examples)
- [Deployment](#deployment)
- [Project Structure Details](#project-structure-details)
- [Technologies](#technologies)

## Overview

NeMo Data Designer is a comprehensive data generation platform that leverages NVIDIA's NeMo models to create high-quality synthetic datasets. It supports various data generation methods including statistical samplers, Python expressions, and LLM-powered generation for complex data scenarios.

## Features

- **Multiple Column Types**:
  - Statistical Samplers (Bernoulli, Gaussian, Poisson, Uniform, etc.)
  - Expression-based columns (Python expressions)
  - LLM Text Generation
  - LLM Code Generation
  - LLM Structured Output Generation
  - LLM Judge columns with scoring

- **Seed Data Support**: Upload and use existing datasets as seed data for constrained generation

- **Job Management**: Asynchronous job processing with status tracking

- **Two Modes**:
  - **Create Mode**: Generate full synthetic datasets
  - **Preview Mode**: Generate sample data for preview

- **LLM Proxy**: OpenAI-compatible chat completions endpoint

- **Encryption**: Built-in encryption for sensitive authentication data

- **Cloud-Ready**: Terraform and Ansible configurations for deployment

## Project Structure

```
nemo_data_designer/
├── ReadMe.md                          # This file
├── requirements.txt.txt               # Python dependencies
├── src/
│   ├── __init__.py
│   ├── nemo_setup.sh                 # Setup and deployment script
│   ├── ansible/
│   │   └── deploy.yml               # Ansible deployment playbook
│   ├── terraform/
│   │   └── main.tf                  # Terraform IaC configuration
│   └── NemoDataDesignerAPI/
│       ├── __init__.py
│       ├── main.py                  # FastAPI application entry point
│       ├── config.py                # Configuration and environment setup
│       ├── data_generation_request.py       # Data generation logic
│       ├── data_generation_with_seed_data_request.py  # Seed-based generation
│       ├── controllers/
│       │   ├── __init__.py
│       │   ├── job_controller.py    # Job execution logic
│       │   └── proxy_controller.py  # LLM proxy logic
│       ├── models/
│       │   ├── __init__.py
│       │   └── requests.py          # Request/response Pydantic models
│       ├── routes/
│       │   ├── __init__.py
│       │   ├── base_router.py       # Health check endpoint
│       │   ├── client_router.py     # Data generation endpoints
│       │   └── proxy_router.py      # LLM proxy endpoints
│       ├── utils/
│       │   ├── __init__.py
│       │   ├── encryption.py        # Encryption utilities
│       │   ├── patching.py          # Runtime patches
│       │   ├── helpers.py           # File upload, seed data processing, and API credential tunneling
│       │   └── adapters.py          # OpenAI to Anthropic API format adapters
│       ├── uploaded_datasets/        # Directory for uploaded seed data
│       └── generated_output/         # Directory for generated outputs
```

## Installation

### Prerequisites

- Python 3.8+
- NeMo Microservices running on `http://127.0.0.1:8080`
- Datastore service running on `http://127.0.0.1:3000`

### Quick Start

1. **Make setup script executable** (Linux/macOS):
```bash
chmod +x src/nemo_setup.sh
```

2. **Run setup and deploy**:
```bash
./src/nemo_setup.sh
```

This script will handle:
- Installing Python dependencies
- Creating necessary directories
- Starting the FastAPI server

### Manual Installation

1. **Install dependencies**:
```bash
pip install -r requirements.txt.txt
```

2. **Navigate to API directory**:
```bash
cd src/NemoDataDesignerAPI
```

3. **Start the server**:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

## Configuration

Configuration is managed in `src/NemoDataDesignerAPI/config.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `FIXED_MODEL_ALIAS` | `saas_generator` | Model alias for generation requests |
| `BASE_IP` | `127.0.0.1` | NeMo microservices host |
| `NEMO_MICROSERVICES_BASE_URL` | `http://127.0.0.1:8080` | NeMo microservices URL |
| `DATASTORE_ENDPOINT` | `http://127.0.0.1:3000/v1/hf` | Datastore service endpoint |
| `UPLOAD_DIR` | `uploaded_datasets/` | Directory for uploaded seed datasets |
| `OUTPUT_DIR` | `generated_output/` | Directory for generated outputs |
| `JOB_STORE` | In-memory dict | Job storage (use Redis in production) |

## API Endpoints

### Health Check
- **GET** `/ok` - Server health check
  ```json
  {"status": "ok"}
  ```

### Data Generation

#### Create Job
- **POST** `/data_generation/v1/create`
  
  Creates a new data generation job that generates full synthetic datasets.
  
  Request (multipart/form-data):
  - `generate_request` (JSON string): Generation configuration
  - `seed_data` (file, optional): CSV file with seed data

  Response:
  ```json
  {
    "status": "processing",
    "job_id": "uuid-string"
  }
  ```

#### Preview Job
- **POST** `/data_generation/v1/preview`
  
  Creates a preview job that generates sample data for validation.
  
  Request (multipart/form-data):
  - `generate_request` (JSON string): Generation configuration
  - `seed_data` (file, optional): CSV file with seed data

  Response:
  ```json
  {
    "status": "processing",
    "job_id": "uuid-string"
  }
  ```

#### Get Job Status
- **GET** `/data_generation/v1/jobs/{job_id}`
  
  Retrieves the status of a submitted job.
  
  Response:
  ```json
  {
    "status": "completed|processing|failed",
    "created_at": 1234567890,
    "result": {...}
  }
  ```

### LLM Proxy (OpenAI Compatible)

#### List Models
- **GET** `/proxy/v1/models`

  Lists available models.
  
  Response:
  ```json
  {
    "object": "list",
    "data": [
      {
        "id": "tunnel",
        "object": "model",
        "owned_by": "saas"
      }
    ]
  }
  ```

#### Chat Completions
- **POST** `/proxy/v1/chat/completions`
  
  OpenAI-compatible chat completions endpoint for routing requests to configured LLM providers.

## Usage Examples

### Example 1: Generate Synthetic Data with Samplers

```python
import requests
import json

# Create generation request
generate_request = {
    "columns": [
        {
            "name": "age",
            "sampler_type": "gaussian",
            "params": {"mean": 35, "std": 15}
        },
        {
            "name": "email",
            "sampler_type": "person_from_faker",
            "params": {"provider": "email"}
        }
    ],
    "num_records": 1000,
    "model_id": "gpt-3.5-turbo",
    "model_provider": "openai",
    "provider_api_key": "your-api-key",
    "provider_base_url": "https://api.openai.com/v1",
    "provider_api_version": "2023-07"
}

# Submit job
response = requests.post(
    "http://localhost:8000/data_generation/v1/create",
    data={
        "generate_request": json.dumps(generate_request)
    }
)

job_id = response.json()["job_id"]

# Check status
status_response = requests.get(
    f"http://localhost:8000/data_generation/v1/jobs/{job_id}"
)
print(status_response.json())
```

### Example 2: Generate Data with Seed Dataset

```python
import requests
import json

generate_request = {
    "columns": [
        {
            "name": "description",
            "prompt": "Generate a product description based on the category",
            "system_prompt": "You are a product description writer"
        }
    ],
    "num_records": 100,
    "model_id": "gpt-3.5-turbo",
    "model_provider": "openai",
    "provider_api_key": "your-api-key",
    "provider_base_url": "https://api.openai.com/v1",
    "provider_api_version": "2023-07"
}

# Submit job with seed data
with open("seed_data.csv", "rb") as f:
    response = requests.post(
        "http://localhost:8000/data_generation/v1/create",
        data={
            "generate_request": json.dumps(generate_request)
        },
        files={
            "seed_data": f
        }
    )

job_id = response.json()["job_id"]
```

## Deployment

### Using Ansible

Deploy to production servers using Ansible:

```bash
ansible-playbook src/ansible/deploy.yml
```

See `src/ansible/deploy.yml` for configuration details.

### Using Terraform

Define cloud infrastructure using Terraform:

```bash
cd src/terraform
terraform init
terraform plan
terraform apply
```

See `src/terraform/main.tf` for infrastructure configuration.

## Project Structure Details

### Controllers

- **job_controller.py**: Orchestrates data generation jobs, handles seed data processing, builds NeMo configurations, and manages the generation pipeline
- **proxy_controller.py**: Routes LLM requests to configured external providers (OpenAI-compatible)

### Routes

- **base_router.py**: Health check endpoint `/ok`
- **client_router.py**: Data generation endpoints (`/data_generation/v1/*`)
- **proxy_router.py**: LLM proxy endpoints (`/proxy/v1/*`)

### Models

**requests.py** defines request/response schemas:
- `SamplerColumn`: Statistical data samplers (Bernoulli, Gaussian, Poisson, Uniform, UUID, DateTime, etc.)
- `ExpressionColumn`: Python expression-based generation
- `LLMTextColumn`: LLM text generation with customizable prompts
- `LLMCodeColumn`: LLM code generation with language specification
- `LLMStructuredColumn`: LLM structured output with defined schemas
- `LLMJudgeColumn`: LLM-based scoring/judgment with multiple scoring options
- `ValidationColumn`: Data validation rules
- `GenerateRequest`: Main generation request containing all column definitions

### Utilities

- **encryption.py**: Encrypts sensitive authentication credentials
- **patching.py**: Applies runtime patches for compatibility

## Technologies

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) - Modern async Python web framework
- **Server**: [Uvicorn](https://www.uvicorn.org/) - ASGI server
- **Data Processing**: [Pandas](https://pandas.pydata.org/) - Data manipulation and CSV handling
- **Validation**: [Pydantic](https://docs.pydantic.dev/) - Request/response validation
- **NeMo Models**: [nemo-microservices](https://github.com/NVIDIA/NeMo) - NVIDIA NeMo synthetic data generation
- **Encryption**: [cryptography](https://cryptography.io/) - Secure credential handling
- **Logging**: [python-json-logger](https://github.com/madzak/python-json-logger) - Structured JSON logging
- **Async HTTP**: [httpx](https://www.python-httpx.org/) - Async HTTP client
- **Infrastructure**: 
  - **Terraform**: Infrastructure as Code for cloud deployment
  - **Ansible**: Configuration management and deployment automation

## Environment Variables

The application cleans and configures environment variables in `config.py`:

- **Network**: Disables HTTP/HTTPS proxies for local communication
- **HuggingFace**: Sets `HF_HUB_ENABLE_HF_TRANSFER=0` for compatibility

## Data Directories

- **uploaded_datasets/**: Stores uploaded seed CSV files for constrained generation
- **generated_output/**: Stores generated synthetic datasets after completion

## Architecture Overview

### Request Flow

1. **Client submits request** to `/data_generation/v1/create` or `/preview` endpoint
2. **Seed data is processed** (if provided) - columns are extracted and uploaded
3. **Job is queued** with unique ID and added to in-memory job store
4. **Background task processes** the generation request asynchronously
5. **NeMo Microservices** generates synthetic data based on configuration
6. **Results are stored** and job status is updated
7. **Client polls** job status endpoint to retrieve results

### Data Generation Pipeline

1. Authentication data is encrypted for external LLM providers
2. NeMo configuration is built from column specifications
3. Seed data (if provided) is uploaded to datastore with column metadata
4. Generation request is sent to NeMo Microservices
5. Multiple column types are processed:
   - **Samplers**: Statistical distributions generate diverse values
   - **Expressions**: Python expressions create derived columns
   - **LLM-based**: External LLM calls generate text, code, or structured data
   - **Judge columns**: LLM evaluates and scores other columns

## Performance Considerations

- **In-Memory Job Store**: Current implementation uses Python dict. For production, migrate to Redis or PostgreSQL
- **Async Processing**: Fast endpoint responses - computation happens in background tasks
- **CSV Upload**: Seed data is read to extract column information, enabling constrained generation
- **Datastore Caching**: Column schemas are cached to optimize repeated generations

## Error Handling

- **Validation Errors**: Invalid request schemas return 400 Bad Request
- **Missing Jobs**: Querying non-existent job IDs returns 404 Not Found
- **Generation Errors**: Failures during generation are captured in job status
- **Proxy Errors**: LLM proxy issues return 502 Bad Gateway

## Support

For issues, feature requests, or questions:
1. Check existing documentation in this README
2. Review API endpoint specifications
3. Verify configuration settings in `config.py`
4. Check NeMo Microservices availability and connectivity
"# synth-data-gen" 
