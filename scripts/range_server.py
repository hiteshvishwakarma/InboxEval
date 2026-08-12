import os
import http.server
import socketserver

PORT = 8080

class RangeHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def send_head(self):
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            return super().send_head()
        
        try:
            f = open(path, 'rb')
        except OSError:
            self.send_error(404, "File not found")
            return None

        fs = os.fstat(f.fileno())
        file_len = fs[6]
        
        range_header = self.headers.get('Range')
        if range_header:
            try:
                type_unit, ranges = range_header.split('=')
                if type_unit.strip() == 'bytes':
                    start_str, end_str = ranges.split('-')
                    start = int(start_str)
                    end = int(end_str) if end_str else file_len - 1
                    if start >= file_len:
                        self.send_error(416, "Requested Range Not Satisfiable")
                        f.close()
                        return None
                    
                    self.send_response(206)
                    self.send_header('Content-Type', self.guess_type(path))
                    self.send_header('Content-Range', f'bytes {start}-{end}/{file_len}')
                    self.send_header('Content-Length', str(end - start + 1))
                    self.send_header('Accept-Ranges', 'bytes')
                    self.end_headers()
                    f.seek(start)
                    return f
            except Exception as e:
                pass

        self.send_response(200)
        self.send_header('Content-Type', self.guess_type(path))
        self.send_header('Content-Length', str(file_len))
        self.send_header('Accept-Ranges', 'bytes')
        self.end_headers()
        return f

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), RangeHTTPRequestHandler) as httpd:
        print(f"Serving Range HTTP on port {PORT}...")
        httpd.serve_forever()
