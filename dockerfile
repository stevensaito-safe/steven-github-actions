FROM public.ecr.aws/lambda/python:3.12

# curl is already present (curl-minimal) — only unzip is needed
RUN dnf install -y unzip

# Download and install Bitwarden CLI (Linux x64)
RUN curl -Lo /tmp/bw.zip "https://vault.bitwarden.com/download/?app=cli&platform=linux" \
    && unzip /tmp/bw.zip -d /usr/local/bin \
    && chmod +x /usr/local/bin/bw \
    && rm /tmp/bw.zip

# Removing
#ENV PATH="/opt/bin:${PATH}"

# Copy app code and Chalice lib
COPY app.py ${LAMBDA_TASK_ROOT}
COPY chalicelib ${LAMBDA_TASK_ROOT}/chalicelib

# Install dependencies
COPY requirements-PROD.txt ${LAMBDA_TASK_ROOT}
RUN pip install -r ${LAMBDA_TASK_ROOT}/requirements-PROD.txt --target ${LAMBDA_TASK_ROOT}

CMD ["app.handler"]