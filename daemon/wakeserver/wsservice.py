import threading
import json
from websocket_server import WebsocketServer

WSPORT = 9090

server = None

def newClient(client, server):
    addr, port = client['address']
    print 'WS: connected a client: {0}.{1}'.format(addr, port)

def leftClient(client, server):
    addr, port = client['address']
    print 'WS: disconnected a client: {0}.{1}'.format(addr, port)


class WSService(threading.Thread) :
    def __init__(self, conf):
        global server
        super(WSService, self).__init__()
        self.conf = conf
        server = WebsocketServer(WSPORT, host='0.0.0.0')
        server.set_fn_new_client(newClient)
        server.set_fn_client_left(leftClient)

    def run(self):
        global servrer
        server.run_forever()

__service = None
        
def startService(conf):
    global __service
    if __service:
        return
    __service = WSService(conf)
    __service.start()

def sendStatus(index, status):
    global server
    data = {'index': index, 'status': status}
    if server:
        server.send_message_to_all(json.dumps(data))
