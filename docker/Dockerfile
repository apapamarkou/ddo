FROM debian:trixie-slim

LABEL maintainer="DDO Contributors"
LABEL description="Debian Desktop Optimizer — CI/CD build environment"

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.13 \
    python3.13-dev \
    python3-pip \
    python3-venv \
    python3-full \
    build-essential \
    dpkg-dev \
    devscripts \
    fakeroot \
    lintian \
    git \
    ca-certificates \
    curl \
    apt-utils \
    # For pytest-qt headless mode
    xvfb \
    libqt6widgets6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
COPY src/ ./src/
COPY tests/ ./tests/
COPY data/ ./data/
COPY packaging/ ./packaging/
COPY docs/ ./docs/
COPY scripts/ ./scripts/

# Create venv and install all dependencies including dev extras
RUN python3.13 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --upgrade pip wheel && \
    pip install -e ".[dev]"

# Default command runs full CI pipeline
CMD ["bash", "-c", "\
    echo '=== Ruff ===' && ruff check src/ tests/ && \
    echo '=== Black ===' && black --check src/ tests/ && \
    echo '=== Mypy ===' && mypy src/ddo/backend/ src/ddo/models/ src/ddo/utils/ && \
    echo '=== Pytest ===' && pytest --cov=ddo --cov-report=term-missing -x \
"]
