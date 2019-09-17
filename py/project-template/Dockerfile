FROM alpine:latest

RUN apk add --no-cache python3 uwsgi-python3

COPY . /app
WORKDIR /app

RUN pip3 install --no-cache-dir -r /app/requirements.txt

EXPOSE 5000
CMD [ "uwsgi", "--ini", "uwsgi.ini" ]
