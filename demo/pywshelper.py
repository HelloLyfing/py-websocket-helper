"""
websocket helper doing 
  handshake
  frame encoding( before send frame )
  frame decoding( after recv frame ) 
work for you
"""

import re
import random
from hashlib import sha1
from base64 import b64encode

def decode_from_frames(frames, mask = True):
    wholebuf = bytearray( frames )
    # The min header size is two bytes, so anything less is FUBAR.
    if len(wholebuf) < 2:
        raise Exception("Broken-Frame: HEADER DATA")

    # in case of that you need frame_info, it's here
    frame_info = {}
    frame_info['fin'] = wholebuf[0] >> 7
    frame_info['opcode'] = wholebuf[0] & 0b1111
    frame_info['pload_len'] = wholebuf[1] & 0b1111111
    frame_info['mask'] = wholebuf[1] >> 7

    # Trim header off the data buffer.
    buf = wholebuf[2:]
    tmp_len = 0
    # payload length can denote different things depending on its value:
    if frame_info['pload_len'] < 126:
        tmp_len = frame_info['pload_len']

        if mask:
            # 32 bit mask + 16 bit header
            frame_len = 6 + tmp_len
        else:
            # just 16 bit header
            frame_len = 2 + tmp_len

        # Sanity checking the buffer sizes against header fields.
        if frame_len > len(wholebuf):
            raise Exception("Broken-Frame: FRAME DATA")
        if len(buf) < 4 and mask:
            raise Exception("Broken-Frame: KEY DATA")

        if mask:
            # the mask key value
            mask_key = buf[:4]
            # strip the mask key from the buffer
            buf = buf[4:4+len(buf)+1]
        else:
            # no mask so we're good to go
            buf = buf[:tmp_len]

    # A payload_length of 126 indicates that payload size is
    # actually stored in a 16 bit 'extended payload' field.
    elif frame_info['pload_len'] == 126:
        # Sanity check.
        if len(buf) < 6 and mask:
            raise Exception("Broken-Frame: KEY DATA")

        # Concatenate the next two bytes into a single 16 bit int.
        for k, i in [(0, 1), (1, 0)]:
            tmp_len += buf[k] * 1 << (8*i)

        if mask:
            # 16 bit extended + 16 bit header + 32 bit mask
            frame_len = 8 + tmp_len
        else:
            frame_len = 4 + tmp_len

        # Sanity check.
        if frame_len > len(buf):
            raise Exception("Broken-Frame: FRAME DATA")

        # Strip the remaining header data from the buffer.
        buf = buf[2:]
        if self.mask:
            mask_key = buf[:4]
            buf = buf[4:4+len(buf)+1]
        else:
            buf = buf[:tmp_len]

    # A payload length of 127 indicates a 64 bit extended payload length
    else:

        # Sanity check.
        if len(buf) < 10 and mask:
            raise Exception("Broken-Frame: KEY DATA")

        # Concatenate the next 8 bytes into a 64 bit integer.
        for k, i in [(0, 7), (1, 6), (2, 5), (3, 4), (4, 3), (5, 2), (6, 1), (7, 0)]:
            tmp_len += buf[k] * 1 << (8*i)

        if self.mask:
            # 16 bit header + 64 bit extended payload + 32 bit mask
            frame_len = 14 + tmp_len
        else:
            frame_len = 10 + tmp_len

        # Sanity check.
        if frame_len > len(buf):
            raise Exception("Broken-Frame: FRAME DATA")

        # Strip remaining header data from the buffer.
        buf = buf[8:]
        if mask:
            mask_key = buf[:4]
            buf = buf[4:4+len(buf)+1]
        else:
            buf = buf[tmp_len]

    # everything remaining is just the payload/message
    msg = buf
    
    if not mask: return msg

    decoded_msg = bytearray()
    for i in range(tmp_len):
        # Each byte in the message should be not-ored against a
        # byte of the mask key.  The mask key byte rotates via modulus.
        c = msg[i] ^ mask_key[i % 4]
        decoded_msg.append(c)

    return decoded_msg

def encode_to_frames(msg, mask = False):
    """
    Build frame from scratch.
    """
    
    def encode_msg(buf, key = None):
        """ Apply a mask to some message data."""
        encoded_msg = bytearray()
        for i in range(len(buf)):
            c = buf[i] ^ key[i % 4]
            encoded_msg.append(c)
        return encoded_msg

    frame = bytearray()

    # Generate a mask key: 32 random bits.
    if mask:
        key = [(random.randrange(1, 255)) for i in range(4)]

    # Build the first byte of header.
    ##
    # The first byte indicates that this is the final data frame
    # opcode is set to 0x1 to indicate a text payload.
    frame.append(0x81)  # 1 0 0 0 0 0 0 1

    # Build rest of the header and insert a payload.

    # How we build remaining header depends on buf size.
    msg_len = len(msg)

    if msg_len < 126:
        msg_header = msg_len  # prepare the payload size field

        if mask:
            # set the mask flag to 1
            frame.append(msg_header + (1 << 7))
        else:
            frame.append(msg_header)

        # Apply a mask and insert the payload.
        if mask:
            frame.extend(key)  # insert the mask key as a header field
            frame.append(self.encode_msg(buf, key))
        else:
            frame += bytearray(msg)
        return frame

    # If the buffer size is greater than can be described by 7 bits but
    # will fit into 16 bits use an extended payload size of 16 bits
    if msg_len <= ((1 << 16) - 1):

        if mask:
            # Make the payload field (7 bits 126) and set the mask flag
            frame.append(126 + (1 << 7))
        else:
            # No need to set the mask flag.
            frame.append(126)

        # Convert the buffer size into a 16 bit integer
        for i in range(1, 3):
            msg_header = (msg_len >> (16 - (8*i))) & (2**8 - 1)
            frame.append(msg_header)

        # Insert the payload and apply a mask key if necessary
        if mask:
            frame.extend(key)
            frame.append(encode_msg(msg, key))
        else:
            frame += msg
        return frame

    # If the buffer length can only be described by something larger than
    # a 16 bit int, extended payload will be 64 bits.
    if msg_len <= ((1 << 64) - 1):

        # Same as previous except with a payload field indicating 64 bit
        # extended playload header.
        if mask:
            frame.append(127 + (1 << 7))
        else:
            frame.append(127)

        for i in range(1, 9):
            # Make the buffer size a 64 bit int.
            msg_header = (msg_len >> (64 - (8*i))) & (2**8 - 1)
            frame.append(msg_header)

        # Prepare/insert the payload.
        if mask:
            frame.extend(key)
            frame.append(encode_msg(msg, key))
        else:
            frame += bytearray(msg)
        return frame

def handshake( socket ):
    magic = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    data = socket.recv(1024).strip()
    key_match = re.search(r'Sec-WebSocket-Key:\s?(.*)\r', data)
    if not key_match:
        raise Exception("Broken-Frame: KEY DATA")
        return False

    key = key_match.group(1)
    digest = b64encode( sha1(key + magic).digest() )
    
    response = 'HTTP/1.1 101 Switching Protocols\r\n'
    response += 'Upgrade: websocket\r\n'
    response += 'Sec-WebSocket-Version: 13\r\n'
    response += 'Connection: Upgrade\r\n'
    response += 'Sec-WebSocket-Accept: %s\r\n\r\n' % digest
    socket.send(response);
    
    return True
