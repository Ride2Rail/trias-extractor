import os
import pytest

from lxml import etree
import geojson
from trias_extractor import extractor, model, writer

from unittest.mock import Mock, call

@pytest.fixture
def parsed_request():
    local_folder = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(local_folder, 'test_example.xml')
    offers = open(config_path, "rb")
    parsed_request = extractor.extract_trias(offers.read())
    return parsed_request

@pytest.fixture
def pipe(parsed_request):
    pipe = Mock()
    writer.request_to_cache(parsed_request, pipe)
    return pipe

def test_request(parsed_request, pipe):  
    prefix = parsed_request.id
    pipe.set.assert_any_call('{}:user_id'.format(prefix), 'test-user-ID')
    pipe.set.assert_any_call('{}:traveller_id'.format(prefix), 'test-traveller-ID')
    pipe.set.assert_any_call('{}:start_time'.format(prefix), '2020-11-10T07:00:00.000Z')
    pipe.set.assert_any_call('{}:end_time'.format(prefix), '2020-11-10T08:00:00.000Z')
    pipe.set.assert_any_call('{}:start_point'.format(prefix), geojson.dumps(geojson.Point((-3.671161, -3.663255))))
    pipe.set.assert_any_call('{}:end_point'.format(prefix), geojson.dumps(geojson.Point((-3.792386, -3.677984))))

    pipe.set.assert_any_call('{}:cycling_dist_to_stop'.format(prefix), 5)
    pipe.set.assert_any_call('{}:walking_dist_to_stop'.format(prefix), 10)
    pipe.set.assert_any_call('{}:walking_speed'.format(prefix), 'slow')
    pipe.set.assert_any_call('{}:cycling_speed'.format(prefix), 'medium')
    pipe.set.assert_any_call('{}:driving_speed'.format(prefix), 'medium')
    pipe.set.assert_any_call('{}:max_transfers'.format(prefix), 2)
    pipe.set.assert_any_call('{}:expected_duration'.format(prefix), 2)
    pipe.set.assert_any_call('{}:via_locations'.format(prefix), geojson.dumps(geojson.LineString([(-9.222798, 38.745818),(-9.197911, 38.746093), (-9.174333, 38.750229)])))

    pipe.lpush.assert_any_call('{}:offers'.format(prefix), '2a8e0e6c-285d-4c8c-b98f-rs1')

def test_offer(parsed_request, pipe):    
    prefix = "{}:{}".format(parsed_request.id, '2a8e0e6c-285d-4c8c-b98f-rs1')
    o = parsed_request.offers['2a8e0e6c-285d-4c8c-b98f-rs1']
    pipe.hmset.assert_any_call('{}:bookable_total'.format(prefix), o.bookable_total)
    pipe.hmset.assert_any_call('{}:complete_total'.format(prefix), o.complete_total)

    calls = [call('{}:legs'.format(prefix), 'continuous-leg-1'), call('{}:legs'.format(prefix), 'timed-leg-2'), call('{}:legs'.format(prefix), 'continuous-leg-3'), call('{}:legs'.format(prefix), 'ridesharing-leg-4')]
    # Check legs are added in the correct order
    pipe.lpush.assert_has_calls(calls, any_order=False)
    
    pipe.set.assert_any_call('{}:duration'.format(prefix), 'PT42M30S')
    pipe.set.assert_any_call('{}:start_time'.format(prefix), '2020-11-10T07:08:30.000Z')
    pipe.set.assert_any_call('{}:end_time'.format(prefix), '2020-11-10T07:51:00.000Z')
    pipe.set.assert_any_call('{}:num_interchanges'.format(prefix), 1)
    pipe.set.assert_any_call('{}:length'.format(prefix), 24677)

    pipe.lpush.assert_any_call('{}:offer_items'.format(prefix), 
        'multimodal-offer-item', 'ridesharing-offer-item')
    
def test_offer_item_mm(parsed_request, pipe):
    prefix = "{}:{}:{}".format(parsed_request.id, 
        '2a8e0e6c-285d-4c8c-b98f-rs1', 'multimodal-offer-item')
    o = parsed_request.offers['2a8e0e6c-285d-4c8c-b98f-rs1']
    mm_oi = o.offer_items['multimodal-offer-item']
    pipe.hmset.assert_any_call('{}:price'.format(prefix), mm_oi.price)

    pipe.set.assert_any_call('{}:name'.format(prefix), 'Standard Ticket')
    pipe.set.assert_any_call('{}:fares_authority_ref'.format(prefix), 'TMB')
    pipe.set.assert_any_call('{}:fares_authority_text'.format(prefix), 'TMB planner for Barcelona metropolitan transport')

    pipe.lpush.assert_any_call('{}:legs'.format(prefix), 
        'continuous-leg-1', 'timed-leg-2', 'continuous-leg-3')

def test_offer_item_rs(parsed_request, pipe):
    prefix = "{}:{}:{}".format(parsed_request.id, 
        '2a8e0e6c-285d-4c8c-b98f-rs1', 'ridesharing-offer-item')
    o = parsed_request.offers['2a8e0e6c-285d-4c8c-b98f-rs1']
    rs_oi = o.offer_items['ridesharing-offer-item']
    pipe.hmset.assert_any_call('{}:price'.format(prefix), rs_oi.price)

    pipe.set.assert_any_call('{}:name'.format(prefix), 'RideSharing Ticket')
    pipe.set.assert_any_call('{}:fares_authority_ref'.format(prefix), 'R2R_CBTSP')
    pipe.set.assert_any_call('{}:fares_authority_text'.format(prefix), 'R2R Crowd-based Travel Expert')

    pipe.lpush.assert_any_call('{}:legs'.format(prefix), 
        'ridesharing-leg-4')

def test_trip_leg_1(parsed_request, pipe):
    prefix = "{}:{}:{}".format(parsed_request.id, 
        '2a8e0e6c-285d-4c8c-b98f-rs1', 'continuous-leg-1')
    o = parsed_request.offers['2a8e0e6c-285d-4c8c-b98f-rs1']
    tl = o.trip.legs['continuous-leg-1']

    pipe.set.assert_any_call('{}:leg_type'.format(prefix), 'continuous')
    pipe.set.assert_any_call('{}:start_time'.format(prefix), '2020-11-10T07:08:30.000Z')
    pipe.set.assert_any_call('{}:end_time'.format(prefix), '2020-11-10T07:17:09.000Z')
    pipe.set.assert_any_call('{}:duration'.format(prefix), 'PT8M39S')
    pipe.set.assert_any_call('{}:length'.format(prefix), 1023)
    pipe.set.assert_any_call('{}:transportation_mode'.format(prefix), 'walk')
    pipe.set.assert_any_call('{}:leg_stops'.format(prefix), geojson.dumps(geojson.LineString([(-3.663254737854004, 40.38188171386719),(-3.6711626052856445, 40.38353729248047)])))
    pipe.set.assert_any_call('{}:travel_expert'.format(prefix), 'TMB')

    pipe.set.assert_any_call('{}:last_minute_changes'.format(prefix), '0.34')

def test_trip_leg_2(parsed_request, pipe):
    prefix = "{}:{}:{}".format(parsed_request.id, 
        '2a8e0e6c-285d-4c8c-b98f-rs1', 'timed-leg-2')
    o = parsed_request.offers['2a8e0e6c-285d-4c8c-b98f-rs1']
    tl = o.trip.legs['timed-leg-2']

    pipe.set.assert_any_call('{}:leg_type'.format(prefix), 'timed')
    pipe.set.assert_any_call('{}:start_time'.format(prefix), '2020-11-10T07:17:10.000Z')
    pipe.set.assert_any_call('{}:end_time'.format(prefix), '2020-11-10T07:23:47.000Z')
    pipe.set.assert_any_call('{}:duration'.format(prefix), 'PT6M37S')
    pipe.set.assert_any_call('{}:length'.format(prefix), 2042)
    pipe.set.assert_any_call('{}:transportation_mode'.format(prefix), 'bus')
    pipe.set.assert_any_call('{}:leg_stops'.format(prefix), geojson.dumps(geojson.LineString([(-3.6711626052856445, 40.38353729248047),(-3.67111362, 40.383737),(-3.677884578704834, 40.3937873840332)])))
    pipe.set.assert_any_call('{}:leg_track'.format(prefix), geojson.dumps(geojson.LineString([(-3.671162, 40.383537),(-3.677884, 40.393787)])))
    pipe.set.assert_any_call('{}:travel_expert'.format(prefix), 'TMB')

    pipe.set.assert_any_call('{}:line'.format(prefix), '102')
    pipe.set.assert_any_call('{}:journey'.format(prefix), 'journey_1_102')

    pipe.set.assert_any_call('{}:last_minute_changes'.format(prefix), '0.34')
    pipe.set.assert_any_call('{}:cleanliness'.format(prefix), '2.2')
    pipe.set.assert_any_call('{}:user_feedback'.format(prefix), '4.13')

def test_trip_leg_3(parsed_request, pipe):
    prefix = "{}:{}:{}".format(parsed_request.id, 
        '2a8e0e6c-285d-4c8c-b98f-rs1', 'continuous-leg-3')

    pipe.set.assert_any_call('{}:leg_type'.format(prefix), 'continuous')
    # ContinuousLeg writing already tested

def test_trip_leg_4(parsed_request, pipe):
    prefix = "{}:{}:{}".format(parsed_request.id, 
        '2a8e0e6c-285d-4c8c-b98f-rs1', 'ridesharing-leg-4')
    o = parsed_request.offers['2a8e0e6c-285d-4c8c-b98f-rs1']
    tl = o.trip.legs['ridesharing-leg-4']

    pipe.set.assert_any_call('{}:leg_type'.format(prefix), 'ridesharing')
    pipe.set.assert_any_call('{}:start_time'.format(prefix), '2020-11-10T07:30:00.000Z')
    pipe.set.assert_any_call('{}:end_time'.format(prefix), '2020-11-10T07:51:00.000Z')
    pipe.set.assert_any_call('{}:duration'.format(prefix), 'PT21M')
    pipe.set.assert_any_call('{}:length'.format(prefix), 21362)
    pipe.set.assert_any_call('{}:transportation_mode'.format(prefix), 'others-drive-car')
    pipe.set.assert_any_call('{}:leg_stops'.format(prefix), geojson.dumps(geojson.LineString([(-3.677985906600952, 40.395389556884766),(-3.7923872470855713, 40.29673385620117)])))
    pipe.set.assert_any_call('{}:travel_expert'.format(prefix), 'r2r_cbtsp')

    pipe.hmset.assert_any_call('{}:driver'.format(prefix), tl.driver)
    pipe.hmset.assert_any_call('{}:vehicle'.format(prefix), tl.vehicle)
    pipe.set.assert_any_call('{}:passenger_ref'.format(prefix), 'passenger_id_1')