from http.server import BaseHTTPRequestHandler
from socketserver import TCPServer
from webbrowser import open_new_tab
import pathlib


def open_in_perfetto(tracefile: pathlib.Path):
    print(f"Opening {str(tracefile)} on ui.perfetto.dev")
    content = tracefile.read_text()

    PORT = 9001
    ORIGIN = "https://ui.perfetto.dev"

    class TraceHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != "/trace.json":
                self.send_error(405)

            self.server.trace_served = True
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", ORIGIN)
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Content-type", "text/json")
            self.send_header("Content-length", str(len(content)))
            self.end_headers()
            self.wfile.write(content.encode())

        def do_POST(self):
            self.send_error(405)

        def log_message(self, format, *args):
            pass

    # We reuse the HTTP+RPC port because it's the only one allowed by the CSP.

    TCPServer.allow_reuse_address = True
    with TCPServer(("127.0.0.1", PORT), TraceHandler) as httpd:
        address = f"{ORIGIN}/#!/?url=http://127.0.0.1:{PORT}/trace.json"
        open_new_tab(address)

        httpd.trace_served = False
        httpd.allow_origin = ORIGIN
        while not httpd.trace_served:
            httpd.handle_request()
