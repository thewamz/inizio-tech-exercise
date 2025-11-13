# inizio-tech-exercise

This is a FastAPI application.

# Khassandra AI

This is an app that performs text classification on product reviews to predict the activity a consumer performed using a product.

## Technology Stack

It is actively developed using Python and Fast API.

Requires:

Python >= 3.12
Fast API
Docker

## Development

This application can be developed in a Docker environment or virtual environment.

### Docker Environment

To run the app in a Docker environment:

Bring up the docker environment: `make up`

Bring down the docker environment: `make down`

When you bring up the Docker environment, a `docker-entrypoint` will be run to fetch articles from the PubMed API, and
then you will be able to generate articles via the `/write-article` endpoint.

### Virtual Environment

Create a virtual environment and install dependencies.

```
pip install -r requirements.txt
```

### Run Development Server

Run the Fast API development server

Use python directly: `uvicorn api.main:app --reload`

### Usage

To fetch data from PubMed, run `python run_pipeline.py`.

The pipeline will fetch articles from the PubMed API, generate summaries in plain English and
check to make sure there is limited hallucinations being produced by the LLM.

To generate an article, send a POST request to `localhost:8000/write-article`.

The POST request must include the title of the article in the body.

It will be easier to use the Swagger UI: `http://localhost:8000/docs`

### Unit Tests

Run unit tests using Python: `python -m unittest discover tests`

### Code QA

`pre-commit` is used to run checks on the codebase before commits are
made to `git`.

To run checks: `make check`

You can invoke `pre-commit` directly: `pre-commit run --all-files`

For more information: https://pre-commit.com/

### Manage Dependencies

`pip-tools` is used manage application dependencies

For more information: https://github.com/jazzband/pip-tools

Install pip-tools

```
pip install pip-tools
```

Add a new dependency to `requirements.in` and then run:

```
make requirements
```

Upgrade dependencies

```
make upgrade-requirements
```

## CI/CD

To be described.

### Deploy App

To be described