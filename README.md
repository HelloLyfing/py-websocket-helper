# py-websocket-helper
===================

While, I just need several websocket helper funcs, why the hell dozens of **websocket frameworks** appeared as the Google search result ?

## summary
This tiny project just provides three server-side，underlyfing-websocket funcs for you, which are:

 - websocket handshake
 - websocket frame decode( received from the client side )
 - websocket frame encode( string-data to frame )

## quick start

When you need shakehand, pass in the client socket resource:

```
import pywshelper
pywshelper.handshake(cli_sk)
``` 

Fetch msg from received frame:

```
cli_msg = None

frames = cli_sk.recv(2048) # the recv len is up to you

if len(frames) > 0:
    cli_msg = pywshelper.decode_from_frames(frames)

print cli_msg
``` 

Encode str-data into frame:

```
msg = 'hello there !'
frame = pywshelper.encode_to_frames(msg)
# send to client
cli_sk.send(frame)
```

## thanks to:

 - mrrrgn's github [script][github-src-link]

[github-src-link]:https://github.com/mrrrgn/websocket-data-frame-encoder-decoder
