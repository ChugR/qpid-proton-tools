2018-09-17

Abstract
========

This directory holds some tools and schemes for analyzing an AMQP data
stream when there is a protocol error.

Introduction
===========

Typically dumpcap can capture an AMQP data stream and wireshark can
dissect the stream into AMQP traffic and show the traffic in decoded
AMQP terms. However, the wireshark dissectors sometimes fail to decode
the data stream and wireshark becomes less useful. Rolke's Adverb
decoder relies on wireshark (tshark) to decode the frames so if wireshark
fails then Adverb is equally useless.

Work is progressing on a qpid-dispatch issue where the AMQP data stream
is getting corrupted somehow. Fortunately dumpcap can capture the raw
data stream, corrupted or not, and give it to wireshark. Then wireshark
can export the binary data in a format that has a chance of off-line
evaluation.

There are plenty of other ways to accomplish this same taks. This
project is but one example to help get you started.

Data Acquisition
================

On one of the target systems where the bad data stream is visible
a user may capture the raw network traffic.

    dumpcap -i any -c 5000 -B 2000 -w ~/somedir/file.pcapng

    -i any          : capture on any interface
    -c 5000         : capture 5000 network frames
    -B 2000         : buffer 2000 Mbytes - large buffers hav a better
                      chance of capturing all data frames
    -w file.pacpng  : where to save the data

Capturing the raw data is somewhat fragile. If the networks are too
fast then dumpcap can't get all the data frames. If data frames are
missing then protocol analysis is impossible. Well, maybe not impossible
but subject to too much guessing about what happened. With all the
data positive conclusions may be drawn.

Extracting a Data Stream
========================

Using wireshark, open file.pcapng. Then hunt around for the TCP stream
that contains the AMQP of interest. Use your debugging skilz here to
narrow down what flows have the bad data. If you have two routers and
three clients all running at the same time then there will be many AMQP
connections and traffic flows that must be ignored. Also, not all the
traffic will be going to the 'amqp' port 5672. You will have to use the
wireshark decode-as feature to apply AMQP dissection to flows to other
ports.

Once you have found an interesting data stream, right click it in
wireshark and select Follow -> TCP Stream. A wireshark window will
open showing the traffic for the AMQP link pair involved in the TCP
stream.

It it easier to analyze AMQP traffic in only one direction at a
time. Near the bottom of the window is a pulldown that is selecting
'Entire conversation'. Use that pulldown to select only one direction or
the other.

Use the 'Show and save data as' pulldown to select 'C Arrays' format.
This will produce C source code for the AMQP stream. With this format
there is no binary data in the output stream. It may be difficult to
read binary string data but for getting at the exact bytes in the
AMQP data stream this format is great.

Now select 'Save as ...' to save the C Arrays data into a file. For
this example save the file as 'raw.c'.

Processing the raw data
=======================

Synchronizing the data stream
-----------------------------

Failed AMQP analysis starts with synchronizing with the AMQP frame
stream. It is easiest to start with a data file that does NOT have
the AMQP and SASL initial handshake data. Normal AMQP framing
starts with the first AMQP Open performative.

Look into file 'raw.c' and look for the first few frames that
might start with data like this:

    char peer1_0[] = { /* Packet 78 */
    0x41, 0x4d, 0x51, 0x50, 0x03, 0x01, 0x00, 0x00, 

The first four bytes are literal 'A', 'M', 'Q', 'P' and do not
have the transport framing SIZE bytes. Using an editor delete
those Packet data sections.

Reasonable AMQP frames will start with '0x00, 0x00, 0x??, 0x??',
where the last two bytes are lenghts of the frames. These
frames are normally a few tens or hundereds of bytes.

Save the synchronized data file as 'raw2.c'.


Make single C array for all data
--------------------------------

Wireshark formats the data bytes in a per-frame layout. Each frame
on the network has it's own small byte array. This format is
inconvenient since AMQP traffic will straddle network frame boundaries.

A small python program reads the 'raw2.c' source file and writes
a new source file named 'data.c' In file 'data.c' the bytes are in
an array named 'rewrite_bytes'.

    python rewrite_bytes.py raw2.c data.c

Start looking for AMQP errors
=============================


