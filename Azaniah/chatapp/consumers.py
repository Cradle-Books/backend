from channels.generic.websocket import AsyncJsonWebsocketConsumer #websocket behavior that adds JSON encoding and decoding

class EchoConsumer(AsyncJsonWebsocketConsumer): #this class inherits from AsyncWebsocketConsumer, which is a base class provided by Django Channels for handling WebSocket connections asynchronously.
    async def connect(self):
        """channels calls connect() when a browser client attempts to establish a WebSocket connection with 
        the server. The method is asynchronous, allowing it to handle
        multiple connections concurrently without blocking the event loop."""
        await self.accept() #self refers to the instance of the EchoConsumer class. The accept() method is called to accept the WebSocket connection, allowing communication between the client and server.

    async def receive_json(self, content, **kwargs): #channels calls recerve() when a connected browser send a message
        if not isinstance(content, dict): 
            await self.send_json({
                "type": "error",
                "message": "Send a JSON object",
            })
            return

        if content.get("type") != "chat.message":
            await self.send_json({
                "type": "error",
                "message": "Unsupported message type",
            })
            return
        
        text = content.get("content")

        if not isinstance(text, str): #checks that the instance of the text is a string.
            await self.send_json({
                "type": "error",
                "message": "Message content must be a string",
            })
            return

        text = text.strip()

        if not text:
            await self.send_json({
                "type": "error",
                "message": "Message content cannot be empty",
            })
            return

        if len(text) > 1000:
            await self.send_json({
                "type": "error",
                "message": "Message content cannot exceed 1000 characters",
            })
            return

        await self.send_json({
            "type": "chat.message",
            "content": text,
        })

        """reason for this echoconsumer is to test the websocket connection.
        the exact messages sent by the client are echoed(resent) back to the client.
        just like texting with someone that sends exactly what you sent to them.
        this is useful for testing the websocket connection and ensuring that messages are being sent and received correctly."""


