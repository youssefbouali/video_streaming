# server.py
import asyncio
import base64
import cv2
import numpy as np
from aiohttp import web
from aiortc import RTCPeerConnection, VideoStreamTrack, RTCSessionDescription
from av import VideoFrame
import websockets

latest_frame = None  # shared between WebSocket and WebRTC

class RelayStreamTrack(VideoStreamTrack):
    async def recv(self):
        global latest_frame
        pts, time_base = await self.next_timestamp()
        while latest_frame is None:
            await asyncio.sleep(0.01)
        frame = cv2.cvtColor(latest_frame, cv2.COLOR_BGR2RGB)
        av_frame = VideoFrame.from_ndarray(frame, format="rgb24")
        av_frame.pts = pts
        av_frame.time_base = time_base
        return av_frame

async def websocket_handler(websocket, path):
    global latest_frame
    async for message in websocket:
        data = base64.b64decode(message)
        npdata = np.frombuffer(data, dtype=np.uint8)
        frame = cv2.imdecode(npdata, 1)
        latest_frame = frame

async def index(request):
    return web.Response(content_type="text/html", text=open("index.html").read())

async def offer(request):
    params = await request.json()
    offer = params["offer"]

    pc = RTCPeerConnection()

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        print("Connection state:", pc.connectionState)

    pc.addTrack(RelayStreamTrack())
    await pc.setRemoteDescription(
        RTCSessionDescription(sdp=offer["sdp"], type=offer["type"])
    )
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return web.json_response({
        "sdp": pc.localDescription.sdp,
        "type": pc.localDescription.type
    })

# Start both HTTP server and WebSocket server
async def start_all():
    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_post("/offer", offer)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, port=8080)
    await site.start()
    print("HTTP server running at http://localhost:8080")

    ws_server = websockets.serve(websocket_handler, "localhost", 8765)
    await ws_server
    print("WebSocket server running at ws://localhost:8765")

    while True:
        await asyncio.sleep(3600)

asyncio.run(start_all())
