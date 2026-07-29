import functools, http.server, socketserver
D = "/Users/carlodemarchis/Documents/_cdm/_carlo/FACTORY63/Claude Code/atp-cards"
H = functools.partial(http.server.SimpleHTTPRequestHandler, directory=D)
socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("127.0.0.1", 8777), H) as s:
    s.serve_forever()
