FROM raspbian/jessie
RUN apt-get update && apt-get -y install build-essential git uuid-dev

RUN git clone https://github.com/dailab/libsml.git /build/libsml
COPY ehzpoll.c /build/libsml/examples/ehzpoll.c

WORKDIR /build/libsml
RUN make
RUN cp sml/lib/libsml.* /usr/lib/arm-linux-gnueabihf/

WORKDIR /build/libsml/examples
RUN cc -static -I../sml/include/ -g -Wall ehzpoll.c -l:libsml.a -l:libuuid.a  -o ehzpoll


FROM arm32v6/alpine:3.5
RUN apk add --no-cache dumb-init python py-flask
COPY --from=0 /build/libsml/examples/ehzpoll /bin/
COPY ehzserve.py /bin/
ENTRYPOINT ["dumb-init", "--"]
CMD ["python", "/bin/ehzserve.py"]

# docker run -v /dev/ttyUSBx:/dev/ttyUSB0 ehzpoll
