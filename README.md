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

> Once the server is running you can view the API documentation (provided by Swagger UI) by entering the following url
```bash
http://127.0.0.1:8000/docs
```





## Code Formatting
### Black
Black is a Python code formatter that automatically formats your code to ensure consistent style, eliminating the need for manual formatting.
```bash
black .
```

### Ruff
Ruff is a code analysis tool that comprehensively checks and can apply automatic fixes to your Python code.
```bash
ruff .
```



## Testing
To run tests just enter the following into terminal
```bash
pytest
```

> To view the applications total test code coverage 
```bash
pytest --cov=app --cov-report term-missing   
``` 








## Docker
### Build image
Generates a Docker image, which can then be used to create a run containers.
```bash
docker build -t indentr-backend .
```

### Run container
Starts a Docker container named indentr-backend and maps port 8080 from the host to port 8080 inside the container.
```bash
docker run -p 8080:8080 indentr-backend
```

## Google cloud
Deploy to google cloud
```bash
gcloud run deploy indentr-backend --port 8080 --source . --region=europe-west1
```