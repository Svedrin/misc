FROM alpine:latest

# Install basic dependencies
RUN apk add --no-cache python3 uwsgi-python3

# Install dependencies first without copying the whole application,
# so that Docker can cache the dependencies
COPY requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r /app/requirements.txt

# Now install the rest of the application
COPY . /app
WORKDIR /app

EXPOSE 5000
CMD [ "uwsgi", "--ini", "uwsgi.ini" ]

# build using: docker build -t myproject .
# run using:   docker run --rm -it myproject
# dev edition: docker run --rm -it -v $PWD:/app myproject
