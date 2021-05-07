FROM python:3.8

WORKDIR /code

ENV FLASK_APP=trias_extractor_service.py
ENV FLASK_RUN_HOST=0.0.0.0

RUN pip3 install --no-cache-dir --upgrade pip

COPY requirements.txt requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

COPY trias_extractor /code/trias_extractor
COPY trias_extractor_service.py trias_extractor_service.py
COPY trias_extractor_service.conf trias_extractor_service.conf

EXPOSE 5000

CMD ["flask", "run"]