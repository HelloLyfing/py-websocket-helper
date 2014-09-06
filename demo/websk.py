import socket
import select
import uuid
import threading

# where is the pywshelper ?
import os, sys
curtPath = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(curtPath, '..'))
import pywshelper

class WebSocket(threading.Thread):

    def __init__(self, host, port):
        threading.Thread.__init__(self)
        # server socket
        self.serverSK = self.newServerSK(host, port)
        # client socket list
        self.cliSKList = []
        
    def newServerSK(self, host, port):
        sk = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sk.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sk.bind( (host, int(port)) )
        sk.listen(5)

        print 'Establish server socket - %s:%s \n' %(host, port)
        return sk

    def run(self):
        while True:
            checkInputList = [client['sk'] for client in self.cliSKList]
            checkInputList.append(self.serverSK)
            
            changedSK = select.select(checkInputList, [], [])[0]
            for sk in changedSK:
                self.addNewClient() if (sk == self.serverSK) else self.handleCliMsg(sk)

    def addNewClient(self):
        cliSK, clAddr = self.serverSK.accept()
        uid = str( uuid.uuid4() )
        self.cliSKList.append( {'idx': uid, 'sk': cliSK, 'handShake': False} )
        print 'New client conned - %s:%s' %(clAddr[0], clAddr[1])

    def handleCliMsg(self, sk):
        client = [item for item in self.cliSKList if item['sk'] == sk ][0]
        if not client['handShake']:
            client['handShake'] = pywshelper.handshake(sk)
            return

        msg = self.getCliMsg(sk)
        if msg is None:
            sk.close()
            self.cliSKList.remove(client)
            print 'Client closed: %s' % client['idx']
            return

        print 'New msg: %s' % msg.decode('utf-8')
        # when received msg, send it back
        self.sendMsg(msg, sk)

    def getCliMsg(self, sk):
        # start recv data
        frames = sk.recv(2048)
        # data len == 0
        if len(frames) == 0:
            return None

        return pywshelper.decode_from_frames(frames)

    def sendMsg(self, msg, sk):
        frame = pywshelper.encode_to_frames(msg)
        # send to a specific sk
        sk.send(frame)
    
    def broadcast(self, msg):        
        # send to all
        for cli in self.cliSKList:
            if cli['handShake']:
                self.sendMsg(msg, cli['sk'])

if __name__ == "__main__":
    import time
    
    host = '127.0.0.1'
    port = '9023'
    websk = WebSocket(host, port)
    websk.daemon = True
    websk.start()
    
    keepAlive = True
    while keepAlive:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            print 'Capture Error: KeyboardInterrupt'
            keepAlive = False
    
    print '\nmain thread exits.'

