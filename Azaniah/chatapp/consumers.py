from channels.generic.websocket import AsyncJsonWebsocketConsumer #websocket behavior that adds JSON encoding and decoding

class EchoConsumer(AsyncJsonWebsocketConsumer): #this class inherits from AsyncWebsocketConsumer, which is a base class provided by Django Channels for handling WebSocket connections asynchronously.
    async def connect(self):
        """channels calls connect() when a browser client attempts to establish a WebSocket connection with 
        the server. The method is asynchronous, allowing it to handle
        multiple connections concurrently without blocking the event loop."""
        await self.accept() #self refers to the instance of the EchoConsumer class. The accept() method is called to accept the WebSocket connection, allowing communication between the client and server.

    async def receive_json(self, content, **kwargs): #channels calls recerve() when a connected browser send a message
        if content is not None:
            await self.send_json(content)

        """reason for this echoconsumer is to test the websocket connection.
        the exact messages sent by the client are echoed(resent) back to the client.
        just like texting with someone that sends exactly what you sent to them.
        this is useful for testing the websocket connection and ensuring that messages are being sent and received correctly."""


