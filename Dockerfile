FROM python:3.8

WORKDIR /code

ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

RUN pip3 install --no-cache-dir --upgrade pip

COPY requirements.txt requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

EXPOSE 5000

CMD ["flask", "run"]