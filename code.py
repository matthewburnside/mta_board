import adafruit_display_text.label
import displayio
import gc
import microcontroller
import mta_bus
import mta_train
import openweather
import secrets
import time
from adafruit_bitmap_font import bitmap_font
from adafruit_datetime import datetime
from adafruit_display_text import label
from adafruit_display_shapes import circle
from adafruit_display_shapes import line
from adafruit_matrixportal.matrix import Matrix
from adafruit_matrixportal.network import Network
from board import NEOPIXEL

ERROR_THRESHOLD   = 3     # before resetting the microcontroller
REFRESH_RATE      = 15    # time (s) between refreshing the counts
TIME_SYNC_RATE    = 3600  # query the network time once per hour 
WEATHER_SYNC_RATE = 600   # check weather every 10 mins

MONTH = ['','Jan','Feb','Mar','Apr','May','Jun',
    'Jul','Aug','Sep','Oct','Nov','Dec']

WHITE  = 0x666666
ORANGE = 0xff6319
GREY   = 0x444444
BLUE   = 0x0039a6
GOLD   = 0xDD8000
BLACK  = 0x000000

FONT = {
    '5x7': bitmap_font.load_font("fonts/5x7.bdf"),
    '6x10': bitmap_font.load_font("fonts/6x10.bdf"),
    'helvB10': bitmap_font.load_font("fonts/helvB10.bdf"),
    'thumb': bitmap_font.load_font("fonts/tom-thumb.bdf"),
}

ICONS_FILE = displayio.OnDiskBitmap('weather-icons.bmp')
ICON_DIM = (16, 16) # width x height
ICON_MAP = {  # map the openweathermap code to the icon location
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

SPRITE = displayio.TileGrid(ICONS_FILE, pixel_shader=ICONS_FILE.pixel_shader,
    tile_width = ICON_DIM[0], tile_height = ICON_DIM[1])

def get_sprite(icon):
    icon = '01d'
    (col, row) = ICON_MAP[icon]
    if len(weather['icon']) > 0:
        weather['icon'].pop()
    SPRITE[0] = (row * 2) + col
    return SPRITE    

matrix = Matrix()
display = matrix.display
display.rotation = 270
network = Network(status_neopixel=NEOPIXEL, debug=False)

root_group = displayio.Group()
clock_group = displayio.Group(x=0, y=0)
headers_group = displayio.Group(x=4, y=12)
times_group = displayio.Group(x=0, y=26)
weather_group = displayio.Group(x=1, y=48)

clock = {
    'time': label.Label(FONT['helvB10'], color=WHITE, x=3, y=4, text="00:00"),
}

headers = [
    circle.Circle(fill=ORANGE, x0=1, y0=4, r=4),
    circle.Circle(fill=GREY, x0=11, y0=4, r=4),
    circle.Circle(fill=BLUE, x0=22, y0=4, r=4),
    label.Label(FONT['5x7'], color=BLACK, x=-1, y=4, text="M"),
    label.Label(FONT['5x7'], color=BLACK, x=10, y=4, text="L"),
    label.Label(FONT['thumb'], color=BLACK, x=19, y=5, text="13"),
    line.Line(x0=6, y0=10, x1=6, y1=35, color=GREY),
    line.Line(x0=17, y0=10, x1=17, y1=35, color=GREY),
]

times = {
    'M': label.Label(FONT['5x7'], color=GOLD, x=0, y=0, \
        text=" "*9, line_spacing=1.4),
    'L': label.Label(FONT['5x7'], color=GOLD, x=11, y=0, \
        text=" "*9, line_spacing=1.4),
    'B': label.Label(FONT['5x7'], color=GOLD, x=23, y=0, \
        text=" "*9, line_spacing=1.4),
}

weather = {
    'icon': displayio.Group(x=0, y=0),
    'temp': label.Label(FONT['helvB10'], color=WHITE, x=17, y=8, text="00"),
    'degree': label.Label(FONT['6x10'], color=WHITE, x=27, y=7, text='°'),
}
weather['icon'].append(get_sprite('01n'))

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


errors = 0
time_refresh = None
weather_refresh = None
while True:
    try:
        if time_refresh == None or time.monotonic() - time_refresh > TIME_SYNC_RATE:
            network.get_local_time()
            time_refresh = time.monotonic()

        now = datetime.now()
        clock['time'].text = "%02d:%02d" % (now.hour, now.minute)

        arrivals = mta_train.arrivals(network, 'Forest Av', route='M', dir='N')
        times['M'].text = "\n".join(arrivals)

        arrivals = mta_train.arrivals(network, 'Myrtle - Wyckoff Avs', route='L', dir='N')
        times['L'].text = "\n".join(arrivals)

        stops = mta_bus.stops_away(network, 'GATES AV/GRANDVIEW AV', dir=0)
        times['B'].text = "\n".join(stops)

        if weather_refresh == None or time.monotonic() - weather_refresh > WEATHER_SYNC_RATE:
            weather_refresh = time.monotonic()
	    icon, temp = openweather.weather(network, secrets.secrets['coords'])
            weather['icon'].append(get_sprite(icon))
            weather['temp'].text = str(temp)

    except (ValueError, TimeoutError, RuntimeError) as e: # , MemoryError) as e:
        print("\nError\n", e)
        errors = errors + 1
        if errors > ERROR_THRESHOLD:
            microcontroller.reset()

    time.sleep(REFRESH_RATE);


