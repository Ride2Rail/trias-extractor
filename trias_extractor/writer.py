import time
import redis
import geojson
import logging

from trias_extractor.exception import ParsingException

# logger
logger = logging.getLogger()

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

    if r.user_id != None:
    	pipe.set("{}:user_id".format(prefix), r.user_id)
    if r.traveller_id != None:
    	pipe.set("{}:traveller_id".format(prefix), r.traveller_id)
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
    if r.max_transfers != None:
        pipe.set("{}:max_transfers".format(prefix), r.max_transfers)
    if r.cycling_dist_to_stop != None:
        pipe.set("{}:cycling_dist_to_stop".format(prefix), r.cycling_dist_to_stop)
    if r.walking_dist_to_stop != None:
        pipe.set("{}:walking_dist_to_stop".format(prefix), r.walking_dist_to_stop)
    if r.walking_speed != None:
        pipe.set("{}:walking_speed".format(prefix), r.walking_speed)
    if r.cycling_speed != None:
        pipe.set("{}:cycling_speed".format(prefix), r.cycling_speed)
    if r.driving_speed != None:
        pipe.set("{}:driving_speed".format(prefix), r.driving_speed)
    if r.max_transfers != None:
        pipe.set("{}:max_transfers".format(prefix), r.max_transfers)
    if r.expected_duration != None:
        pipe.set("{}:expected_duration".format(prefix), r.expected_duration)
    # due to simpler extraction, the locations are stored as list of strings
    if r.via_locations:
        pipe.set("{}:via_locations".format(prefix),
            geojson.dumps(geojson.LineString(r.via_locations)))

    # Offers
    offer_ids = r.offers.keys()
    if len(offer_ids) > 0:
        pipe.lpush("{}:offers".format(prefix),*(offer_ids))
    # else: no offer found
    for key in offer_ids:
        offer_to_cache(r.offers[key], pipe, prefix)
    
    logger.debug("Request {} added to the pipeline".format(r.id))

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
    if t.length != None:
        pipe.set("{}:length".format(prefix), t.length)
    # Legs
    for key in t.ordered_legs_ids:
        pipe.lpush("{}:legs".format(prefix), key)
        t.legs[key].to_redis(pipe, prefix)

    # From Offer
    if o.bookable_total != None:
        pipe.hmset("{}:bookable_total".format(prefix), o.bookable_total)
    if o.complete_total != None:
        pipe.hmset("{}:complete_total".format(prefix), o.complete_total)

    # Offer Items
    offer_item_ids = o.offer_items.keys()
    if len(offer_item_ids) > 0:
        pipe.lpush("{}:offer_items".format(prefix),*(offer_item_ids))
    # else: a Offer without associated Offer Items means no purchase needed
    for key in o.offer_items.keys():
        offer_item_to_cache(o.offer_items[key], pipe, prefix)

    logger.debug("Offer {} added to the pipeline".format(o.id))

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
    if len(o_i.leg_ids) > 0:
        pipe.lpush("{}:legs".format(prefix),*(o_i.leg_ids))
    else:
        raise ParsingException("No legs for the offer item {}".format(o_i.id))

    logger.debug("Offer Item {} added to the pipeline".format(o_i.id))

# Adds to the pipeline (pipe) the commands to serialize a model.TripLeg
def trip_leg_to_cache(tl, pipe, prefix):
    prefix = "{}:{}".format(prefix, tl.id)
    if tl.start_time != None:
    	pipe.set("{}:start_time".format(prefix), tl.start_time)
    if tl.end_time != None:
        pipe.set("{}:end_time".format(prefix), tl.end_time)
    if tl.duration  != None:
        pipe.set("{}:duration".format(prefix), tl.duration)
    if tl.length != None:
        pipe.set("{}:length".format(prefix), tl.length)
    if tl.transportation_mode != None:
        pipe.set("{}:transportation_mode".format(prefix), tl.transportation_mode)
    if tl.leg_stops != None:
        pipe.set("{}:leg_stops".format(prefix),
            geojson.dumps(geojson.LineString(tl.leg_stops)))
    if tl.leg_track != None:
        pipe.set("{}:leg_track".format(prefix),
            geojson.dumps(geojson.LineString(tl.leg_track)))
    if tl.travel_expert != None:
        pipe.set("{}:travel_expert".format(prefix), tl.travel_expert)
    for key in tl.attributes.keys():
        pipe.set("{}:{}".format(prefix, key), tl.attributes[key])

# Adds to the pipeline (pipe) the commands to serialize a model.TimedLeg
def timed_leg_to_cache(tl, pipe, prefix):
    trip_leg_to_cache(tl, pipe, prefix)
    prefix = "{}:{}".format(prefix, tl.id)
    pipe.set("{}:leg_type".format(prefix), "timed")
    if tl.line != None:
        pipe.set("{}:line".format(prefix), tl.line)
    if tl.journey != None:
        pipe.set("{}:journey".format(prefix), tl.journey)

    logger.debug("Timed Leg {} added to the pipeline".format(tl.id))

# Adds to the pipeline (pipe) the commands to serialize a model.ContinuousLeg
def continuous_leg_to_cache(tl, pipe, prefix):
    trip_leg_to_cache(tl, pipe, prefix)
    prefix = "{}:{}".format(prefix, tl.id)
    pipe.set("{}:leg_type".format(prefix), "continuous")

    logger.debug("Continuous Leg {} added to the pipeline".format(tl.id))

# Adds to the pipeline (pipe) the commands to serialize a model.RideSharingLeg
def ridesharing_leg_to_cache(tl, pipe, prefix):
    trip_leg_to_cache(tl, pipe, prefix)
    prefix = "{}:{}".format(prefix, tl.id)
    pipe.set("{}:leg_type".format(prefix), "ridesharing")
    if tl.driver != None:
        pipe.hmset("{}:driver".format(prefix), tl.driver)
    if tl.vehicle != None:
        pipe.hmset("{}:vehicle".format(prefix), tl.vehicle)

    logger.debug("Ridesharing Leg {} added to the pipeline".format(tl.id))
