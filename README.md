# Indentr - FastAPI
Backend for indentr website.

## Run locally

### Create new virtual env
```bash
python3 -m venv venv
```

### Activate virtual environment (mac)
```bash
source venv/bin/activate 
```

### Install dependencies
Once the virtual environment is activated you can then install the necessary dependencies.
```bash
pip install -r requirements.txt
```

### Run server
Command to run the server with hot reload, ie server will automatically reload on changes to code.
```bash
uvicorn app.main:app --reload
```

## Code Formatting
### Black
Black is a code formatter for Python that enforces a consistent and opinionated coding style. It automatically formats your Python code to ensure it adheres to the defined style guidelines. To run Black on your project, use the following command:
```bash
black .
```

### Ruff
Ruff is a powerful "super-formatter" that combines multiple linters and code formatters to analyze and automatically format your Python code. It includes tools like Black, isort, pyflakes, flake8-comprehensions, and flake8-bugbear.
```bash
ruff .
```


## API documentation (provided by Swagger UI)

```bash
http://127.0.0.1:8000/docs
```
