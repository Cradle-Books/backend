# Learning Django: databases, WebSockets, and ASGI

Django's ORM (Object-Relational Mapper) is the Python interface you use to work with your database.

Most commands start with `Model.objects`, which gives you access to queries for that model.

## Open the Django shell

From the `backend` directory, run:

```powershell
python manage.py shell
```

Import the models:

```python
from django.contrib.auth import get_user_model
from Azaniah.chat.models import Conversation, Message

User = get_user_model()
```

`get_user_model()` returns the user model configured for your project.

Select two existing test users, replacing these placeholders with their actual usernames:

```python
user1 = User.objects.get(username="first_username")
user2 = User.objects.get(username="second_username")
```

## Common methods

| Method | What it does | Example |
|---|---|---|
| `.create()` | Creates and saves a record | `Conversation.objects.create()` |
| `.all()` | Retrieves all matching records | `Message.objects.all()` |
| `.get()` | Retrieves exactly one record | `Message.objects.get(id=1)` |
| `.filter()` | Retrieves records matching conditions | `Message.objects.filter(sender=user1)` |
| `.values()` | Retrieves selected fields as dictionaries | `Message.objects.values("id", "content")` |
| `.exists()` | Checks whether any matching record exists | `Message.objects.filter(sender=user1).exists()` |
| `.count()` | Counts matching records | `conversation.messages.count()` |

The ID `1` in these examples is illustrative; use an ID that exists in your database.

## Retrieving one record versus a collection

```python
message = Message.objects.get(id=1)
```

`.get()` returns one `Message` object. It raises `Message.DoesNotExist` if there are no matches, or `Message.MultipleObjectsReturned` if there are multiple matches. A primary key such as `id` is unique, so querying by it cannot return multiple matches.

```python
messages = Message.objects.filter(sender=user1)
```

`.filter()` returns a **QuerySet**: a collection of matching records. Having no matches is fine—it returns an empty QuerySet.

## Combining query methods

```python
list(
    Message.objects
    .filter(sender=user1)
    .values("id", "content")
)
```

Read this as: "Find messages sent by `user1`, select their IDs and content, then display the results."

- `.filter(sender=user1)` selects the matching messages.
- `.values("id", "content")` returns those fields as dictionaries instead of model objects.
- `list(...)` evaluates the QuerySet and produces a Python list that the shell displays.

## Creating a conversation and linking participants

```python
conversation = Conversation.objects.create()
```

`.create()` creates and immediately saves the conversation. Its `created_at` timestamp is filled automatically.

```python
conversation.participants.add(user1, user2)
```

`.add()` works on relationships, such as your conversation's participants. This links existing users to the conversation; it does not create new users.

A many-to-many relationship stores its links in a separate database table. The conversation must be saved first so Django has its ID to use when linking users.

```python
conversation.participants.remove(user2)
```

`.remove()` removes the relationship. The user still exists in the database.

Add the participant back before continuing:

```python
conversation.participants.add(user2)
```

## Creating and updating a message

```python
message = Message.objects.create(
    conversation=conversation,
    sender=user1,
    content="Hello! What are you reading?",
)
```

Each argument fills a field in the `Message` model. Passing `conversation` and `user1` tells Django which records the foreign keys should reference.

To change the message:

```python
message.content = "I started a new book."
message.save()
```

The first line changes the Python object. `.save()` writes that change to the database.

## Querying through a relationship

```python
conversation.messages.all()
```

This retrieves messages belonging to this conversation. `.messages` is available because the `conversation` foreign key uses `related_name="messages"`.

```python
list(
    conversation.messages.values(
        "sender__username",
        "content",
        "created_at",
    )
)
```

`sender__username` follows the `sender` relationship to retrieve that user's username. The double underscore lets queries traverse relationships.

With `ordering = ["created_at", "id"]` in the message model's `Meta` class, results are sorted by creation time, then ID.

These shell commands write directly to the database. They do not automatically check that the sender belongs to the conversation. Our chat handling code will enforce that rule later.

## Practice exercises

Use your test conversation to try the following:

1. Count its messages.
2. Retrieve only messages in that conversation sent by `user2`.
3. Display just those messages' content using `.values()`.
4. Create another message and edit its content using `.save()`.

Try writing the queries yourself before looking back at the examples.

## Why our chat needs WebSockets

Think of a normal HTTP request as asking a librarian a question: you ask for a book, the librarian answers, and that interaction finishes. Your browser uses requests like this to fetch pages and API data.

For chat, we want a conversation that stays available. A WebSocket is like keeping a walkie-talkie switched on: either side can speak when it has something to say. Technically, it supports communication in both directions over an established connection. [WebSocket API reference](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API)

| HTTP request and response | WebSocket |
|---|---|
| Useful for fetching message history | Useful for receiving new messages live |
| Browser requests data, server responds | Either side can send messages after connecting |
| Each request has its own response | One connection can carry many messages |

Finishing an HTTP response does not necessarily close the underlying network connection; browsers can reuse connections. The comparison above describes the application interaction.

Polling is another option: the browser repeatedly asks, "Any new messages?" It is like checking your mailbox every few seconds. WebSockets let the server notify a connected browser when a message arrives.

WebSockets deliver data; they do not provide message history, user accounts, or permissions by themselves. Our Django models store history, and our application checks who may access it.

### Connection lifecycle

1. The browser requests a WebSocket connection.
2. The server evaluates the request and accepts or rejects it.
3. An accepted connection carries messages in both directions.
4. Either side can close it; network interruptions can also end it.

With the usual HTTP/1.1 handshake, the browser asks to upgrade to WebSocket. Local URLs commonly start with `ws://`; encrypted connections use `wss://`. A connection can carry text or binary data. JSON is a format we can choose for our text messages, rather than a requirement of WebSocket itself. [WebSocket protocol events](https://asgi.readthedocs.io/en/stable/specs/www.html)

An example application payload might be:

```json
{"content": "What are you reading?"}
```

Our server will determine the sender from authentication. A browser-supplied sender ID should not be treated as proof of identity.

## ASGI explained from the beginning

**ASGI** stands for **Asynchronous Server Gateway Interface**. It defines how a Python application and a compatible server communicate. The name describes an interface, rather than a separate program you start. [ASGI overview](https://asgi.readthedocs.io/en/stable/introduction.html)

### A child-friendly picture: a school reception desk

Imagine a school where visitors arrive at reception:

- The **browser** is a visitor.
- **Daphne**, our server, is the receptionist who handles arrivals from outside.
- **ASGI** is the agreed form and procedure used to pass information to staff.
- The **router** decides which classroom should handle the visitor's request.
- A **consumer** is the staff member responsible for an ongoing conversation.
- The **database** is the school's record book.

The agreed procedure matters because a receptionist and a teacher must understand the same information. Likewise, an ASGI server and an ASGI application can work together because they follow the same interface.

This analogy describes our planned architecture; it is not a literal explanation of network hardware.

### The words in ASGI

| Word | Meaning in this context |
|---|---|
| Asynchronous | Supports work that can pause while waiting, allowing other tasks to progress |
| Server | Software that accepts incoming network traffic |
| Gateway | The boundary through which the server communicates with application code |
| Interface | An agreed shape for calls and messages |

### Why we encounter ASGI when adding chat

Django already has an ASGI entry point in `Azaniah/asgi.py`. Adding Channels will let that entry point route WebSocket traffic to our chat handlers while HTTP traffic continues to reach Django views.

Setting `ASGI_APPLICATION` alone does not create a chat endpoint. We still need routing and a consumer. [Django ASGI deployment guide](https://docs.djangoproject.com/en/stable/howto/deployment/asgi/)

## WSGI and ASGI

**WSGI** means **Web Server Gateway Interface**. Its standard application interface is synchronous and organized around an HTTP request and response. ASGI introduces an asynchronous event interface suitable for HTTP and longer conversations such as WebSockets. [ASGI introduction](https://asgi.readthedocs.io/en/stable/introduction.html)

Imagine WSGI as a reception form for one question and answer. ASGI also supports a running conversation log, with new events arriving over time.

| Detail | WSGI | ASGI |
|---|---|---|
| Application interface | Synchronous callable | Asynchronous callable |
| Communication model | Request and response | Connection context plus events |
| Standard WebSocket handling | Not provided by WSGI | Supported through its WebSocket specification |
| Django entry point | `Azaniah/wsgi.py` | `Azaniah/asgi.py` |

A WSGI server can still handle many users using workers or threads. ASGI does not mean every line of our code runs in parallel, and it does not automatically make slow code fast.

## Understanding asynchronous Python

Imagine making snacks for three children. While one snack is warming, you can pour another child's drink instead of standing still. That is the useful idea behind asynchronous I/O: make progress elsewhere while waiting.

```python
async def wait_for_message():
    event = await receive()
    return event
```

This is a conceptual fragment: `receive` would need to be supplied by the surrounding application.

- `async def` defines a coroutine function.
- Calling it produces a coroutine object; it needs to be awaited or scheduled to run.
- `await receive()` waits for an event, allowing the event loop to run other ready tasks when the operation suspends.
- Once an event arrives, execution resumes and assigns it to `event`.
- `return event` gives that result to the caller.

The **event loop** coordinates ready tasks, like a teacher moving between children as they become ready for help. `await` does not automatically start a background thread. [Python coroutines and tasks](https://docs.python.org/3/library/asyncio-task.html)

Long CPU calculations and blocking calls can hold up an event loop. In an async consumer, synchronous database work needs an appropriate adapter such as `database_sync_to_async`, or suitable asynchronous ORM methods. Channels also offers synchronous consumers for code that primarily uses synchronous APIs. [Consumer guidance](https://channels.readthedocs.io/en/stable/topics/consumers.html)

## The three inputs of an ASGI application

An ASGI application has this signature:

```python
async def application(scope, receive, send):
    ...
```

The server supplies three inputs:

| Input | Purpose | School analogy |
|---|---|---|
| `scope` | A dictionary describing the request or connection | The visitor's information card |
| `receive` | An async callable for getting the next incoming event | Listening for the next update |
| `send` | An async callable for sending an outgoing event | Passing an instruction to reception |

For HTTP, the application scope covers one request. For WebSocket, it covers the connected socket's lifetime. Incoming messages arrive as events rather than being stored in `scope`. [ASGI specification](https://asgi.readthedocs.io/en/latest/specs/main.html)

### `scope`: context for the interaction

A simplified illustration is:

```python
{
    "type": "websocket",
    "path": "/ws/chat/",
}
```

Actual scopes contain additional protocol information. Middleware and routing can add context such as an authenticated user or matched URL parameters. An authenticated user is not automatically supplied merely because a connection uses ASGI.

### `receive`: the next event

```python
event = await receive()
```

The event might announce a connection attempt, contain a message, or report disconnection.

### `send`: an outgoing instruction

```python
await send({"type": "websocket.send", "text": "Hello!"})
```

This asks the server to transmit text on an accepted socket. It does not save a message or prove the recipient read it. [WebSocket send event specification](https://asgi.readthedocs.io/en/stable/specs/www.html)

## Following ASGI events through a connection

The following is a simplified illustration, not code to paste into the project:

```text
Browser asks to connect
    Server delivers: websocket.connect
    Application sends: websocket.accept

Browser sends "Hello"
    Server delivers: websocket.receive
    Application sends: websocket.send

Connection ends
    Server delivers: websocket.disconnect
```

These names describe ASGI events exchanged between the server and Python application. They are different from a JSON payload's own fields such as `content`. [ASGI WebSocket event definitions](https://asgi.readthedocs.io/en/stable/specs/www.html)

When our consumer uses `await self.accept()` or `await self.send(...)`, Channels handles the corresponding low-level event details for us.

## What Channels and Daphne each do

**Daphne** accepts HTTP and WebSocket network traffic and communicates with our application using ASGI. Think of it as the receptionist handling the outside connection. [Daphne project documentation](https://github.com/django/daphne/)

**Channels** gives our Django project tools for routing connections and writing consumers. It lets us organize behavior into methods rather than manually handling every ASGI event. [Channels consumer documentation](https://channels.readthedocs.io/en/stable/topics/consumers.html)

A consumer typically has these methods:

| Method | When it runs | Example responsibility |
|---|---|---|
| `connect()` | A connection is requested | Check access, then accept or reject |
| `receive(...)` | A message arrives | Validate content and process it |
| `disconnect(close_code)` | The connection ends | Clean up connection-specific state |

A consumer instance represents a connection, not an entire stored conversation. Two browser tabs can create two connections for the same user.

## How the pieces fit in our project

```text
Browser
   |
   | HTTP or WebSocket traffic
   v
Daphne
   |
   | ASGI calls and events
   v
Azaniah/asgi.py: application
   |
   +-- HTTP ------> Django URL routing ------> Views
   |
   +-- WebSocket -> WebSocket URL routing ---> Chat consumer
                                                  |
                                                  v
                                         Conversation / Message
                                              database records
```

This diagram shows the intended arrangement once we add WebSocket routing. Your existing `asgi.py` initially provides Django's HTTP application; a consumer and WebSocket routes are still needed.

### What a channel layer adds later

An echo handler can reply directly on its own socket. Delivering a message to other connections needs a way to notify those handlers. A **channel layer** provides communication between application instances, and groups let us address several connected channels together.

Think of a school intercom: one classroom can notify another without sharing the same desk. Redis can back this communication when application instances run in separate processes. An in-memory layer is useful for local experimentation but does not communicate across processes. The channel layer is optional, and is separate from our durable message database. [Channel layers](https://channels.readthedocs.io/en/stable/topics/channel_layers.html)

## Installing the tools: each line explained

Run this from `backend`, with your virtual environment active:

```powershell
python -m pip install "channels[daphne]"
```

- `python` selects the interpreter in your active environment.
- `-m pip` runs that interpreter's package installer.
- `install` requests package installation.
- `channels` is the package name.
- `[daphne]` requests its optional Daphne dependencies; this is package syntax, not a Python list.
- Quotes keep the package expression together as a command argument.

Add `"daphne"` at the beginning of `INSTALLED_APPS` in `Azaniah/settings.py`. Preserve the existing entries:

```python
INSTALLED_APPS = [
    "daphne",
    # Keep all existing app entries here.
]
```

The comment is a placeholder, not a replacement for your apps. Putting Daphne first gives its ASGI-capable `runserver` command precedence. [Channels installation instructions](https://channels.readthedocs.io/en/stable/installation.html)

Add this setting in the same file:

```python
ASGI_APPLICATION = "Azaniah.asgi.application"
```

Read the dotted path from left to right:

- `Azaniah` is the project package.
- `asgi` is the `asgi.py` module inside that package.
- `application` is the callable exposed by that module.

This tells Channels where to load the root application. It does not start a server. Keep the existing `WSGI_APPLICATION` setting; the server you launch determines which entry point is used. [Django's ASGI application](https://docs.djangoproject.com/en/stable/howto/deployment/asgi/)

Finally, run:

```powershell
python manage.py check
```

This runs Django's system checks. Passing them is useful, but does not prove a WebSocket route works. We will test an actual connection after adding the consumer and routing.

## Reading the existing `asgi.py`

The original entry point has this general shape:

```python
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Azaniah.settings")

application = get_asgi_application()
```

- `import os` provides access to environment settings.
- The import from Django supplies the function that builds its ASGI handler.
- `os.environ.setdefault(...)` chooses the settings module if one has not already been set.
- `get_asgi_application()` initializes Django and returns its HTTP ASGI application.
- Assigning it to `application` exposes the entry point the server loads.

When we add routing, we will initialize Django before importing routing code that might import models. This avoids loading models before Django's application registry is ready. [Channels ASGI setup](https://channels.readthedocs.io/en/stable/installation.html)

## What we will build next

Our first exercise will be an echo connection: send text from a browser and receive the same text back. It teaches connection handling without adding database operations immediately.

After that, we will add authentication, check conversation membership, save messages, and notify the other participant. In this project, JWTs identify Django authentication users, so the sender will come from that authenticated identity.

## Check your understanding

Try answering these in your own words:

1. Why does fetching old messages fit HTTP well, while receiving new messages fits WebSocket?
2. In the school analogy, which part is Daphne and which part is ASGI?
3. How does `scope` differ from an event returned by `receive()`?
4. Does `await` mean Python starts a new thread?
5. Does sending a WebSocket message also save it to the database?
6. Why does `ASGI_APPLICATION` point to a Python object rather than a URL?
7. Why will we still need to check conversation membership after authenticating a user?

## Our working echo WebSocket

We successfully tested the echo connection on port **8001**. Our actual app folder is `Azaniah/chatapp`, so use that name in imports rather than the earlier example name `Azaniah/chat`.

An echo sends back exactly what you send it. It confirms this path works:

```text
Browser -> Daphne -> ASGI router -> EchoConsumer -> Browser
```

It does not yet save messages, authenticate users, or deliver messages to another participant.

### Step 1: the consumer

File: `backend/Azaniah/chatapp/consumers.py`

```python
from channels.generic.websocket import AsyncWebsocketConsumer


class EchoConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()

    async def receive(self, text_data=None, bytes_data=None):
        if text_data is not None:
            await self.send(text_data=text_data)
```

Line by line:

- The import brings in Channels' asynchronous WebSocket consumer base class.
- `class EchoConsumer(AsyncWebsocketConsumer)` inherits its connection-handling tools.
- `async def connect(self)` defines what to do when a connection is requested.
- `self` refers to this connection's consumer instance.
- `await self.accept()` accepts the connection.
- `receive(...)` runs when a connected client sends a message.
- `text_data` contains a text message; `bytes_data` contains a binary message. The unused kind is `None`.
- `if text_data is not None` handles text, including an empty string.
- `await self.send(text_data=text_data)` sends that text back through the same connection.

We do not override `disconnect()` yet because we have no custom cleanup to perform. Accepting every connection is appropriate for this local echo exercise; private chat will require authentication and membership checks.

### Step 2: the WebSocket route

File: `backend/Azaniah/chatapp/routing.py`

```python
from django.urls import path
from .consumers import EchoConsumer


websocket_urlpatterns = [
    path("ws/echo/", EchoConsumer.as_asgi()),
]
```

- `path` connects a URL pattern to a handler.
- `.consumers` means the `consumers.py` module in this same package.
- `websocket_urlpatterns` is our list of WebSocket routes.
- `"ws/echo/"` matches the URL path. The `ws/` prefix is a naming convention; the router does not infer a protocol from that prefix.
- `.as_asgi()` supplies an ASGI application that creates a consumer instance for each connection.

### Step 3: connect routing to ASGI

File: `backend/Azaniah/asgi.py`

```python
import os

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Azaniah.settings")

django_asgi_app = get_asgi_application()

from Azaniah.chatapp.routing import websocket_urlpatterns


application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        URLRouter(websocket_urlpatterns)
    ),
})
```

- `ProtocolTypeRouter` chooses an ASGI handler using the connection's `scope["type"]`.
- `URLRouter` chooses a handler using the URL path.
- `AllowedHostsOriginValidator` checks the browser's origin against allowed hosts. This is an origin check, not user authentication.
- `get_asgi_application()` initializes Django before we import our app's routing, which may eventually import models.
- `"http": django_asgi_app` preserves ordinary Django request handling.
- The `"websocket"` branch applies the origin check and then matches the WebSocket URL to our consumer.

Imagine two reception desks: the first asks "What kind of connection?" and the second asks "Which URL?" [Channels routing reference](https://channels.readthedocs.io/en/stable/topics/routing.html)

### Which types can ProtocolTypeRouter choose?

You provide a dictionary mapping scope types to compatible ASGI applications:

| Scope type | Purpose | Example |
|---|---|---|
| `http` | Ordinary HTTP requests | Login or fetching message history |
| `websocket` | Persistent WebSocket connections | Echo or live chat |
| `channel` | Internal Channels worker messages | A background thumbnail task |
| `lifespan` | Startup and shutdown events, where supported | Initializing and closing application resources |

Our project currently routes only `http` and `websocket`. Adding a dictionary entry requires a suitable handler and a server or worker that produces that type of scope; it does not automatically implement a protocol. `channel` is a Channels worker mechanism. `lifespan` is part of ASGI's lifecycle specification. [Channels scope routing](https://channels.readthedocs.io/en/stable/topics/routing.html), [ASGI lifespan](https://asgi.readthedocs.io/en/stable/specs/lifespan.html)

The router selects the application for a connection, rather than choosing a new consumer for each chat message.

### Step 4: start the server

From the `backend` directory:

```powershell
..\.venv\Scripts\python.exe manage.py runserver 8001
```

- `..` means the parent directory, which is `CRADLE` here.
- `.venv\Scripts\python.exe` explicitly uses our project's Python environment.
- `manage.py runserver` starts the development server; with Daphne first in `INSTALLED_APPS`, its ASGI-capable command takes precedence.
- `8001` chooses the listening port.

Leave this terminal running. Use `Ctrl+C` in that terminal to stop the server when finished.

### Step 5: test from the browser

Open `http://localhost:8001/`, then open Developer Tools and select Console. A 404 for the root page is okay if there is no route for `/`; it is separate from our WebSocket endpoint.

Enter:

```javascript
const socket = new WebSocket("ws://localhost:8001/ws/echo/");

socket.onopen = () => {
    console.log("Connected!");
    socket.send("Hello!");
};

socket.onmessage = (event) => console.log("Echo:", event.data);
socket.onerror = (event) => console.log("Error:", event);
socket.onclose = (event) => console.log("Closed:", event.code);
```

- `const socket` stores our browser-side WebSocket object.
- `new WebSocket(...)` begins connecting to the specified server and path.
- `onopen` runs once the connection is established.
- Sending inside `onopen` avoids sending before the socket is ready.
- `onmessage` runs when a message arrives from the server.
- `event.data` contains the received message.
- `onerror` reports a socket error; the backend terminal may provide more detail.
- `onclose` reports that the connection has ended, including its close code.

Expected output:

```text
Connected!
Echo: Hello!
```

After connecting, try another message:

```javascript
socket.send("What are you reading?");
```

Expected output:

```text
Echo: What are you reading?
```

Close it when done:

```javascript
socket.close();
```

Refresh the page before repeating the full example to avoid redeclaring the same `const socket` in the console.

## Troubleshooting we encountered

### WebSocket handshake returned 404

We saw:

```text
Error during WebSocket handshake: Unexpected response code: 404
```

This means a server answered the connection request with an HTTP 404 instead of establishing the WebSocket. Possible causes include the wrong path, missing WebSocket routing, or reaching a server that is not running the expected ASGI setup.

Our route, consumer, and ASGI configuration looked correct. We then tried restarting the server explicitly with the project's Python environment.

### Port 8000 was already occupied

The restart produced:

```text
Couldn't listen on 127.0.0.1:8000: [WinError 10048]
Only one usage of each socket address (protocol/network address/port) is normally permitted.
```

Another process was already listening on that address and port, so the new server could not bind there. Think of a port as a numbered reception desk: desk 8000 was already occupied.

We did not identify or stop the existing process. Instead, we launched our server on port 8001 and changed both browser addresses accordingly:

```text
Page:      http://localhost:8001/
WebSocket: ws://localhost:8001/ws/echo/
```

The echo worked on 8001. This confirms our intended server and WebSocket route work there; it does not establish exactly which process was answering on 8000.

## Where to resume next time

Completed: models and database practice, Channels/Daphne setup, echo consumer, WebSocket routing, and a successful browser echo test.

Next: move from echoing text to designing authenticated private chat. We will learn how to identify the connected Django user, check conversation membership, and then save and deliver messages. We will continue in small steps with each line explained.
