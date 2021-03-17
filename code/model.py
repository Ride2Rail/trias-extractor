import dateutil.parser
import isodate

class Request:

    def __init__(self, id, start_time, end_time, start_lon, start_lat, end_lon, end_lat):
        self.id = id
        self.start_time = start_time
        self.end_time = end_time
        # Serialize as geojson.Point((-155.52, 19.61))
        self.start_loc = (float(start_lon), float(start_lat))
        self.end_loc = (float(end_lon), float(end_lat))
        self.offers = {}

    def add_offer(self, offer):
        self.offers[offer.id] = offer

    def to_redis(self, pipeline):
    	# TODO
        return

    def to_string(self):
        return " ".join([self.id, self.start_time, self.end_time,
            self.start_loc, self.end_loc, str(len(self.offers))])

class Offer:

    def __init__(self, id, trip, bookable_total, complete_total):
        self.id = id
        self.trip = trip
        self.offer_items = []
        self.bookable_total = bookable_total # Pair (price, currency)
        self.complete_total = complete_total # Pair (price, currency)

    def add_offer_item(self, offer_item):
		self.offer_items.append(offer_item)

    def to_redis(self, pipeline):
    	# TODO
        return

    def to_string(self):
        return " ".join([self.id, str(len(self.offer_items)), self.trip.to_string()])

class OfferItem:

    def __init__(self, id, name, fares_authority_ref, fares_authority_text, price):
        self.id = id
        self.name = name
        self.fares_authority_ref = fares_authority_ref
        self.fares_authority_text = fares_authority_text
        self.price = price
        # TODO Add currency to constructor OR use pair as for Offer
        self.currency = "EUR"
        self.legs = []
        self.context = {}

class Trip:

    def __init__(self, id, duration, start_time, end_time, num_interchanges):
        self.id = id
        self.duration = duration
        self.start_time = start_time
        self.end_time = end_time
        self.num_interchanges = num_interchanges
        self.legs = {}

    def add_leg(self, leg):
        self.legs[leg.id] = leg

    def to_redis(self, pipeline):
    	# TODO
        return

    def to_string(self):
        return " ".join([self.id, self.duration, self.start_time, self.end_time,
                         self.num_interchanges, str(len(self.legs))])

class TripLeg:

    def __init__(self, id, start_time, end_time, leg_track, leg_stops, transportation_mode, travel_expert):
        self.id = id
        self.start_time = start_time
        self.end_time = end_time
        # Serialize as geojson.MultiPoint([(-155.52, 19.61), (-157.97, 21.46)])
        self.leg_track = leg_track
        # Serialize as geojson.MultiPoint
        self.leg_stops = leg_stops
        self.transportation_mode = transportation_mode
        self.travel_expert = travel_expert

    def to_redis(self, pipeline):
    	# TODO
        return

class TimedLeg(TripLeg):

    def __init__(self, id, start_time, end_time, leg_track, leg_stops, transportation_mode, travel_expert, 
        line, journey):
        super().__init__(id, start_time, end_time, leg_track, leg_stops, transportation_mode, travel_expert)
        # self.duration = end_time - start_time
        delta = dateutil.parser.parse(end_time) - dateutil.parser.parse(start_time)
        self.duration = str(isodate.duration_isoformat(delta))
        self.line = line
        self.journey = journey

    def to_redis(self, pipeline):
    	# TODO
        return

class ContinuousLeg(TripLeg):

    def __init__(self, id, start_time, end_time, leg_track, leg_stops, transportation_mode, travel_expert, 
        duration):
        super().__init__(id, start_time, end_time, leg_track, leg_stops, transportation_mode, travel_expert)
        self.duration = duration

    def to_redis(self, pipeline):
    	# TODO
        return

class RideSharingLeg(ContinuousLeg):

    def __init__(self, id, start_time, end_time, leg_track, leg_stops, transportation_mode, travel_expert, 
        duration, driver, vehicle, passenger):
        super().__init__(id, start_time, end_time, leg_track, leg_stops, transportation_mode, travel_expert, duration)
        self.driver = driver
        self.vehicle = vehicle
        self.passenger = passenger

    def to_redis(self, pipeline):
    	# TODO
        return

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