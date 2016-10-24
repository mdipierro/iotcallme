# created My Massimo Di Pierro
# license BSD, 2016
import hmac
import uuid
import json
from tornado import websocket, web, ioloop
from pymongo import MongoClient
from iotcallme_server_master_key import MASTER_KEY

class IOTDB(object):
    def __init__(self, uri='mongodb://localhost:27017/'):
        self.uri = uri
        self.client = MongoClient(uri)
        self.db = self.client['iot-db']
        self.credentials = self.db['iot-credentials']
        self.devices = self.db['iot-devices']
    def get_credentials(self, api_key):
        record = self.credentials.find_one({'_id':api_key}) if api_key else None
        return record
    def register_device(self, device_key, record):
        user_id = record['user_id']
        if device_key:
            record = self.devices.find_one({'_id':device_key})
            if record:
                record['user_id'] = user_id
            else:
                self.devices.save({'_id':device_key, 'user_id':user_id})
            return record
    def get_device(self, device_key):
        record = self.devices.find_one({'_id':device_key}) if device_key else None
        return record

CLIENTS = {}
REVERSED = {}

class SocketHandler(websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True

    def open(self):        
        device_key = self.request.headers.get('X-Device-Key')        
        # TODO: verify device_key
        CLIENTS[device_key] = self
        REVERSED[id(self)] = device_key

    def on_close(self):
        id_self = id(self)
        del CLIENTS[REVERSED[id_self]]
        del REVERSED[id_self]

def sign(code, master_key=MASTER_KEY):
    return code+'-'+hmac.new(master_key, code).hexdigest()

class ApiHandler(web.RequestHandler):

    @web.asynchronous
    def get(self, *args):
        self.write('ok')

    @web.asynchronous
    def post(self, *args):
        parts = self.request.path.split('/')[2:]
        command = parts[0]
        if command == 'register':
            record = iot.get_credentials(self.request.headers.get('X-Api-Key'))
            if record:
                device_key_unsigned = str(uuid.uuid4()).replace('-','')
                device_key = sign(device_key_unsigned)
                iot.register_device(device_key, record)
                self.write(json.dumps({'device_id':device_key}))
            else:
                self.write(json.dumps({'error':'invalid or missing x-api-key'}))
        elif command == 'wakeup':
            device_key = parts[1] if len(parts)>1 else None
            device_key_unsigned = device_key.split('-')[0]
            if device_key != sign(device_key):
                if device_key in CLIENTS:
                    CLIENTS[device_key].write_message(self.request.body)
                    self.write(json.dumps({}))
                else:
                    self.write(json.dumps({'error':'device not connected'}))
            else:
                self.write(json.dumps({'error':'unknown device_key'}))
        else:
            self.write(json.dumps({'error':'invalid command'}))
        self.finish()
        
iot = IOTDB()
app = web.Application([
    (r'/ws', SocketHandler),
    (r'/api/([^/]*)', ApiHandler),
    (r'/api/([^/]*)/(.*)', ApiHandler),
])

if __name__ == '__main__':
    app.listen(9000)
    ioloop.IOLoop.instance().start()
