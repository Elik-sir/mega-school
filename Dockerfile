FROM debian:latest
RUN apt-get update -y && apt-get upgrade -y && apt-get install curl
RUN curl -L https://ollama.com/download/ollama-linux-amd64.tgz -o ollama-linux-amd64.tgz
RUN tar -C /usr -xzf ollama-linux-amd64.tgz


FROM python:3.12-slim

# switch working directory
WORKDIR /app
# copy the requirements file into the image
COPY ./requirements.txt ./
RUN pip install --upgrade pip
RUN apt-get update -y
RUN ollama pull qwen2.5:14b
# RUN python -m pip install --upgrade pip

# install the dependencies and packages in the requirements file
RUN pip install -r requirements.txt

# copy every content from the local file to the image
COPY . /app
EXPOSE 5000
# configure the container to run in an executed manner
ENTRYPOINT ["python"]

CMD ["main.py"]