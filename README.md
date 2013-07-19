ffmpeg_live
===========

Wrapper for ffmpeg for live broadcasting

Main example is for taking an RTMP feed to rebroadcast to a local Wowza server. 
Could easily be extended to changed to other delivery formats and also set to take other types of input such as from an SDI card or webcam.

Handles loss of signal by putting up colorbars and waiting for the signal to become available again

There is also a live monitoring script which can monitor streams and if it detects the stream is down then it sends an 
alert via an Amazon SNS (which can go to email etc)
