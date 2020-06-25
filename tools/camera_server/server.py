import cv2
import asyncio
from io import BytesIO
from typing import Optional

import json
from aiohttp import web

cameras = {}


COLORSPACE_BGR = 1


class InvalidCamera(Exception):
    pass


async def root(request):
    return web.Response(text="Hello!")


def _get_image (id: Optional[int]):
    if id is None:
        raise InvalidCamera()

    id = int(id)
    if id not in cameras:
        raise InvalidCamera()

    success, frame = cameras[id].read()

    if not success:
        raise InvalidCamera()

    return frame

def _get_image_http (id: Optional[int]): 
    try:
        return _get_image(id)
    except InvalidCamera:
        raise web.HTTPNotFound()

async def get_image_png(request):
    id = request.match_info.get('id', None)
    frame = _get_image(id)
    success, buffer = cv2.imencode(".png", frame)

    if not success:
        raise web.HTTPServerError()
    
    io_buf = BytesIO(buffer)

    return web.Response(body=io_buf.getvalue(), content_type='image/png')

def _get_image_bytes (frame):
    return frame.tobytes()

async def get_image_bytes (request):
    id = request.match_info.get('id', None)
    return web.Response(body = _get_image_bytes(_get_image_http(id)))

def _get_image_format (frame) -> dict:
    image_format = dict(
        height = frame.shape[0],
        width = frame.shape[1],
        colorspace = COLORSPACE_BGR
    )

    try:
        image_format['channels'] = frame.shape[2]
    except IndexError:
        image_format['channels'] = 1
    
    return image_format


async def get_image_format (request):
    id = request.match_info.get('id', None)
    return web.json_response(_get_image_format(_get_image_http(id)))


class CameraServerProtocol(asyncio.Protocol):
    _buffer = b''
    delimiter = b'\n'
    MAX_LENGTH = 10

    def connection_made (self, transport: asyncio.Transport):
        self.transport = transport

    def data_received (self, data: bytes):
        """
        Translates bytes into lines, and calls line_received.
        """
        lines = (self._buffer + data).split(self.delimiter)
        self._buffer = lines.pop(-1)
        
        for line in lines:
            if self.transport.is_closing():
                # this is necessary because the transport may be told to lose
                # the connection by a line within a larger packet, and it is
                # important to disregard all the lines in that packet following
                # the one that told it to close.
                return
            if len(line) > self.MAX_LENGTH:
                return self.transport.close()
            else:
                return self.line_received(line)
        if len(self._buffer) > self.MAX_LENGTH:
            return self.transport.close()

    def send_data (self, command: bytes, line: bytes):
        """
        Sends a line to the other end of the connection.

        @param line: The line to send, not including the delimiter.
        """
        command_b = command
        length_b = len(line).to_bytes(4, byteorder = 'big')
        return self.transport.write(command_b + length_b + line)
    
    def line_received (self, line: bytes):
        """
        Processes a line that is received
        """

        try:
            command = chr(line[0])
            camera_id = int(line[1:])
        except (IndexError, ValueError):
            return self.send_line(b'!', b'Invalid Command Format')

        try:
            if command == 'I':
                return self.send_data(b'I', _get_image_bytes(_get_image(camera_id)))

            if command == 'F':
                return self.send_data(b'F', json.dumps(_get_image_format(_get_image(camera_id))).encode('utf-8'))

        except InvalidCamera:
            return self.send_data(command.encode(), b'Invalid Camera ID')

        return self.send_data(b'!', b'Invalid Command Format')


async def tcp_server (app: web.Application):
    loop = asyncio.get_event_loop()
    server = await loop.create_server(
        lambda: CameraServerProtocol(), 
        '127.0.0.1', 
        8081
    )
    server_task = loop.create_task(server.serve_forever())
    app['tcp_server'] = server
    yield
    server_task.cancel()
    await server.wait_closed()


app = web.Application()
app.add_routes([
    web.get('/', root),
    web.get('/cameras/{id}/format.json', get_image_bytes),
    web.get('/cameras/{id}/image.b', get_image_bytes),
    web.get('/cameras/{id}/image.png', get_image_png)
])
app.cleanup_ctx.append(tcp_server)

if __name__ == '__main__':
    cameras[0] = cv2.VideoCapture(0)
    web.run_app(app)


