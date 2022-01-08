import json
import os
import random
import time
import requests
from requests.exceptions import ConnectTimeout

from botocore.exceptions import ClientError

from aws_utils import LambdaClient, S3Client, SnsClient


ALERT_NAME = "PETROLWATCH"
ALERT_SUBJECT = "PETROL WATCH - Price increase detected!"
CENTRE_LAT = float(os.environ['CENTRE_LAT'])
CENTRE_LNG = float(os.environ['CENTRE_LNG'])
MIN_COORD_DIST = float(os.environ['MIN_COORD_DIST'])
MAX_COORD_DIST = float(os.environ['MAX_COORD_DIST'])
PETROL_ALERT_TOPIC = os.environ['PETROL_ALERT_TOPIC']
PETROL_TYPE = 'E10'
PRICES_BUCKET = os.environ['PRICES_BUCKET']
URL_BASE = 'https://petrolspy.com.au/webservice-1/station/box'
URL_HEADERS = {
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Connection': 'keep-alive',
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/86.0.4240.111 Safari/537.36'
    ),
}
URL_QUERY_TIMEOUT = int(os.environ['URL_QUERY_TIMEOUT'])

lambda_client = LambdaClient()
s3 = S3Client()
sns = SnsClient()


def check_prices(centre_lat, centre_lng, context, override_url=None):
    coords = round(centre_lat, 3), round(centre_lng, 3)
    ne_lat, ne_lng, sw_lat, sw_lng = get_boundary(*coords)
    try:
        raw_data = get_raw_data(ne_lat, ne_lng, sw_lat, sw_lng, override_url)
    except ConnectTimeout:
        force_cold_start(context)
        raise
    new_prices = get_prices(raw_data)
    prices_key = translate_coords_to_key(*coords)
    old_prices = get_last_prices(prices_key)
    if old_prices is not None:
        compare_prices(old_prices, new_prices)
    s3.put_object(PRICES_BUCKET, prices_key, json.dumps(new_prices).encode())


def compare_prices(old_prices, new_prices):
    increases = 0
    overlap = 0
    example = None
    comparisons = {}
    for station_id, new_values in new_prices.items():
        if (old_values := old_prices.get(station_id)) is not None:
            overlap += 1
            old_price = old_values['price']
            new_price = new_values['price']
            if old_price != new_price:
                comparisons[new_values['name']] = {
                    'old': old_price,
                    'new': new_price,
                }
                # Only count big jumps
                if new_price > old_price + 20:
                    increases += 1
                    example = station_id
    print(f"{overlap} stations are common between old and new data,"
          f" resulting in the following updates: {json.dumps(comparisons)}")
    if example:
        new_values = new_prices[example]
        message = (f"{new_values['name']} from {old_prices[example]['price']}"
                   f" to {new_values['price']} and {increases - 1} others")
        sns.publish(PETROL_ALERT_TOPIC, message, ALERT_NAME, ALERT_SUBJECT)


def force_cold_start(context):
    current_memory_limit = int(context.memory_limit_in_mb)
    current_name = context.function_name
    if current_memory_limit == 64:
        new_memory_limit = 128
    else:
        new_memory_limit = current_memory_limit - 64
    print("Forcing the next invocation to be a cold start.")
    lambda_client.update_function_configuration(
        name=current_name,
        MemorySize=new_memory_limit
    )
    lambda_client.update_function_configuration(
        name=current_name,
        MemorySize=current_memory_limit
    )


def get_boundary(centre_lat, centre_lng):
    ne_lat = wobble(centre_lat + random.uniform(MIN_COORD_DIST, MAX_COORD_DIST))
    ne_lng = wobble(centre_lng + random.uniform(MIN_COORD_DIST, MAX_COORD_DIST))
    sw_lat = wobble(centre_lat - random.uniform(MIN_COORD_DIST, MAX_COORD_DIST))
    sw_lng = wobble(centre_lng - random.uniform(MIN_COORD_DIST, MAX_COORD_DIST))
    return ne_lat, ne_lng, sw_lat, sw_lng


def get_last_prices(prices_key):
    try:
        streaming_body = s3.get_object(PRICES_BUCKET, prices_key)
    except ClientError as error:
        print(json.dumps(error.response, default=str))
        print(f"These are probably new coordinates")
        return None
    last_prices = json.load(streaming_body)
    return last_prices


def get_raw_data(ne_lat, ne_lng, sw_lat, sw_lng, override_url=None):
    now = timestamp_ms()
    ajax_ = now - int(random.gauss(1500, 200))
    url = override_url or f'{URL_BASE}?neLat={ne_lat}&neLng={ne_lng}&swLat={sw_lat}&swLng={sw_lng}&ts={now}&_={ajax_}'
    print(f"Querying {url}")
    try:
        response = requests.get(url, headers=URL_HEADERS, timeout=URL_QUERY_TIMEOUT)
    except ConnectTimeout:
        print("Connection timed out")
        raise
    print(f"{response.status_code} {response.reason}")
    response.raise_for_status()
    response_json = response.json()
    return response_json


def get_prices(raw_data):
    station_list = raw_data['message']['list']
    print(f"Found data on {len(station_list)} stations.")
    prices = {
        station['id']: {
            'name': station['name'],
            'price': e10['amount'],
        }
        for station in station_list
        if (e10 := station['prices'].get('E10')) is not None
    }
    assert prices, "No E10 prices found."
    return prices


def timestamp_ms():
    return int(time.time()*1000)


def translate_coords_to_key(centre_lat, centre_lng):
    return f'{centre_lat}.{centre_lng}.json'


def wobble(coord):
    return round(coord + (random.random() - 0.5)/1000, 14)


def lambda_handler(event, context):
    print('Event Received: {}'.format(json.dumps(event)))
    override_url = event.get('url')
    check_prices(CENTRE_LAT, CENTRE_LNG, context, override_url)
