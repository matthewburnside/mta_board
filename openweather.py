from adafruit_datetime import datetime
from secrets import secrets

API = 'https://api.openweathermap.org/data/2.5/weather?' \
    'lat=%s&lon=%s&appid=%s&units=imperial'

MAX_ENTRIES = 3


def weather(network, coords):
    query = API % (coords['lat'], coords['lon'], secrets['weather_key'])
    resp = network.fetch_data(query, json_path=([]))

    icon = resp['weather'][0]['icon']
    temp = round(resp['main']['temp'])
    print("icon: %s, temp: %s" % (icon, temp))
    return (icon, temp)



'''

{'base': 'stations',
 'clouds': {'all': 20},
 'cod': 200,
 'coord': {'lat': 40.7094, 'lon': -73.9049},
 'dt': 1690288353,
 'id': 5112738,
 'main': {'feels_like': 76.96,
          'humidity': 73,
          'pressure': 1019,
          'temp': 76.21,
          'temp_max': 79.9,
          'temp_min': 72.43},
 'name': 'City Line',
 'sys': {'country': 'US',
         'id': 2002197,
         'sunrise': 1690278324,
         'sunset': 1690330714,
         'type': 2},
 'timezone': -14400,
 'visibility': 10000,
 'weather': [{'description': 'few clouds',
              'icon': '02d',
              'id': 801,
              'main': 'Clouds'}],
 'wind': {'deg': 220, 'speed': 5.75}}

'''
