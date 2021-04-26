import os
import configparser as cp
import logging

from flask import Flask, request, abort
import redis

import extractor, writer, setup

service_name = os.path.splitext(os.path.basename(__file__))[0]
app = Flask(service_name)

# init config
local_folder = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(local_folder, 'config', '{}.conf'.format(service_name))
config = cp.ConfigParser()
config.read(config_path)

# init cache
cache = redis.Redis(host=config.get('cache', 'host'),
                    port=config.get('cache', 'port'))

# init logging
logger, ch = setup.setup_logger()

# Expose an health check endpoint for the cache
@app.route('/check', methods = ['GET'])
def check():
    try:
        cache.info()
        return "Cache up"
    except:
        abort(500, 'Cache not reachable')

# Main endpoint parsing a TRIAS file and adding the related offers to the cache.
# Expects a TRIAS file as body of the POST request. 
# Returns the request_id associated to the offers parsed.
@app.route('/extract', methods = ['POST'])
def extract():
    request.get_data()
    offers = request.data
    
    # TODO Add additional validation/Define error codes
    try:
        parsed_request = extractor.extract_trias(offers)
        logger.info("Offers parsed from Trias [request_id:{}]".format(parsed_request.id))

        cache_reply = writer.write_to_cache(cache, parsed_request)
        logger.debug("Cache write executed {} commands".format(len(cache_reply)))
        logger.info("Offers inserted in the Cache [request_id:{}]".format(parsed_request.id))
    except Exception as e:
        abort(500, 'Parsing failed. Exception: {}'.format(e))

    response = app.response_class(
        response='{{ "request_id" : "{}" }}'.format(parsed_request.id),
        status=200,
        mimetype='application/json'
    )

    return response

if __name__ == '__main__':
    import os

    FLASK_PORT = 5000
    REDIS_HOST = "localhost"
    REDIS_PORT = 6379
    cache = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

    logger.setLevel(logging.DEBUG)

    os.environ["FLASK_ENV"] = "development"
    app.run(port=FLASK_PORT, debug=True, use_reloader=False)

    exit(0)