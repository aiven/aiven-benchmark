FROM fedora

RUN dnf install -y gcc gcc-c++ git make openssl-devel

WORKDIR /root
RUN git clone https://github.com/edenhill/librdkafka.git
WORKDIR /root/librdkafka
RUN ./configure
RUN make
WORKDIR /root

RUN pip3 install aiven-client

ADD load_generator.py /root/
CMD python3 /root/load_generator.py
