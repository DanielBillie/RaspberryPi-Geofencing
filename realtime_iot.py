import serial
import time
from datetime import datetime
import string
import pynmea2
import pyrebase
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub
from pubnub.exceptions import PubNubException
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon
from twilio.rest import Client
import keys

client = Client(keys.account_sid, keys.auth_token)

# message = client.messages.create(
	# body="Alert:Your vehicle is out of geofence!",
	# from_=keys.twilio_number,
	# to=keys.my_phone_number
# )

config = {
  "apiKey": "2eX6YYjCCSvJFEYHPHmDqikMMRgc6W55DSY78Ddx",
  "authDomain": "ultbov3firebase.firebaseapp.com",
  "databaseURL": "https://ultbov3firebase-default-rtdb.asia-southeast1.firebasedatabase.app",
  "storageBucket": "ultbov3firebase.appspot.com"
}

firebase = pyrebase.initialize_app(config)
db = firebase.database()

pnChannel = "raspi-tracker";

pnconfig = PNConfiguration()
pnconfig.subscribe_key = "sub-c-adda7307-c21b-4651-b3c2-351a9845feb2"
pnconfig.publish_key = "pub-c-6b7e8106-927e-4960-8c95-2595dbc46d19"
pnconfig.ssl = False
 
pubnub = PubNub(pnconfig)
pubnub.subscribe().channels(pnChannel).execute()

# Define the geofence polygon coordinates
geofence_coords = [(101.130979,4.329709), (101.131496,4.330236), (101.132065,4.33008),(101.131336,4.329214)]
geofence_polygon = Polygon(geofence_coords)

# Initialize geofence status variable to 'outside'
geofence_status = 'outside'

while True:
    port="/dev/ttyAMA0"
    ser=serial.Serial(port, baudrate=9600, timeout=5.0)
    dataout = pynmea2.NMEAStreamReader()
    gps_data = ser.readline().decode('ascii', errors='replace')
    

    if gps_data[0:6] == '$GPGGA' or gps_data[0:6] == '$GPRMC':
        newmsg=pynmea2.parse(gps_data)
        lat=newmsg.latitude
        lng=newmsg.longitude
        
        # Create a point object from the GPS coordinates
        point = Point(lng, lat)
        
        # Check if the point is inside the geofence polygon
        if geofence_polygon.contains(point):
            geofence_status = 'inside'
            print("Inside the geofence")
        else:
            geofence_status = 'outside'
            print("Outside the geofence")
            
            message = client.messages.create(
            body="Alert:Your vehicle is out of geofence!",
            from_=keys.twilio_number,
            to=keys.my_phone_number
)
            print(message.body)
            time.sleep(10)
        
        try:
            envelope = pubnub.publish().channel(pnChannel).message({
            'lat':lat,
            'lng':lng,
            'geofence_status': geofence_status # Add geofence status to message
            }).sync()
            print("publish timetoken: %d" % envelope.result.timetoken)
            print("Longitude:", lng, "\t Latitude:", lat)
            now = datetime.now()
            current_time = now.strftime("%Y-%b-%d %H:%M:%S \n")
            print("Current Time=", current_time)
            
            
            data = {
                "Date Time": current_time,
                "Longitude": lng,
                "Latitude": lat,
                "Geofence": geofence_status,
            }
            
            db.child("ultGPSbov3").child("1-set").set(data)
            db.child("ultGPSbov3").child("2-push").push(data)

            
        except PubNubException as e:
            handle_exception(e)
            
