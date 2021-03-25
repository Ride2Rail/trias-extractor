import os
import sys
import pathlib
import logging
import configparser as cp

from flask import Flask, request, abort
import redis

import extractor, writer

app = Flask(__name__)
cache = redis.Redis(host='redis', port=6379)

##### Logging
# create logger
logger = logging.getLogger(__name__)

# create formatter
formatter_fh = logging.Formatter('[%(asctime)s][%(levelname)s]: %(message)s')
formatter_ch = logging.Formatter('[%(asctime)s][%(levelname)s](%(name)s): %(message)s')

# create handler
handler = logging.StreamHandler()
handler.setFormatter(formatter_ch)
root = logging.getLogger()
root.setLevel(os.environ.get("LOGLEVEL", "INFO"))
root.addHandler(handler)
#####

@app.route('/extract', methods = ['POST'])
def extract():
    request.get_data()
    offers = request.data
    
    # TODO Add validation?
    # TODO Define more errors?
    # try:
    parsed_request = extractor.extract_trias(offers)
    logger.info("Offers parsed from TRIAS [request_id:{}]".format(parsed_request.id))

    writer.write_to_cache(cache, parsed_request)
    logger.info("Offers inserted in the Cache [request_id:{}]".format(parsed_request.id))
    # except:
    #    abort(500, 'Parsing failed')

    response = app.response_class(
        response='{{ "request_id" : "{}"}}'.format(parsed_request.id),
        status=200,
        mimetype='application/json'
    )

    return response

if __name__ == '__main__':

    # remove default logger
    while logger.hasHandlers():
        logger.removeHandler(logger.handlers[0])

    # create file handler which logs INFO messages
    fh = logging.FileHandler("{}.log".format(__name__), mode='a+')
    fh.setLevel(logging.INFO)

    # create console handler and set level to DEBUG
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    # add formatter to ch
    ch.setFormatter(formatter_ch)
    fh.setFormatter(formatter_fh)

    # add ch to logger
    logger.addHandler(fh)
    logger.addHandler(ch)

    FLASK_PORT = 5000

    REDIS_HOST = 'localhost'
    REDIS_PORT = 6379

    os.environ["FLASK_ENV"] = "development"

    cache = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

    app.run(port=FLASK_PORT, debug=True)

    exit(0)