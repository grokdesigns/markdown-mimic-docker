FROM python:3.13.2-slim
WORKDIR /app
COPY mimic.py .
RUN echo "deb https://deb.debian.org/debian trixie main contrib" > /etc/apt/sources.list
RUN echo "" > /etc/apt/sources.list.d/debian.sources
RUN apt-get update && apt-get full-upgrade -y && apt-get clean && apt-get autoremove -y
RUN apt-get install -y git
RUN git config --global --add safe.directory /github/workspace
CMD ["python", "/app/mimic.py"]