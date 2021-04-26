# Offer parser `trias-extractor`

**Version:** 1.0 

**Date:** 13.04.2021

**Authors:** Mario Scrocca (mario.scrocca@cefriel.com)

## Description 

The `trias-extractor` offer parser  is a module of the **Ride2Rail Offer Categorizer** responsible for parsing offers from Trias and for converting them to the _offer cache_ schema enabling  the categorization.

The parsed input format is mainly based on the [Trias specification](https://github.com/VDVde/TRIAS) for a `TripResponse` message but takes also into account: (i) extensions to the specification developed by Shift2Rail IP4 projects, and (ii) the ridesharing offer structure defined by Ride2Rail.

The procedure implemented by the `trias-extractor` is composed of two main phases.

### Phase I: Parsing   

Parsing of data required from the Trias file provided to an intermediate representation using in-memory objects. The procedures to parse the data are implemented in the ***extractor.py*** module. The intermediate object model used to represent the parsed data is defined in the ***model.py*** module. 

The defined model reflects the _offer cache_ schema:
- **Request**: id, start_time, end_time, start_point, end_point, ***offers*** (dictionary of associated *Offer* objects)
- **Offer**: id, trip, bookable_total, complete_total, ***offer_items***  (dictionary of associated *OfferItem* objects)
- **Trip**: id, duration, start_time, end_time, num_interchanges, **legs** (dictionary of associated *TripLeg* objects)
- **OfferItem**: id, name, fares_authority_ref, fares_authority_text, price, leg_ids (list of ids of *TripLeg* objects covered by the *OfferItem* object)
- **TripLeg**: id, start_time, end_time, leg_track, leg_stops, transportation_mode, travel_expert, attributes (dictionary of *OfferItemContext* key-value pairs)
    - **TimedLeg**(TripLeg): line, journey
    - **ContinuousLeg**(TripLeg): duration 
        - **RideSharingLeg**(ContinuousLeg): driver, vehicle

*Location* and its subclasses (*StopPoint*, *Address*) are used to support the processing but are not serialized in the _offer cache_.

The parsing procedure is implemented through the following steps:

1.  Parse the `TripRequest` data associated with the offers described in the Trias `TripResponse` obtaining a `model.Request` object
2.  Parse the `TripResponseContext` associated with the offers described in the Trias `TripResponse` obtaining a list of `model.Location` objects
3.  Parse all the Trias `Trip`s and the associated `TripLeg`s obtaining a set of `model.Trip` objects referencing an ordered list of `model.TripLeg`s
4.  Parse the Trias Meta-`Ticket` associated with the different Trias `Trip`s obtaining a list of `model.Offer` objects referencing the associated `model.Trip` and bound to the `model.Request` object
5.  Parse the Trias `Ticket` associated with each Meta-`Ticket` obtaining a list of `model.OfferItem` associated with a `model.Offer` and with the `model.TripLeg`s covered by the offer item.
6.  Parse the `OfferItemContext` for each Trias `Ticket` obtaining a dictionary of key-value pairs bound to specific `model.TripLeg`s associated to the `model.OfferItem`

**Note on step 6**: If the `OfferItemContext` contains a composite key, the assumption is that it is composed as `oic_key:leg_id` and the parsed value should be associated only with the `model.TripLeg` having the provided `leg_id`. In all the other cases the value parsed is associated to all the `model.TripLeg`s associated with the `model.OfferItem`. The information extracted from the `OfferItemContext` is merged with the `Attribute`s parsed for each `model.TripLeg`.

### Phase II: Writing 

Storing of the data parsed by the `trias-extractor` to the offer cache. A dedicated procedure is defined for in the ***writer.py*** module. The complete serialization is composed of queued commands in a pipeline that is executed as a single write to the _offer cache_.

### Implementation

The `trias-extractor` component is implemented as a _Python_ application using the _Flask_ framework to expose the described procedure as a service. Each Trias file processed by the `trias-extractor` component is mapped to a *Request* object and then serialized in the _offer cache_. The _request_id_ (key to access the data from the cache) is returned in the response as a field in a JSON body.

## Configuration

The following values of parameters can be defined in the configuration file ***config/trias-extractor.conf***.

Section ***cache***: 
- ***host*** - host address of the cache service that should be accessed 
- ***port*** - port number of the cache service that should be accessed 

The  ***config/codes.csv*** can be modified to configure the parsing procedure of the `Attribute`s associated with the different _TripLeg_ nodes and the _offer item context_ associated with the different _Ticket_ nodes (offer items). The file defines the admissible keys (`key` column), the expected range of the values  (`value_min` and `value_max` columns for numeric datatypes) and the datatype (`type` column, admissible values are `string`, `int`, `float`, `date`) to execute a preliminary validation of the value parsed. 

## Usage

Adding Trias requests to a `trias` folder in the repository root, the `load.sh` script can be used to automatically launch the _trias-extractor_ service, the _offer cache_ and parse the files. The _offer cache_ data are persisted in the `./redis-data` folder.

### Local development (debug on)

Running it locally (assumption Redis is running at  `localhost:6379 `)

```bash
$ python3 trias-extractor.py
 * Serving Flask app "trias-extractor" (lazy loading)
 * Environment: development
 * Debug mode: on
 * Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)
 * Restarting with stat
 * Debugger is active!
 * Debugger PIN: 441-842-797
```

Running on Docker (executes both the `trias-extractor` service and a Redis container)

```bash
$ docker-compose build
$ docker-compose up
```

### Production development
Change the `build` section in the docker-compose file to use the `Dockerfile.production` configuration that runs the Flask app on `gunicorn`, remove the `environment` section.
```bash
$ docker-compose build
$ docker-compose up
```
Edit the `Dockerfile.production` file to set a different `gunicorn` configuration.

### Example Request
```bash
$ curl --header 'Content-Type: application/xml' \
       --request POST  \
       --data-binary '@trias/$FILE_NAME' \
         http://localhost:5000/extract
```