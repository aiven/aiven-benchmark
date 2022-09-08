FROM fedora

RUN dnf install -y python3-pip
RUN pip3 install aiven-client kafka-python

ADD result_reader.py /root/
CMD python3 /root/result_reader.py
