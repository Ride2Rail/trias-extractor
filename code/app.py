from flask import Flask, request, abort
import redis

import extractor, writer

app = Flask(__name__)
cache = redis.Redis(host='redis', port=6379)

@app.route('/extract', methods = ['POST'])
def extract():
    request.get_data()
    offers = request.data
    
    # TODO Add validation?
    # TODO Define more errors?
    # try:
    parsed_request = extractor.extract_trias(offers)
    # TODO Implement writing procedure
    writer.write_to_cache(cache, parsed_request)
    # except:
    #    abort(500, 'Parsing failed')

    response = app.response_class(
        response='{{ "request_id" : "{}"}}'.format(parsed_request.id),
        status=200,
        mimetype='application/json'
    )

    return response