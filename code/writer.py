import time
import redis
import geojson
import logging

# logger
logger = logging.getLogger(__name__)

# Builds and executes a pipeline to serialize a model.Request to the Offer Cache
def write_to_cache(cache, request):
    retries = 5
    pipe = cache.pipeline()
    request_to_cache(request, pipe)
    while True:
        try:
            return pipe.execute()
        except redis.exceptions.ConnectionError as exc:
            logging.debug("Attempt failed. Retries remaining: {}".format(retries))
            if retries == 0:
                raise exc
            retries -= 1
            time.sleep(0.5)

# Adds to the pipeline (pipe) the commands to serialize a model.Request
def request_to_cache(r, pipe):
    prefix = r.id
    if r.start_time != None:
    	    pipe.set("{}:start_time".format(prefix), r.start_time)
    if r.end_time != None:
        pipe.set("{}:end_time".format(prefix), r.end_time)
    if r.start_point != None:
        pipe.set("{}:start_point".format(prefix),
            geojson.dumps(geojson.Point(r.start_point)))
    if r.end_point != None:
        pipe.set("{}:end_point".format(prefix),
            geojson.dumps(geojson.Point(r.end_point)))
    # Offers
    pipe.lpush("{}:offers".format(prefix),*(r.offers.keys()))
    for key in r.offers.keys():
        offer_to_cache(r.offers[key], pipe, prefix)

# Adds to the pipeline (pipe) the commands to serialize a model.Offer
def offer_to_cache(o, pipe, prefix):
    prefix = "{}:{}".format(prefix, o.id)

    # From Trip
    t = o.trip
    if t.duration != None:
        pipe.set("{}:duration".format(prefix), t.duration)
    if t.start_time != None:
        pipe.set("{}:start_time".format(prefix), t.start_time)
    if t.end_time != None:
        pipe.set("{}:end_time".format(prefix), t.end_time)
    if t.num_interchanges != None:
        pipe.set("{}:num_interchanges".format(prefix), t.num_interchanges)
    # Legs
    pipe.lpush("{}:legs".format(prefix),*(t.legs.keys()))
    for key in t.legs.keys():
        t.legs[key].to_redis(pipe, prefix)

    # From Offer
    if o.bookable_total != None:
        pipe.hmset("{}:bookable_total".format(prefix), o.bookable_total)
    if o.complete_total != None:
        pipe.hmset("{}:complete_total".format(prefix), o.complete_total)
    # Offer Items
    pipe.lpush("{}:offer_items".format(prefix),*(o.offer_items.keys()))
    for key in o.offer_items.keys():
        offer_item_to_cache(o.offer_items[key], pipe, prefix)

# Adds to the pipeline (pipe) the commands to serialize a model.OfferItem
def offer_item_to_cache(o_i, pipe, prefix):
    prefix = "{}:{}".format(prefix, o_i.id)
    if o_i.price != None:
    	pipe.hmset("{}:price".format(prefix), o_i.price)
    if o_i.name != None:
        pipe.set("{}:name".format(prefix), o_i.name)
    if o_i.fares_authority_ref  != None:
        pipe.set("{}:fares_authority_ref".format(prefix), o_i.fares_authority_ref)
    if o_i.fares_authority_text  != None:
        pipe.set("{}:fares_authority_text".format(prefix), o_i.fares_authority_text)
    # Legs
    pipe.lpush("{}:legs".format(prefix),*(o_i.leg_ids))

# Adds to the pipeline (pipe) the commands to serialize a model.TripLeg
def trip_leg_to_cache(tl, pipe, prefix):
    prefix = "{}:{}".format(prefix, tl.id)
    if tl.start_time != None:
    	pipe.set("{}:start_time".format(prefix), tl.start_time)
    if tl.end_time != None:
        pipe.set("{}:end_time".format(prefix), tl.end_time)
    if tl.duration  != None:
        pipe.set("{}:duration".format(prefix), tl.duration)
    if tl.transportation_mode != None:
        pipe.set("{}:transportation_mode ".format(prefix), tl.transportation_mode)
    if tl.leg_stops != None:
        pipe.set("{}:leg_stops".format(prefix),
            geojson.dumps(geojson.LineString(tl.leg_stops)))
    if tl.leg_track != None:
        pipe.set("{}:leg_track".format(prefix),
            geojson.dumps(geojson.LineString(tl.leg_track)))
    if tl.travel_expert != None:
        pipe.set("{}:travel_expert".format(prefix), tl.travel_expert)
    for key in tl.oic.keys():
        pipe.set("{}:{}".format(prefix, key), tl.oic[key])

# Adds to the pipeline (pipe) the commands to serialize a model.TimedLeg
def timed_leg_to_cache(tl, pipe, prefix):
    trip_leg_to_cache(tl, pipe, prefix)
    prefix = "{}:{}".format(prefix, tl.id)
    pipe.set("{}:leg_type".format(prefix), "timed")
    if tl.line != None:
        pipe.set("{}:line".format(prefix), tl.line)
    if tl.journey != None:
        pipe.set("{}:journey".format(prefix), tl.journey)

# Adds to the pipeline (pipe) the commands to serialize a model.ContinuousLeg
def continuous_leg_to_cache(tl, pipe, prefix):
    trip_leg_to_cache(tl, pipe, prefix)
    prefix = "{}:{}".format(prefix, tl.id)
    pipe.set("{}:leg_type".format(prefix), "continuous")

# Adds to the pipeline (pipe) the commands to serialize a model.RideSharingLeg
def ridesharing_leg_to_cache(tl, pipe, prefix):
    trip_leg_to_cache(tl, pipe, prefix)
    prefix = "{}:{}".format(prefix, tl.id)
    pipe.set("{}:leg_type".format(prefix), "ridesharing")
    if tl.driver != None:
        pipe.set("{}:driver".format(prefix), tl.driver)
    if tl.vehicle != None:
        pipe.set("{}:vehicle".format(prefix), tl.vehicle)

