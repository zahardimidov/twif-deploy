FROM python:3.10-alpine

WORKDIR /background

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .

CMD python run.py