import csv
# from flask import current_app as app
from dateutil.parser import parse

OIC_CONFIG_PATH = "config/offer_item_context.csv"
oic_config = {}

with open(OIC_CONFIG_PATH) as fp:
    reader = csv.reader(fp, delimiter=",", quotechar='"')
    next(reader, None)  # skip the headers
    for row in reader:
        oic_config[row[0]] = row

def parse_oic(parsed_oic, offer, offer_item):
    for p_key in parsed_oic.keys():
        value = parsed_oic[p_key]
        if p_key.find(":") != -1:
            key = p_key[:p_key.find(":")]
        else:
            key = p_key
        if key in oic_config:
            # Check if composite key
            # If composite key, assumption is key:leg_id and 
            #   the value is associated to the leg with leg_id
            # Else the value is associated to all the legs associated to the offer item
            leg_ids = offer_item.legs if key == p_key else [p_key.replace(key + ":", "")]

            config = oic_config[key]
            min_value = int(config[1])
            max_value = int(config[2])
            value_type = config[3]

            try: 
                if value_type == "int" or value_type == "float":
                    f_value = float(value)
                    if f_value >= min_value and f_value <= max_value:
                        add_to_offer(offer, key, leg_ids, value)
                elif value_type == "date":
                    if is_date(value):
                        add_to_offer(offer, key, leg_ids, value)
            except ValueError:
                continue

def add_to_offer(offer, key, leg_ids, value):
    legs = offer.trip.legs
    for leg_id in leg_ids:
        leg = legs[leg_id]
        leg.add_to_oic(key, value)
        # app.logger.info("Add {} to {} with value {}".format(key, leg_id, value))

def is_date(string):
    try: 
        parse(string)
        return True
    except ValueError:
        return False
