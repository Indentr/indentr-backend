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
Black is a Python code formatter that automatically formats your code to ensure consistent style, eliminating the need for manual formatting.
```bash
black .
```

### Ruff
Ruff is a code analysis tool that combines multiple linters and formatters, including Black, to comprehensively check and format Python code.
> Running ruff in your project will apply Black's formatting rules along with other linters and formatters configured in Ruff.
```bash
ruff .
```


## API documentation (provided by Swagger UI)

```bash
http://127.0.0.1:8000/docs
```
