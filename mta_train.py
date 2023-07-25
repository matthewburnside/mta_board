from adafruit_datetime import datetime

API = 'https://api.wheresthefuckingtrain.com/by-id/' 

STATION = {
    'Forest Av': '934a',
    'Myrtle - Wyckoff Avs': 'f145'
}

MAX_ENTRIES = 3

def arrivals(network, station, route, dir):
    query = '%s%s'% (API, STATION[station])
    schedule = network.fetch_data(query, json_path=(["data"],))
    arrivals = [] 
    now = datetime.now()
    for entry in schedule:
        trains = entry[dir] # only grab the trains in the dir we want
        trains = [t for t in trains if t['route'] == route] # only our line
        for train in trains:
            arrivals.append(in_mins(now, train['time']))
    arrivals.sort()
    arrivals = ["Ar" if i < 1 else str(i) for i in arrivals]
    print("%s %s %s: %s" % (station, route, dir, arrivals))

#    del schedule
    return arrivals[:MAX_ENTRIES]


def in_mins(now, date_str):
    train_date = datetime.fromisoformat(date_str).replace(tzinfo=None)
    return round((train_date-now).total_seconds()/60.0)
