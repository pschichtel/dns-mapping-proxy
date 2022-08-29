FROM python:3.10-alpine

RUN mkdir /proxy

COPY requirements.txt /proxy/requirements.txt

RUN pip install -r /proxy/requirements.txt

COPY main.py /proxy/main.py

ENTRYPOINT ["/proxy/main.py"]

