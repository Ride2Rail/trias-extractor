import dateutil.parser
import isodate

from trias_extractor import writer

# Classes of the model parsed from TRIAS

class Request:

    def __init__(self, id):
        self.id = id
        self.offers = {}
        self.user_id = None
        self.traveller_id = None
        self.start_time = None
        self.end_time = None
        self.start_point = None
        self.end_point = None
        self.cycling_dist_to_stop = None
        self.walking_dist_to_stop = None
        self.walking_speed = None
        self.cycling_speed = None
        self.driving_speed = None
        self.max_transfers = None
        self.expected_duration = None
        self.via = []


    def add_offer(self, offer):
        self.offers[offer.id] = offer

class Offer:

    def __init__(self, id, trip, bookable_total, complete_total):
        self.id = id
        self.trip = trip
        self.offer_items = {}
        self.bookable_total = parse_price(bookable_total)
        self.complete_total = parse_price(complete_total)

    def add_offer_item(self, offer_item):
        self.offer_items[offer_item.id] = offer_item

class Trip:

    def __init__(self, id, duration, start_time, end_time, num_interchanges, length):
        self.id = id
        self.duration = duration
        self.start_time = start_time
        self.end_time = end_time
        self.num_interchanges = num_interchanges
        self.length = length
        self.ordered_legs_ids = []
        self.legs = {}

    def add_leg(self, leg):
        self.legs[leg.id] = leg
        self.ordered_legs_ids.append(leg.id)

class OfferItem:

    def __init__(self, id, name, fares_authority_ref, fares_authority_text, price):
        self.id = id
        self.name = name
        self.fares_authority_ref = fares_authority_ref
        self.fares_authority_text = fares_authority_text
        self.price = parse_price(price)
        self.leg_ids = []

class TripLeg:

    def __init__(self, id, start_time, end_time, leg_track, length, leg_stops, transportation_mode, travel_expert):
        self.id = id
        self.start_time = start_time
        self.end_time = end_time
        self.leg_track = leg_track
        self.leg_stops = leg_stops
        self.transportation_mode = transportation_mode
        self.travel_expert = travel_expert
        self.attributes = {}
        self.length = length
        self.duration = None

    def add_attribute(self, key, value):
        self.attributes[key] = value

class TimedLeg(TripLeg):

    def __init__(self, id, start_time, end_time, leg_track, length, leg_stops, transportation_mode, travel_expert, 
        line, journey):
        super().__init__(id, start_time, end_time, leg_track, length, leg_stops, transportation_mode, travel_expert)
        # self.duration = end_time - start_time
        delta = dateutil.parser.parse(end_time) - dateutil.parser.parse(start_time)
        self.duration = str(isodate.duration_isoformat(delta))
        self.line = line
        self.journey = journey

    def to_redis(self, pipeline, prefix):
    	writer.timed_leg_to_cache(self, pipeline, prefix)

class ContinuousLeg(TripLeg):

    def __init__(self, id, start_time, end_time, leg_track, length, leg_stops, transportation_mode, travel_expert, 
        duration):
        super().__init__(id, start_time, end_time, leg_track, length, leg_stops, transportation_mode, travel_expert)
        self.duration = duration

    def to_redis(self, pipeline, prefix):
    	writer.continuous_leg_to_cache(self, pipeline, prefix)

class RideSharingLeg(ContinuousLeg):
    def __init__(self, id, start_time, end_time, leg_track, length, leg_stops, transportation_mode, travel_expert, 
        duration, driver, vehicle):
        super().__init__(id, start_time, end_time, leg_track, length, leg_stops, transportation_mode, travel_expert, duration)
        self.driver = driver
        self.vehicle = vehicle

    def to_redis(self, pipeline, prefix):
    	writer.ridesharing_leg_to_cache(self, pipeline, prefix)

class Location:

    def __init__(self, id, name, loc_lon, loc_lat):
        self.id = id
        self.name = name
        self.pos = (float(loc_lon), float(loc_lat))

class StopPoint(Location):

    def __init__(self, id, name, loc_lon, loc_lat, stop_name):
        super().__init__(id, name, loc_lon, loc_lat)
        self.stop_name = stop_name
        self.codes = {}

    def add_code(self, system, value):
        self.codes[system] = value

class Address(Location):

    def __init__(self, id, name, loc_lon, loc_lat, address_name):
        super().__init__(id, name, loc_lon, loc_lat)
        self.address_name = address_name

# Utility functions

def parse_price(price):
    d_price = {}
    d_price["value"] = price[0]
    d_price["currency"] = price[1]
    return d_price