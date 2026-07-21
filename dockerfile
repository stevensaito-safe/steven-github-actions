FROM public.ecr.aws/lambda/python:3.12

# Install unzip/curl for grabbing the bw binary
RUN dnf install -y unzip curl && dnf clean all

# Download and install Bitwarden CLI (Linux x64)
RUN curl -Lo /tmp/bw.zip "https://vault.bitwarden.com/download/?app=cli&platform=linux" \
    && unzip /tmp/bw.zip -d /usr/local/bin \
    && chmod +x /usr/local/bin/bw \
    && rm /tmp/bw.zip

# Bitwarden CLI needs a writable config dir - only /tmp is writable in Lambda
ENV BITWARDENCLI_APPDATA_DIR=/tmp/bw
ENV HOME=/tmp

# Install your Python deps
COPY requirements.txt ${LAMBDA_TASK_ROOT}
RUN pip install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

# Copy your code
COPY app.py ${LAMBDA_TASK_ROOT}

CMD [ "app.handler" ]