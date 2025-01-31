FROM python:3.12-slim

# switch working directory
WORKDIR /app
# copy the requirements file into the image
COPY ./requirements.txt ./
RUN pip install --upgrade pip
RUN apt-get update -y
# RUN python -m pip install --upgrade pip

# install the dependencies and packages in the requirements file
RUN pip install -r requirements.txt

# copy every content from the local file to the image
COPY . /app
EXPOSE 5000
# configure the container to run in an executed manner

CMD ["gunicorn", "--config", "gin_config.py", "main:app"]