import sys
import time
import redis

def write_to_cache(cache, object):
    retries = 5
    while True:
        try:
            return object.to_redis(cache)
        except redis.exceptions.ConnectionError as exc:
            if retries == 0:
                raise exc
            retries -= 1
            time.sleep(0.5)

# >>> r = redis.Redis(...)
# >>> r.set('bing', 'baz')
# >>> # Use the pipeline() method to create a pipeline instance
# >>> pipe = r.pipeline()
# >>> # The following SET commands are buffered
# >>> pipe.set('foo', 'bar')
# >>> pipe.get('bing')
# >>> # the EXECUTE call sends all buffered commands to the server, returning
# >>> # a list of responses, one for each command.
# >>> pipe.execute()

# for key in cache.scan_iter("offer_id:*"):
#     cache.delete(key)