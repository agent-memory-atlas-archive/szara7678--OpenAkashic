import socket,socketserver,threading
class Relay(socketserver.BaseRequestHandler):
 def handle(self):
  remote=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);remote.connect('/bridge/broker.sock')
  def copy(a,b):
   try:
    while True:
     x=a.recv(65536)
     if not x:break
     b.sendall(x)
   except OSError:pass
   finally:
    try:b.shutdown(socket.SHUT_WR)
    except OSError:pass
  t=threading.Thread(target=copy,args=(self.request,remote),daemon=True);t.start()
  copy(remote,self.request);t.join(2);remote.close()
class S(socketserver.ThreadingMixIn,socketserver.TCPServer):
 allow_reuse_address=True;daemon_threads=True
S(('127.0.0.1',18090),Relay).serve_forever()