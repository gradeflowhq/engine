FROM python:3.11-slim 

ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1

# Copy engine source
COPY . /tmp/engine

# Install the engine
RUN pip install --upgrade pip && pip install "/tmp/engine[ml]"

# Additional dependencies for backend executor
RUN pip install httpx pydantic-settings

# Create non-root user to run the CLI
RUN useradd -m -u 10001 appuser

# Default working directory
WORKDIR /workspace

# Drop privileges
USER appuser

# Pre-download the model
RUN python -c "from fastembed import TextEmbedding; list(TextEmbedding('BAAI/bge-small-en-v1.5').embed(['warmup']))"

# gradeflow-engine console script is on PATH via venv
ENTRYPOINT ["gradeflow-engine"]
CMD ["--help"]