# import gc
from adafruit_datetime import datetime
from secrets import secrets

BUS_KEY = 'b8a18541-8e95-403d-a327-e92c48855853'
API = 'https://bustime.mta.info/api/siri/stop-monitoring.json' \
    '?key=%s&MonitoringRef=%s&DirectionRef=%s&MaximumStopVisits=%s'

STOP = {
    'GATES AV/GRANDVIEW AV': '504111',
}

MAX_ENTRIES = 3

def stops_away(network, stop, dir):
    query = API % (secrets['bustime_key'], STOP[stop], dir, MAX_ENTRIES)
    schedule = network.fetch_data(query, json_path=(["Siri"],))
    buses = schedule['ServiceDelivery']['StopMonitoringDelivery'][0]
    journeys = buses['MonitoredStopVisit']
   
    stops = []
    for j in journeys:
        bus = j['MonitoredVehicleJourney']['MonitoredCall']['Extensions']
        stops.append(bus['Distances']['StopsFromCall'])

    print("%s %s %s" % (stop, dir, stops))
    stops.sort()
    stops = [str(i) for i in stops]

    return stops[:MAX_ENTRIES]

