# 📘 IdyieLLM – Technical Documentation

## 1. Introduction

### Project name
**IdyieLLM**

### Description
IdyieLLM is the IA model that powers the Idyie solution. It is designed to transform human
prompts into database queries, enabling users to interact with their data in a natural language format.

### Main technologies
- Python
- Docker / Docker Compose

## 2. ⚙️ Requirements

### Supported environments
- macOS, Linux recommended (Windows with WSL2 supported)
- Terminal access with `bash`/`zsh`

### Required software
- Docker & Docker Compose
- Git
- (Optional) Python if not fully containerized

### Used ports
| Service     | Port |
|-------------|------|
| LLM         | 9090 |

## 3. 🚀 Installation & Launch

### 3.1 Clone the project
```bash
git clone git@github.com:IdyieOrg/IdyieLLM.git
cd IdyieLLM
```
### 3.2 Configure the environment
```bash
cp .env.example .env
```
### 3.3 Launch the application locally
```bash
docker-compose build
docker compose up -d; docker attach idyie-llm-application
```

## 4. 🏗 Project Structure
### 4.1 Simplified tree
```
.
├── app
│   ├── config.py
│   ├── __init__.py
│   ├── __pycache__
│   ├── routes/
│   └── utils/
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── .github
│   └── workflows/
├── .gitignore
├── README.md
├── requirements.txt
├── run.py
├── setup.cfg
└── tests
    └── test_ping.py
```

### 4.2 Main libraries
- `Flask (3.0.3)`: Web framework for building the API.
- `python-dotenv (1.0.1)`: For loading environment variables from `.env` files.
- `flake8 (7.1.1)`: Code style checker for Python.
- `torch (2.5.1)`: PyTorch library for machine learning and deep learning.
- `transformers= (.48.0)`: Hugging Face Transformers library for working with pre-trained models.

##  5. 🔐 Environment Variables

A ```.env.example``` file is provided to configure the required variables:
```bash
# Application
IDYIE_API_URL=http://idyie-api-application:8080
FLASK_ENV=development
PORT=9090
```
The variables are used to configure the Docker container

## 6. 🧪 Tests & Code Quality
Tool used:
- `flake8`: For checking code style and quality.
- `unittest`: For running unit tests.
<!-- - `pytest`: For running tests. -->

Useful commands:
```bash
docker exec -it idyie-llm-application sh
flake8 .
```
```bash
docker compose exec application python -m unittest
```

## 7. 🔄 Continuous Integration (CI)
### CI Pipeline

GitHub Actions (or GitLab CI) is used to:
- Check code quality with flake8
- Build and push Docker images
- Run tests

### CI Configuration
The CI is run on every push to the `main` branch and on pull requests. The configuration is in the `.github/workflows/ci.yml` file.

## 8. 📚 Appendices
### Glossary
- CI: Continuous Integration

### Useful links
- [GitHub Repository](https://github.com/IdyieOrg/IdyieLLM)
- [Github Organization](https://github.com/IdyieOrg)
- [CI Dashboard](https://github.com/IdyieOrg/IdyieLLM/actions/)
<!-- - Swagger API Documentation (if available) -->

### Conventions
- Python style: PEP 8
