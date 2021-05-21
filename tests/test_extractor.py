import os
import pytest

from lxml import etree
import geojson
from trias_extractor import extractor, model

@pytest.fixture
def parsed_request():
    local_folder = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(local_folder, 'test_example.xml')
    offers = open(config_path, "rb")

    parsed_request = extractor.extract_trias(offers.read())
    return parsed_request

def test_request(parsed_request):
    assert parsed_request.start_time == '2020-11-10T07:00:00.000Z'
    assert parsed_request.end_time == '2020-11-10T08:00:00.000Z'
    assert parsed_request.start_point == (-3.671161, -3.663255)
    assert parsed_request.end_point == (-3.792386, -3.677984)

    parsed_offers = parsed_request.offers
    assert len(parsed_offers) == 1
    assert parsed_offers['2a8e0e6c-285d-4c8c-b98f-rs1'] != None

def test_offer(parsed_request): 
    o = parsed_request.offers['2a8e0e6c-285d-4c8c-b98f-rs1']
    assert o.id == '2a8e0e6c-285d-4c8c-b98f-rs1'
    assert o.bookable_total['value'] == '550'
    assert o.bookable_total['currency'] == 'EUR'
    assert o.complete_total['value'] == '710'
    assert o.complete_total['currency'] == 'EUR'

    assert len(o.offer_items.keys()) == 2
    assert o.offer_items['multimodal-offer-item'] != None
    assert o.offer_items['ridesharing-offer-item'] != None

def test_trip(parsed_request):
    o = parsed_request.offers['2a8e0e6c-285d-4c8c-b98f-rs1']
    t = o.trip
    assert t.id == '38e36a2a-b515-4f7f-a1be-rs1'
    assert t.duration == 'PT42M30S'
    assert t.start_time == '2020-11-10T07:08:30.000Z'
    assert t.end_time == '2020-11-10T07:51:00.000Z'
    assert t.num_interchanges == '1'

    assert len(t.ordered_legs_ids) == 4
    assert t.ordered_legs_ids[0] == 'continuous-leg-1'
    assert t.ordered_legs_ids[1] == 'timed-leg-2'
    assert t.ordered_legs_ids[2] == 'continuous-leg-3'
    assert t.ordered_legs_ids[3] == 'ridesharing-leg-4'

    assert len(t.legs.keys()) == 4
    assert t.legs['continuous-leg-1'] != None
    assert t.legs['timed-leg-2'] != None
    assert t.legs['continuous-leg-3'] != None
    assert t.legs['ridesharing-leg-4'] != None
    
def test_offer_item_mm(parsed_request):
    o = parsed_request.offers['2a8e0e6c-285d-4c8c-b98f-rs1']
    mm_oi = o.offer_items['multimodal-offer-item']

    assert mm_oi.id == 'multimodal-offer-item'
    assert mm_oi.price['value'] == '160'
    assert mm_oi.price['currency'] == 'EUR'
    assert mm_oi.name == 'Standard Ticket'
    assert mm_oi.fares_authority_ref == 'TMB'
    assert mm_oi.fares_authority_text == 'TMB planner for Barcelona metropolitan transport'
    assert 'continuous-leg-1' in mm_oi.leg_ids
    assert 'timed-leg-2' in mm_oi.leg_ids
    assert 'continuous-leg-3' in mm_oi.leg_ids

def test_offer_item_rs(parsed_request):
    o = parsed_request.offers['2a8e0e6c-285d-4c8c-b98f-rs1']
    rs_oi = o.offer_items['ridesharing-offer-item']

    assert rs_oi.id == 'ridesharing-offer-item'
    assert rs_oi.price['value'] == '550'
    assert rs_oi.price['currency'] == 'EUR'
    assert rs_oi.name == 'RideSharing Ticket'
    assert rs_oi.fares_authority_ref == 'R2R_CBTSP'
    assert rs_oi.fares_authority_text == 'R2R Crowd-based Travel Expert'
    assert 'ridesharing-leg-4' in rs_oi.leg_ids

def test_trip_leg_1(parsed_request):
    o = parsed_request.offers['2a8e0e6c-285d-4c8c-b98f-rs1']
    tl = o.trip.legs['continuous-leg-1']
    assert isinstance(tl, (model.ContinuousLeg, model.TripLeg))
    
    assert tl.id == 'continuous-leg-1'
    assert tl.start_time == '2020-11-10T07:08:30.000Z'
    assert tl.end_time == '2020-11-10T07:17:09.000Z'
    assert tl.duration == 'PT8M39S'
    assert tl.length == 1023
    assert tl.transportation_mode == 'walk'
    assert tl.leg_stops[0] == (-3.663254737854004, 40.38188171386719)
    assert tl.leg_stops[1] == (-3.6711626052856445, 40.38353729248047)
    assert tl.leg_track == None
    assert tl.travel_expert == 'TMB'
    a = tl.attributes
    assert len(a.keys()) == 1
    assert a['last_minute_changes'] == '0.34'

def test_trip_leg_2(parsed_request):
    o = parsed_request.offers['2a8e0e6c-285d-4c8c-b98f-rs1']
    tl = o.trip.legs['timed-leg-2']
    assert isinstance(tl, (model.TimedLeg, model.TripLeg))
    
    assert tl.id == 'timed-leg-2'
    assert tl.start_time == '2020-11-10T07:17:10.000Z'
    assert tl.end_time == '2020-11-10T07:23:47.000Z'
    assert tl.duration == 'PT6M37S'
    assert tl.transportation_mode == 'bus'

    # Test with intermediate stop as Address location
    assert len(tl.leg_stops) == 3
    assert tl.leg_stops[0] == (-3.6711626052856445, 40.38353729248047)
    assert tl.leg_stops[1] == (-3.67111362, 40.383737)
    assert tl.leg_stops[2] == (-3.677884578704834, 40.3937873840332)

    assert len(tl.leg_track) == 2
    assert tl.leg_track[0] == (-3.671162, 40.383537)
    assert tl.leg_track[1] == (-3.677884, 40.393787)
    
    assert tl.travel_expert == 'TMB'

    assert tl.line == '102'
    assert tl.journey == 'journey_1_102'

    a = tl.attributes
    assert len(a.keys()) == 3
    assert a['last_minute_changes'] == '0.34'
    assert a['cleanliness'] == '2.2'
    assert a['user_feedback'] == '4.13'

def test_trip_leg_3(parsed_request):
    o = parsed_request.offers['2a8e0e6c-285d-4c8c-b98f-rs1']
    tl = o.trip.legs['continuous-leg-3']
    assert isinstance(tl, (model.ContinuousLeg, model.TripLeg))
    # ContinuousLeg parsing already tested

def test_trip_leg_4(parsed_request):
    o = parsed_request.offers['2a8e0e6c-285d-4c8c-b98f-rs1']
    tl = o.trip.legs['ridesharing-leg-4']
    assert isinstance(tl, (model.RideSharingLeg, model.ContinuousLeg, model.TripLeg))
    
    assert tl.id == 'ridesharing-leg-4'
    assert tl.start_time == '2020-11-10T07:30:00.000Z'
    assert tl.end_time == '2020-11-10T07:51:00.000Z'
    assert tl.duration == 'PT21M'
    assert tl.transportation_mode == 'others-drive-car'
    assert tl.leg_stops[0] == (-3.677985906600952, 40.395389556884766)
    assert tl.leg_stops[1] == (-3.7923872470855713, 40.29673385620117)
    assert tl.driver['id'] == 'RSDriver_1'
    assert tl.driver['text'] == 'Driver_Joe1'
    assert tl.vehicle['id'] =='https://en.wikipedia.org/wiki/BMW_X5_(F15)#X5_xDrive40e'
    assert tl.vehicle['text'] =='BMW_X5_xDrive40e'
    assert tl.travel_expert == 'r2r_cbtsp'
    a = tl.attributes
    assert len(a.keys()) == 1
    assert a['passenger_ref'] == 'passenger_id_1'
