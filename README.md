# Indentr - FastAPI
Backend for indentr website.

## Run locally

### Create new virtual env
```
python3 -m venv venv
```

### Activate virtual environment (mac)
```
source venv/bin/activate 
```

### Install dependencies
Once the virtual environment is activated you can then install the necessary dependencies.
```
pip install -r requirements.txt
```

### Run server
Command to run the server with hot reload, ie server will automatically reload on changes to code.
```
uvicorn app.main:app --reload
```


## API documentation (provided by Swagger UI)

```
http://127.0.0.1:8000/docs
```
