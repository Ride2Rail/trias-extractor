import sys
import time
import logging

from flask import current_app as app
from lxml import etree
from model import *

# namespaces
NS = {'coactive': 'http://shift2rail.org/project/coactive',
      'ns3': 'http://www.vdv.de/trias',
      'xsi': 'http://www.w3.org/2001/XMLSchema-instance'}

# errors
ERREMPTYTREE = 1
ERRINVALIDDATA = 2

def extract_trias(offers):
    parser = etree.XMLParser(ns_clean=True, recover=True, encoding='utf-8')

    try:
        newtree = etree.fromstring(offers, parser=parser)
    except etree.XMLSyntaxError:
        print('Error: Empty tree.', file=sys.stderr)
        raise Exception(ERREMPTYTREE)
    
    # TripRequest
    request_id = newtree.find('.//coactive:UserId', namespaces=NS).text
    # TODO Parse mobility request data when example available

    # TripResponseContext
    trip_response_context = newtree.find('.//ns3:TripResponseContext', namespaces=NS)
    locations = {}
    if trip_response_context != None:
        locations = parse_context(trip_response_context)
    app.logger.info(str(len(locations.keys())) + ' StopPoint extracted')
    # TODO Extract Addresses

    # TripResults
    try:
        _trip_results = newtree.findall('.//ns3:TripResult', namespaces=NS)
    except AttributeError:
        print('Error: Invalid TRIAS data, no TripResult found.', file=sys.stderr)
        raise Exception(ERRINVALIDDATA)

    trips = {}
    offers = {}

    # Trip
    for trip_result in _trip_results:
        trip = trip_result.find('.//ns3:Trip', namespaces=NS)

        # Trip data
        t = extract_trip(trip)
        trips[t.id] = t

        # TripLeg
        _legs = trip.findall('.//ns3:TripLeg', namespaces=NS)
        for leg in _legs:
            leg_id = leg.find('.//ns3:LegId', namespaces=NS).text
            l = None
            if leg.find('.//ns3:TimedLeg', namespaces=NS) != None:
                l = extract_timed_leg(leg_id, 
                    leg.find('.//ns3:TimedLeg', namespaces=NS), locations)
            elif leg.find('.//ns3:ContinuousLeg', namespaces=NS) != None:
                l = extract_continuous_leg(leg_id, 
                    leg.find('.//ns3:ContinuousLeg', namespaces=NS), locations)
            else:
                app.logger.error("Unknown Leg found with LegId: " + leg_id)
            if l != None:
                t.add_leg(l)

    # TODO Review Offer extraction

    #     _offer_items = trip_result.findall('.//ns3:Ticket', namespaces=NS)
    #     for ticket in _offer_items:
    #         offer_item_id = ticket.find('.//ns3:TicketId', namespaces=NS).text
    #         if offer_item_id == "META":
    #             # Build Offer
    #             o = extract_offer(ticket, t)
    #             offers[o.id] = o
    #     for ticket in _offer_items:
    #             # Build Offer Items
    #             extract_offer_item(ticket, offers)

    # TODO Define serialization in Redis

    # for o_k in offers.keys():
    #     writer.write_to_cache(offers[o_k])

    return request_id

def extract_offer_item(ticket, offers):
    offer_item_id = ticket.find('.//ns3:TicketId', namespaces=NS).text
    if offer_item_id != "META":
        name = ticket.find('.//ns3:TicketName', namespaces=NS).text
        auth_ref = ticket.find('.//ns3:FaresAuthorityRef', namespaces=NS).text
        auth_text = ticket.find('.//ns3:FaresAuthorityText', namespaces=NS).text

        _price = ticket.find('.//ns3:Price', namespaces=NS)
        price = "0"
        if _price != None:
            price = _price.text
        o_i = OfferItem(offer_item_id, name, auth_ref, auth_text, price)

        _currency = ticket.find('.//ns3:Currency', namespaces=NS)
        if _currency != None:
            o_i.currency = _currency.text
        
        offer_item = ticket.find(".//ns3:Extension[ @xsi:type = 'coactive:OfferItemTicketExtension' ]", namespaces=NS)
        offer_id = offer_item.find('.//coactive:OfferId', namespaces=NS).text
        o = offers[offer_id]
        if (o == None):
            print("No associated Offer found")
            return
        o.add_offer_item(o_i)
        
        leg_ids = offer_item.findall('.//coactive:TravelEpisodeId', namespaces=NS)
        for id in leg_ids:
            o_i.legs.append(id.text)


def extract_offer(ticket, trip):
    offer = ticket.find(".//ns3:Extension[ @xsi:type = 'coactive:MetaTicketExtension' ]", namespaces=NS)
    offer_id = offer.find('coactive:OfferId', namespaces=NS).text

    _bookable_total = offer.find('coactive:BookableTotal', namespaces=NS)
    bt_p = _bookable_total.find('ns3:Price', namespaces=NS).text
    bt_c = _bookable_total.find('ns3:Currency', namespaces=NS).text
    bookable_total = (bt_p, bt_c)

    _complete_total = offer.find('coactive:CompleteTotal', namespaces=NS)
    ct_p = _complete_total.find('ns3:Price', namespaces=NS).text
    ct_c = _complete_total.find('ns3:Currency', namespaces=NS).text
    complete_total = (ct_p, ct_c)

    return Offer(offer_id, trip, bookable_total, complete_total)

# Returns a dictionary of id:Location parsing a TripResponseContext node
def parse_context(context):
    locations = {}
    _locations = context.findall('.//ns3:Location', namespaces=NS)
    for location in _locations:
        # StopPoint
        if location.find('.//ns3:StopPoint', namespaces=NS) != None :
            id = location.find('.//ns3:StopPointRef', namespaces=NS).text
            name = location.find('.//ns3:LocationName/ns3:Text', namespaces=NS).text
            stop_name = location.find('.//ns3:StopPointName/ns3:Text', namespaces=NS).text
            pos = location.find('.//ns3:GeoPosition', namespaces=NS)
            loc_lon = pos.find('.//ns3:Longitude', namespaces=NS).text
            loc_lat = pos.find('.//ns3:Latitude', namespaces=NS).text

            l = StopPoint(id, name, loc_lon, loc_lat, stop_name)

            _codes = location.findall('.//ns3:PrivateCode', namespaces=NS)
            for code in _codes:
                system = code.find('.//ns3:System', namespaces=NS).text
                value = code.find('.//ns3:Value', namespaces=NS).text
                l.add_code(system, value)

            locations[id] = l

        # Address
        elif location.find('.//ns3:Address', namespaces=NS) != None :
            id = location.find('.//ns3:AddressCode', namespaces=NS).text
            name = location.find('.//ns3:AddressName/ns3:Text', namespaces=NS).text
            pos = location.find('.//ns3:GeoPosition', namespaces=NS)
            loc_lon = pos.find('.//ns3:Longitude', namespaces=NS).text
            loc_lat = pos.find('.//ns3:Latitude', namespaces=NS).text

            l = Location(id, name, loc_lon, loc_lat)
            locations[id] = l
    
    return locations

# Returns mandatory data about a Trip
def extract_trip(trip):
    trip_id = trip.find('ns3:TripId', namespaces=NS).text
    duration = trip.find('ns3:Duration', namespaces=NS).text
    start_time = trip.find('ns3:StartTime', namespaces=NS).text
    end_time = trip.find('ns3:EndTime', namespaces=NS).text
    num_interchanges = trip.find('ns3:Interchanges', namespaces=NS).text

    return Trip(trip_id, duration, start_time, end_time, num_interchanges)

def extract_timed_leg(leg_id, leg, spoints):
    start_time = leg.find('.//ns3:ServiceDeparture/ns3:TimetabledTime', namespaces=NS).text
    end_time = leg.find('.//ns3:ServiceArrival/ns3:TimetabledTime', namespaces=NS).text

    leg_track = extract_leg_track(leg)

    leg_stops = []
    board = leg.find('.//ns3:LegBoard/ns3:StopPointRef', namespaces=NS).text
    leg_stops.append(spoints[board].pos)
    _intermediates = leg.findall('.//ns3:LegIntermediates', namespaces=NS)
    if _intermediates != None:
        for li in _intermediates:
            li_ref = li.find('ns3:StopPointRef', namespaces=NS).text
            leg_stops.append(spoints[li_ref].pos)
    alight = leg.find('.//ns3:LegAlight/ns3:StopPointRef', namespaces=NS).text
    leg_stops.append(spoints[alight].pos)

    transportation_mode = leg.find('.//ns3:PtMode', namespaces=NS).text
    travel_expert = leg.find('.//coactive:TravelExpertId', namespaces=NS).text
    line = leg.find('.//ns3:LineRef', namespaces=NS).text
    journey = leg.find('.//ns3:JourneyRef', namespaces=NS).text
    
    return TimedLeg(leg_id, start_time, end_time, leg_track, leg_stops, 
        transportation_mode, travel_expert, line, journey)

def extract_leg_track(leg):
    _track = leg.find('.//ns3:Projection', namespaces=NS)
    if _track != None:
        track = []
        for pos in list(_track):
            p_lon = pos.find('ns3:Longitude', namespaces=NS).text
            p_lat = pos.find('ns3:Latitude', namespaces=NS).text
            track.append((float(p_lon), float(p_lat)))
        return track
    return None

def extract_continuous_leg(leg_id, leg, locations):
    start_time = leg.find('.//ns3:TimeWindowStart', namespaces=NS).text
    end_time = leg.find('.//ns3:TimeWindowEnd', namespaces=NS).text
    duration = leg.find('.//ns3:Duration', namespaces=NS).text

    leg_track = extract_leg_track(leg)
    
    leg_stops = []
    start = leg.find('.//ns3:LegStart/ns3:StopPointRef', namespaces=NS)
    if start == None:
        start = leg.find('.//ns3:LegStart/ns3:AddressRef', namespaces=NS)
    if start != None:
        leg_stops.append(locations[start.text].pos)
    else:
        pos = leg.find('.//ns3:LegStart/ns3:GeoPosition', namespaces=NS)
        lon = pos.find('.//ns3:Longitude', namespaces=NS).text
        lat = pos.find('.//ns3:Latitude', namespaces=NS).text
        leg_stops.append((lon, lat))
        
    end = leg.find('.//ns3:LegEnd/ns3:StopPointRef', namespaces=NS)
    if end == None:
        end = leg.find('.//ns3:LegEnd/ns3:AddressRef', namespaces=NS)
    if end != None:
        leg_stops.append(locations[end.text].pos)
    else:
        pos = leg.find('.//ns3:LegEnd/ns3:GeoPosition', namespaces=NS)
        lon = pos.find('.//ns3:Longitude', namespaces=NS).text
        lat = pos.find('.//ns3:Latitude', namespaces=NS).text
        leg_stops.append((lon, lat))

    app.logger.info("Number of stops: " + str(len(leg_stops)))

    travel_expert = leg.find('.//coactive:TravelExpertId', namespaces=NS).text
    transportation_mode = leg.find('.//ns3:IndividualMode', namespaces=NS).text
    if transportation_mode != "others-drive-car":
        return ContinuousLeg(leg_id, start_time, end_time, leg_track, leg_stops, 
            transportation_mode, travel_expert, duration)
    else:
        # RideSharing Leg
        driver = leg.find('.//ns3:OperatorRef', namespaces=NS).text
        vehicle = leg.find('.//ns3:InfoUrl/ns3:Label/ns3:Text', namespaces=NS).text
        passenger = None # TODO Extract it from the OfferItemContext
        return RideSharingLeg(leg_id, start_time, end_time, leg_track, leg_stops, transportation_mode, travel_expert, 
            duration, driver, vehicle, passenger)

def extract_from_oic(offer):
    # TODO Parse defined keys for OfferItemContext
    # TODO Parse composite keys referring to specific TripLeg
    return ""
