import displayio
import gc
import microcontroller
import time
import traceback
from adafruit_bitmap_font import bitmap_font
from adafruit_datetime import datetime
from adafruit_display_text import label
from adafruit_display_shapes import circle, line
from adafruit_matrixportal.matrix import Matrix
from adafruit_matrixportal.network import Network
from board import NEOPIXEL
from secrets import secrets


REFRESH_RATE       = 10    # interval (s) between refreshing the counts
TRAIN_LIMIT        = 0     # no rate limit on the train API
BUS_LIMIT          = 45    # refresh the bus every 45s (30s rate limit)
TIME_LIMIT         = 600   # refresh the clock every 10 mins
WEATHER_LIMIT      = 60    # refresh the weather every 1 min
RESET_LIMIT        = 7200  # reset the microcontroller every 2 hrs
MAX_T              = 3     # count of arrivals to display

WHITE  = 0x666666
ORANGE = 0xff6319
GREY   = 0x444444
BLUE   = 0x0039a6
GOLD   = 0xDD8000
BLACK  = 0x000000

FONT = {
    'thumb':   bitmap_font.load_font("fonts/tom-thumb.bdf"),
    '5x7':     bitmap_font.load_font("fonts/5x7.bdf"),
    'helvB10': bitmap_font.load_font("fonts/helvB10.bdf"),
}

display          = Matrix().display
display.rotation = 270
network          = Network(status_neopixel=NEOPIXEL, debug=False)



# UTILITIES ####################################################################

# Generates all values for key in input
def json_find(input, key):
    if isinstance(input, dict):
        for k, v in input.items():
            if k == key:
                yield v
            else:
                yield from json_find(v, key)
    elif isinstance(input, list):
        for item in input:
            yield from json_find(item, key)

# Returns the difference in minutes between now and then
def in_mins(now, then):
    then_iso = datetime.fromisoformat(then).replace(tzinfo = None)
    return round((then_iso - now).total_seconds() / 60.0)



# GRAPHICS SETUP ###############################################################

ICONS_FILE = displayio.OnDiskBitmap('weather-icons.bmp')
ICON_DIM   = (16, 16) # width x height
ICON_MAP   = {  # map openweathermap icon codes to their x,y in the bitmap
    '01d': (0, 0), '01n': (1, 0),
    '02d': (0, 1), '02n': (1, 1),
    '03d': (0, 2), '03n': (1, 2),
    '04d': (0, 3), '04n': (1, 3),
    '09d': (0, 4), '09n': (1, 4),
    '10d': (0, 5), '10n': (1, 5),
    '11d': (0, 6), '11n': (1, 6),
    '13d': (0, 7), '13n': (1, 7),
    '50d': (0, 8), '50n': (1, 8),
}
SPRITE     = displayio.TileGrid(
    ICONS_FILE,
    pixel_shader = ICONS_FILE.pixel_shader,
    tile_width   = ICON_DIM[0],
    tile_height  = ICON_DIM[1]
)

def get_icon(icon_code):
    (col, row) = ICON_MAP[icon_code]
    SPRITE[0] = (row * 2) + col
    return SPRITE    

root_group    = displayio.Group()
clock_group   = displayio.Group(x=0, y=1)
weather_group = displayio.Group(x=0, y=12)
headers_group = displayio.Group(x=4, y=28)
times_group   = displayio.Group(x=0, y=41)

clock = {
    'time': label.Label(FONT['helvB10'], color=WHITE, x=3, y=4, text="--:--"),
}

headers = [
    circle.Circle(fill=ORANGE, x0=1, y0=4, r=4),
    circle.Circle(fill=GREY, x0=11, y0=4, r=4),
    circle.Circle(fill=BLUE, x0=22, y0=4, r=4),
    label.Label(FONT['thumb'], color=BLACK, x=0, y=5, text="M"),
    label.Label(FONT['thumb'], color=BLACK, x=10, y=5, text="L"),
    label.Label(FONT['thumb'], color=BLACK, x=20, y=5, text="1"),
    label.Label(FONT['thumb'], color=BLACK, x=23, y=5, text="3"),
    line.Line(x0=6, y0=10, x1=6, y1=32, color=GREY),
    line.Line(x0=17, y0=10, x1=17, y1=32, color=GREY),
]

times = {
    'M': label.Label(FONT['5x7'], color=GOLD, x=0, y=0, \
        text="--\n--\n--", line_spacing=1.2),
    'L': label.Label(FONT['5x7'], color=GOLD, x=12, y=0, \
        text="--\n--\n--", line_spacing=1.2),
    'B': label.Label(FONT['5x7'], color=GOLD, x=23, y=0, \
        text="--\n--\n--", line_spacing=1.2),
}

weather = {
    'icon':   displayio.Group(x=0, y=0),
    'temp':   label.Label(FONT['helvB10'], color=WHITE, x=17, y=7, text="--"),
    'degree': circle.Circle(outline=WHITE, fill=BLACK, x0=29, y0=3, r=1),
}
weather['icon'].append(get_icon('01n'))

for item in headers:
    headers_group.append(item)
for item in times.values():
    times_group.append(item)
for item in clock.values():
    clock_group.append(item)
for item in weather.values():
    weather_group.append(item)

root_group.append(clock_group);
root_group.append(headers_group);
root_group.append(times_group);
root_group.append(weather_group);

display.show(root_group)



# MTA SUBWAY API ###############################################################

TRAIN_API = 'https://api.wheresthefuckingtrain.com/by-id/'
STATION = {
    # These codes are from
    #     github.com/jonthornton/MTAPI/blob/master/data/stations.json
    'Forest Av':            '934a',
    'Myrtle - Wyckoff Avs': 'f145'
}

def train_api(station, route, dir):
    query    = '%s%s'% (TRAIN_API, STATION[station])
    schedule = network.fetch_data(query, json_path=(["data"],))
    now      = datetime.now()

    for trains in json_find(schedule, dir):
        for train in (t for t in trains if t['route'] == route):
            mins = in_mins(now, train['time']) 
            yield 'Ar' if mins < 1 else str(mins)



# MTA BUS API ##################################################################

BUS_API = \
    'https://bustime.mta.info/api/siri/stop-monitoring.json' \
    '?version=2' \
    '&StopMonitoringDetailLevel=minimum' \
    '&key=%s' \
    '&MonitoringRef=%s' \
    '&DirectionRef=%s' \
    '&MaximumStopVisits=%s' \

STOP = {
    # These codes are from bustime.mta.info
    'GATES AV/GRANDVIEW AV': '504111',
}

def bus_api(stop, dir):
    query = BUS_API % (secrets['bustime_key'], STOP[stop], dir, MAX_T)
    try:
        schedule = network.fetch_data(query, json_path=(["Siri"],))
    except MemoryError as e:
        # The bus api is quite verbose.  Sometimes the replies are too big
        # and the M4 runs out of memory.
        for _ in range(MAX_T):
            yield 'xx'
        return

    now = datetime.now()
    for bus in json_find(schedule, 'ExpectedArrivalTime'):
        mins = in_mins(now, bus)
        yield 'Ar' if mins < 1 else str(mins)



# WEATHER API SETUP ############################################################

WEATHER_API = \
    'https://api.openweathermap.org/data/2.5/weather' \
    '?lat=%s' \
    '&lon=%s' \
    '&appid=%s' \
    '&units=imperial'


def weather_api(coords):
    query = WEATHER_API % (coords['lat'], coords['lon'], secrets['weather_key'])
    resp = network.fetch_data(query, json_path=([]))
    icon = resp['weather'][0]['icon']
    temp = round(resp['main']['temp'])
    return (icon, temp)



# API HANDLERS #################################################################
errors = {
    'clock':   {},
    'm_train': {},
    'l_train': {},
    'b13_bus': {},
    'weather': {},
    'unknown': {},
} 

def error_log(exception, name):
    err = type(exception).__name__
    if err not in errors[name]:
        errors[name][err] = 0
    errors[name][err] += 1 
    traceback.print_exception(exception)

def clock_time():
    network.get_local_time()

def m_train():
    arrivals = [] 
    for train in zip(train_api('Forest Av', route='M', dir='N'), range(MAX_T)):
        arrivals.append(train[0])   
    times['M'].text = "\n".join(arrivals)

def l_train():
    arrivals = [] 
    for train in zip(
            train_api('Myrtle - Wyckoff Avs', route='L', dir='N'),
            range(MAX_T)):
        arrivals.append(train[0])   
    times['L'].text = "\n".join(arrivals)

def b13_bus():
    arrivals = [] 
    for train in zip(bus_api('GATES AV/GRANDVIEW AV', dir=0), range(MAX_T)):
        arrivals.append(train[0])   
    times['B'].text = "\n".join(arrivals)

def wthr_card():
    icon_code, temp = weather_api(secrets['coords'])
    weather['icon'].pop()
    weather['icon'].append(get_icon(icon_code))
    weather['temp'].text = str(temp)

def reset():
    microcontroller.reset()

# Only call source if at least rate seconds have passed since the last
# time we called it.  Returns the last time we called.
def rate_limit(name, source, rate, last):
    if last == None or time.monotonic() - last >= rate:
        gc.collect()
        print(name)
        try:
            source()
        except Exception as e:
            error_log(e, name)
        return time.monotonic() 
    else:
        return last



# MAIN LOOP ####################################################################

network.get_local_time()
clock_last = reset_last = time.monotonic()
train_last = bus_last = wthr_last = None

while True:
    try:
        now = datetime.now()
        clock['time'].text = "%02d:%02d" % (now.hour, now.minute)

        clock_last = rate_limit("clock", clock_time, TIME_LIMIT, clock_last)
        train_last = rate_limit("m_train", m_train, TRAIN_LIMIT, train_last)
        train_last = rate_limit("l_train", l_train, TRAIN_LIMIT, train_last)
        bus_last   = rate_limit("b13_bus", b13_bus, BUS_LIMIT, bus_last)
        wthr_last  = rate_limit("weather", wthr_card, WEATHER_LIMIT, wthr_last)
        reset_last = rate_limit("reset",   reset, RESET_LIMIT, reset_last)

    except Exception as e:
        error_log(e, 'unknown')

    print("mem_free: %s" % (gc.mem_free()))
    print("error_hist: ", errors)
    time.sleep(REFRESH_RATE);

