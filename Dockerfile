FROM mcr.microsoft.com/azure-functions/python:4-python3.11

WORKDIR /home/site/wwwroot

# Install runtime dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Install application wheel
COPY dist/*.whl /tmp/
RUN pip install /tmp/*.whl && rm /tmp/*.whl

# Copy Azure Functions entry points
COPY function_app.py host.json ./
COPY src/functions ./src/functions

EXPOSE 80
