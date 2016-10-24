# created My Massimo Di Pierro
# license BSD, 2016
import hmac
import hashlib
import json
import time
import threading
import traceback
import requests
from ws4py.client import WebSocketBaseClient

URL_HTTP = 'http://iotcallme.com:9000/api/'
URL_WS = 'ws://iotcallme.com:9000/ws'
MAX_WAIT_RETRY = 10*60 # seconds

class IOTWebSocketClient(WebSocketBaseClient):
    def __init__(self, url, protocols=None, extensions=None, heartbeat_freq=None,
                 ssl_options=None, headers=None):
        WebSocketBaseClient.__init__(self, url, protocols, extensions, heartbeat_freq,
                                     ssl_options, headers=headers)
        self._th = threading.Thread(target=self.run, name='WebSocketClient')
        self._th.daemon = True

    @property
    def daemon(self):
        return self._th.daemon

    @daemon.setter
    def daemon(self, flag):
        self._th.daemon = flag

    def run_forever(self):
        while not self.terminated:
            self._th.join(timeout=0.1)

    def handshake_ok(self):
        self._th.start()

    def opened(self):
        pass

    def closed(self, code, reason):
        pass

    def received_message(self, m):
        self.callback(m)

def call(url, payload=None, api_key=None, method=requests.post):
    headers = None
    if api_key:
        headers = { 'X-Api-Key': api_key }
    res = method(url, json=payload, headers=headers)
    return json.loads(res.content)

def register(api_key):
    return call(URL_HTTP+'register', api_key=api_key)

def trigger(device_key, message):
    return call(URL_HTTP+'wakeup/'+device_key, payload=message)

def ontrigger(device_key, callback):
    def target():
        sleep = 1
        while True:
            try:
                ws = IOTWebSocketClient(
                    URL_WS,
                    protocols=['http-only', 'chat'],
                    headers=[('X-Device-Key', device_key)])
                ws.callback = callback
                ws.connect()
                print 'connected'
                sleep = 1
                ws.run_forever()
            except Exception, e:
                print traceback.format_exc()
                time.sleep(sleep)
                sleep = max(sleep*2, MAX_WAIT_RETRY)
    thread = threading.Thread(target = target)
    thread.start()
    return thread

