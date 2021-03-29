#!/bin/bash

# Start Cache and Trias-Extractor service
docker-compose up -d

# Check if everything is up and running
sleep 5
while [[ "$(curl -s -o /dev/null -w ''%{http_code}'' http://127.0.0.1:5000/check)" != "200" ]]; do
	sleep 2
done

# Load to the Cache all the TRIAS files in the ./trias folder
for test in `ls -d -v ./trias/*` ; do
	TEST_NAME="$(basename "$test")"
	echo $TEST_NAME
	DATA="@trias/$TEST_NAME"
	curl --location --request POST 'http://127.0.0.1:5000/extract' --header 'Content-Type: application/xml' --data-binary $DATA >> ./response-log.txt
	echo "" >> ./response-log.txt
done

# Ensure the entire cache is dumped in the .rdb file 
sleep 5
docker exec -i trias-extractor_cache_1 redis-cli SAVE

# Stop Cache and Trias-Extractor service
docker-compose down