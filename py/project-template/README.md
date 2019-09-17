This is a Python project template featuring a teeny-tiny Flask app. It is
served through uwsgi (meant to be run behind an nginx proxy), packed through
Docker and built through DroneCI. The Docker image is based upon alpine
Linux and is thus probably as small as it gets (without putting in lots of
work). Requirements are installed from a requirements.txt file in the main
directory.

Nginx config:

```
upstream hosts_template {
    server 127.0.0.1:8080;
}

server {
    listen       80;
    server_name  template.somedomain.com;

    include /etc/nginx/uwsgi_params;

    location / {
        uwsgi_pass hosts_template;
    }
}
```
