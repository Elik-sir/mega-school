FROM python:3.12-slim

# switch working directory
WORKDIR /app
# copy the requirements file into the image
COPY ./requirements.txt ./
RUN apt-get update -y
RUN apt-get install -y pip

RUN cat requirements.txt
# install the dependencies and packages in the requirements file
RUN pip3 install -r requirements.txt

# copy every content from the local file to the image
COPY . /app

# configure the container to run in an executed manner
ENTRYPOINT ["python"]

CMD ["main.py"]