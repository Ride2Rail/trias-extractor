import sys
import time
import logging
import uuid

from trias_extractor import model, codes
from trias_extractor.exception import ParsingException

from lxml import etree

# logger
logger = logging.getLogger()

# namespaces
NS = {'coactive': 'http://shift2rail.org/project/coactive',
      'ns3': 'http://www.vdv.de/trias',
      'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
      's2r' : 'http://shift2rail.org/project/'}

# Main parsing procedure
def extract_trias(offers):
    parser = etree.XMLParser(ns_clean=True, recover=True, encoding='utf-8')

    try:
        parsed_trias = etree.fromstring(offers, parser=parser)
    except etree.XMLSyntaxError:
        raise ParsingException('Error parsing the Trias structure.')
    
    # TripRequest
    # Generate identifier for the request received
    request_id = str(uuid.uuid4())
    request = model.Request(request_id)
    
    _request = parsed_trias.find('.//s2r:TripRequest', namespaces=NS)
    if _request != None :
        extract_request(_request, request)

    # TripResponseContext
    trip_response_context = parsed_trias.find('.//ns3:TripResponseContext', namespaces=NS)
    locations = {}
    if trip_response_context != None:
        locations = parse_context(trip_response_context)

    # TripResults
    _trip_results = parsed_trias.findall('.//ns3:TripResult', namespaces=NS)

    offers = {}

    # Trip
    for trip_result in _trip_results:
        _trip = trip_result.find('.//ns3:Trip', namespaces=NS)

        # Trip data
        trip = extract_trip(_trip)

        # Trip Legs
        _legs = _trip.findall('.//ns3:TripLeg', namespaces=NS)
        for leg in _legs:
            leg_id = leg.find('ns3:LegId', namespaces=NS).text
            l = None
            _timed = leg.find('ns3:TimedLeg', namespaces=NS)
            if _timed != None:
                l = extract_timed_leg(leg_id, _timed, locations)
                extract_leg_attributes(_timed, l)
            else:
                _continuous = leg.find('ns3:ContinuousLeg', namespaces=NS) 
                if _continuous != None:
                    l = extract_continuous_leg(leg_id, _continuous, locations)
                    extract_leg_attributes(_continuous, l)

            if l != None:
                trip.add_leg(l)
            else:
                raise ParsingException("Not parsable Leg found with LegId " + leg_id)

        # Offer
        _offer_items = trip_result.findall('.//ns3:Ticket', namespaces=NS)
        for metaticket in _offer_items:
            offer_item_id = metaticket.find('ns3:TicketId', namespaces=NS).text
            if offer_item_id == "META":
                # Parse Offer
                offer = extract_offer(metaticket, trip)
                offers[offer.id] = offer
                request.add_offer(offer)
        # Parse Offer Items and associate them to Offers
        for ticket in _offer_items:
                extract_offer_item(ticket, offers)

    return request

def extract_request(_request, request):
    _r_times = _request.findall('.//s2r:RequestedTravelTime', namespaces=NS)
    if _r_times != None:
        for r_time in _r_times:
            mode = r_time.find('s2r:RequestMode', namespaces=NS).text
            datetime = r_time.find('s2r:RequestedTime', namespaces=NS).text
            if mode == "departure":
                request.start_time = datetime
            if mode == "arrival":
                request.end_time = datetime

    _r_d_location = _request.find('s2r:DepartureLocation/s2r:Position', namespaces=NS)
    if _r_d_location != None:
        r_d_lat = float(_r_d_location.find('s2r:Latitude', namespaces=NS).text)
        r_d_long = float(_r_d_location.find('s2r:Longitude', namespaces=NS).text)
        request.start_point = (r_d_long, r_d_lat)
    _r_a_location = _request.find('s2r:ArrivalLocation/s2r:Position', namespaces=NS)
    if _r_a_location != None:
        r_a_lat = float(_r_a_location.find('s2r:Latitude', namespaces=NS).text)
        r_a_long = float(_r_a_location.find('s2r:Longitude', namespaces=NS).text)
        request.end_point = (r_a_long, r_a_lat)

# Add Offer Items to Offers parsing Ticket nodes from TRIAS
def extract_offer_item(ticket, offers):
    offer_item_id = ticket.find('ns3:TicketId', namespaces=NS).text
    if offer_item_id != "META":
        # Mandatory Fields
        name = ticket.find('ns3:TicketName', namespaces=NS).text
        auth_ref = ticket.find('ns3:FaresAuthorityRef', namespaces=NS).text
        auth_text = ticket.find('ns3:FaresAuthorityText', namespaces=NS).text

        # Price and Currency
        _price = ticket.find('ns3:Price', namespaces=NS)
        p = "0"
        if _price != None:
            p = _price.text
        _currency = ticket.find('ns3:Currency', namespaces=NS)
        c = ""
        if _currency != None:
            c = _currency.text
        o_i = model.OfferItem(offer_item_id, name, auth_ref, auth_text, (p, c))

        # Extension
        offer_item_ticket = ticket.find("ns3:Extension[ @xsi:type = 'coactive:OfferItemTicketExtension' ]", namespaces=NS)
        offer_id = offer_item_ticket.find('coactive:OfferId', namespaces=NS).text
        o = offers[offer_id]
        if (o == None):
            raise ParsingException("No associated offer found for offer item {}".format(offer_item_id))
        o.add_offer_item(o_i)

        _leg_ids = offer_item_ticket.findall('.//coactive:TravelEpisodeId', namespaces=NS)
        for id in _leg_ids:
            o_i.leg_ids.append(id.text)

        # Parse Offer Item Context
        extract_from_oic(offer_item_ticket, o, o_i)

# Returns an Offer parsing a META-Ticket
def extract_offer(ticket, trip):
    offer = ticket.find("ns3:Extension[ @xsi:type = 'coactive:MetaTicketExtension' ]", namespaces=NS)
    offer_id = offer.find('coactive:OfferId', namespaces=NS).text

    prices = offer.find('coactive:Prices', namespaces=NS)
    _bookable_total = prices.find('coactive:BookableTotal', namespaces=NS)
    bt_p = _bookable_total.find('ns3:Price', namespaces=NS).text
    bt_c = _bookable_total.find('ns3:Currency', namespaces=NS).text
    bookable_total = (bt_p, bt_c)

    _complete_total = prices.find('coactive:CompleteTotal', namespaces=NS)
    ct_p = _complete_total.find('ns3:Price', namespaces=NS).text
    ct_c = _complete_total.find('ns3:Currency', namespaces=NS).text
    complete_total = (ct_p, ct_c)

    return model.Offer(offer_id, trip, bookable_total, complete_total)

# Returns a dictionary of id:Location parsing a TripResponseContext node
def parse_context(context):
    locations = {}
    _locations = context.findall('.//ns3:Location', namespaces=NS)
    for location in _locations:
        name = None          
        _name = location.find('ns3:LocationName/ns3:Text', namespaces=NS)
        if _name != None:
            name = _name.text
        pos = location.find('ns3:GeoPosition', namespaces=NS)
        loc_lon = pos.find('ns3:Longitude', namespaces=NS).text
        loc_lat = pos.find('ns3:Latitude', namespaces=NS).text

        # StopPoint
        sp = location.find('ns3:StopPoint', namespaces=NS)
        if sp != None:
            id = sp.find('ns3:StopPointRef', namespaces=NS).text
            stop_name = sp.find('ns3:StopPointName/ns3:Text', namespaces=NS).text
            l = model.StopPoint(id, name, loc_lon, loc_lat, stop_name)
            _codes = sp.findall('.//ns3:PrivateCode', namespaces=NS)
            for code in _codes:
                system = code.find('ns3:System', namespaces=NS).text
                value = code.find('ns3:Value', namespaces=NS).text
                l.add_code(system, value)
            locations[id] = l
        # Address
        ad = location.find('ns3:Address', namespaces=NS)
        if ad != None :           
            id = ad.find('ns3:AddressCode', namespaces=NS).text
            a_name = ad.find('ns3:AddressName/ns3:Text', namespaces=NS).text
            l = model.Address(id, name, loc_lon, loc_lat, a_name)
            locations[id] = l
    
    return locations

# Parses mandatory data about a Trip
def extract_trip(trip):
    trip_id = trip.find('ns3:TripId', namespaces=NS).text
    duration = trip.find('ns3:Duration', namespaces=NS).text
    start_time = trip.find('ns3:StartTime', namespaces=NS).text
    end_time = trip.find('ns3:EndTime', namespaces=NS).text
    num_interchanges = trip.find('ns3:Interchanges', namespaces=NS).text

    return model.Trip(trip_id, duration, start_time, end_time, num_interchanges)

# Parses a TimedLeg
def extract_timed_leg(leg_id, leg, spoints):
    start_time = leg.find('ns3:LegBoard/ns3:ServiceDeparture/ns3:TimetabledTime', namespaces=NS).text
    end_time = leg.find('ns3:LegAlight/ns3:ServiceArrival/ns3:TimetabledTime', namespaces=NS).text

    leg_track = extract_leg_track(leg)

    leg_stops = []
    board = leg.find('ns3:LegBoard/ns3:StopPointRef', namespaces=NS).text
    if board in spoints:
        leg_stops.append(spoints[board].pos)
    else:
        logger.warning("Stop point position not found for LegBoard in TripResponseContext. StopPointRef: {}".format(board))
    _intermediates = leg.findall('.//ns3:LegIntermediates', namespaces=NS)
    if _intermediates != None:
        for li in _intermediates:
            li_ref = li.find('ns3:StopPointRef', namespaces=NS).text
            if li_ref in spoints:
                leg_stops.append(spoints[li_ref].pos)
            else:
                logger.warning("Stop point position not found for IntermediateLeg in TripResponseContext. StopPointRef: {}".format(li_ref))
    alight = leg.find('ns3:LegAlight/ns3:StopPointRef', namespaces=NS).text
    if alight in spoints:
        leg_stops.append(spoints[alight].pos)
    else:
        logger.warning("Stop point position not found for LegAlight in TripResponseContext. StopPointRef: {}".format(alight))

    service = leg.find('ns3:Service', namespaces=NS)
    journey = service.find('ns3:JourneyRef', namespaces=NS).text
    line = service.find('ns3:ServiceSection/ns3:LineRef', namespaces=NS).text
    transportation_mode = service.find('ns3:ServiceSection/ns3:Mode/ns3:PtMode', namespaces=NS).text

    travel_expert = leg.find('.//coactive:TravelExpertId', namespaces=NS).text
    
    return model.TimedLeg(leg_id, start_time, end_time, leg_track, leg_stops, 
        transportation_mode, travel_expert, line, journey)

# Extracts the leg track (list of pairs of coordinates) from a Projection node
def extract_leg_track(leg):
    _track = leg.find('ns3:LegTrack/ns3:TrackSection/ns3:Projection', namespaces=NS)
    if _track != None:
        track = []
        for pos in list(_track):
            p_lon = pos.find('ns3:Longitude', namespaces=NS).text
            p_lat = pos.find('ns3:Latitude', namespaces=NS).text
            track.append((float(p_lon), float(p_lat)))
        return track
    return None

# Parses and returns a ContinuousLeg/RideSharingLeg
def extract_continuous_leg(leg_id, leg, locations):
    start_time = leg.find('ns3:TimeWindowStart', namespaces=NS).text
    end_time = leg.find('ns3:TimeWindowEnd', namespaces=NS).text
    duration = leg.find('ns3:Duration', namespaces=NS).text
    length = leg.find('ns3:Length', namespaces=NS)
    if length != None:
        length = int(length.text)

    leg_track = extract_leg_track(leg)
    
    leg_stops = []
    start = leg.find('ns3:LegStart/ns3:StopPointRef', namespaces=NS)
    if start == None:
        start = leg.find('ns3:LegStart/ns3:AddressRef', namespaces=NS)
    if start != None and start.text in locations:
        leg_stops.append(locations[start.text].pos)
    else:
        pos = leg.find('ns3:LegStart/ns3:GeoPosition', namespaces=NS)
        if pos != None:
            lon = pos.find('ns3:Longitude', namespaces=NS).text
            lat = pos.find('ns3:Latitude', namespaces=NS).text
            leg_stops.append((float(lon), float(lat)))
        else:
            logger.warning("LegStart position not found. ContinuousLeg Id: {}".format(leg_id))
        
    end = leg.find('ns3:LegEnd/ns3:StopPointRef', namespaces=NS)
    if end == None:
        end = leg.find('ns3:LegEnd/ns3:AddressRef', namespaces=NS)
    if end != None and end.text in locations:
        leg_stops.append(locations[end.text].pos)
    else:
        pos = leg.find('ns3:LegEnd/ns3:GeoPosition', namespaces=NS)
        if pos != None:
            lon = pos.find('ns3:Longitude', namespaces=NS).text
            lat = pos.find('ns3:Latitude', namespaces=NS).text
            leg_stops.append((float(lon), float(lat)))
        else:
            logger.warning("LegEnd position not found. ContinuousLeg Id: {}".format(leg_id))

    travel_expert = leg.find('.//coactive:TravelExpertId', namespaces=NS).text
    transportation_mode = leg.find('ns3:Service/ns3:IndividualMode', namespaces=NS).text
    if transportation_mode != "others-drive-car":
        return model.ContinuousLeg(leg_id, start_time, end_time, leg_track, leg_stops, 
            transportation_mode, travel_expert, duration, length)
    else:
        # RideSharing Leg
        sh_service = leg.find('ns3:Service/ns3:SharingService', namespaces=NS)
        driver = {}
        driver['id'] = sh_service.find('ns3:OperatorRef', namespaces=NS).text
        driver['text'] = sh_service.find('ns3:Name', namespaces=NS).text
        vehicle = {}
        vehicle['id'] = sh_service.find('ns3:InfoUrl/ns3:Url', namespaces=NS).text
        vehicle['text'] = sh_service.find('ns3:InfoUrl/ns3:Label/ns3:Text', namespaces=NS).text
        # passenger info are extracted from OIC
        return model.RideSharingLeg(leg_id, start_time, end_time, leg_track, leg_stops, transportation_mode, travel_expert, 
            duration, length, driver, vehicle)

# Extract additional data from the Leg Attributes
def extract_leg_attributes(_leg, leg):
    attributes = _leg.findall(".//ns3:Attribute", namespaces=NS)
    _la = {}
    for _attribute in attributes:
        key = _attribute.find("ns3:Code", namespaces=NS)
        value = _attribute.find("ns3:Text/ns3:Text", namespaces=NS)
        if key != None and value != None:
            _la[key.text] = value.text

    codes.parse_attributes(_la, leg)

# Extract additional data from the OfferItemContext
def extract_from_oic(offer_item_ticket, offer, offer_item):
    oic_nodes = offer_item_ticket.findall(".//coactive:OfferItemContext", namespaces=NS)
    _oic = {}
    for _oic_node in oic_nodes:
        key = _oic_node.find("coactive:Code", namespaces=NS)
        value = _oic_node.find("coactive:Value", namespaces=NS)
        if key != None and value != None:
            _oic[key.text] = value.text

    codes.parse_oic(_oic, offer, offer_item)
