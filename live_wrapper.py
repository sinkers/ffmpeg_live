#!/usr/bin/python
'''
A script to wrap ffmpeg for restreaming a live stream

If it can't pick up the main source then it should show colour bars

Things to look for in output to confirm stream running:
Duration: N/A, start: 0.020000, bitrate: 786 kb/s
    Stream #0:0: Video: h264 (Baseline), yuv420p, 640x360 [SAR 1:1 DAR 16:9], 655 kb/s, 25 tbr, 1k tbn, 50 tbc
    Stream #0:1: Audio: aac, 44100 Hz, stereo, fltp, 131 kb/s

Stream mapping:
  Stream #0:0 -> #0:0 (copy)
  Stream #0:1 -> #0:1 (copy)
Press [q] to stop, [?] for help
'''

import sys
import os
from subprocess import PIPE, Popen
from threading  import Thread
import atexit
import time
import logging

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(message)s',
                    handlers=[logging.FileHandler("encoder.log"),
                              logging.StreamHandler()])

FFMPEG = "/usr/local/bin/ffmpeg"
FFPROBE = "/usr/local/bin/ffprobe"
RTMP_SRC = ""
RTMP_SRC = ""
RTMP_DEST = ""

STREAM_RUNNING = "Press [q] to stop"

FFSMPTE = FFMPEG + " -re -f lavfi -i smptebars  -s 640x360 -g 25 -c:v libx264 \
        -b:v 500k -an -f flv " + RTMP_DEST
FFCMD = FFMPEG + " -i " + RTMP_SRC + \
        " -map 0 -c:v copy -c:a copy -f flv " + RTMP_DEST

try:
    from Queue import Queue, Empty
except ImportError:
    from queue import Queue, Empty  # python 3.x

logging.info("Starting")

ON_POSIX = 'posix' in sys.builtin_module_names

def process_line(std, q):
    partialLine = ""
    tmpLines=[]
    end_of_message = False
    while (True):
        data = std.read(10)
        
        #print repr(data)
        
        #break when there is no more data
        if len(data) == 0:
            end_of_message = True

        #data needs to be added to previous line
        if ((not "\n" in data) and (not end_of_message)):
            partialLine += data
        #lines are terminated in this string
        else:
            tmpLines = []

            #split by \n
            split = data.split("\n")

            #add the rest of partial line to first item of array
            if partialLine != "":
                split[0] = partialLine + split[0]
                partialLine = ""

            #add every item apart from last to tmpLines array
            if len(split) > 1:
                for i in range(len(split)-1):
                    tmpLines.append(split[i])

            #last item is '' if data string ends in \r
            #last line is partial, save for temporary storage
            if split[-1] != "":
                partialLine = split[-1]
            #last line is terminated
            else:
                tmpLines.append(split[-1])
            
            #print split[0]
            q.put(split[0])
            if (end_of_message):
                #print partialLine
                break

def enqueue_output(stdout, queue):
    #for line in iter(stdout.readline, b''):
    #    queue.put(line)
    process_line(stdout, queue)  
    stdout.close()

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def probe(stream):
    probeq = Queue()
    logging.info("Checking " + stream)
    probeproc = run(probeq, FFPROBE + " " + stream, "probethread")
    # Need to read from the queue until the queue is empty and process has exited
    while (True):
        #print "Queue not empty"
#        print probeq.join()
        try:
            line = probeq.get_nowait()
            #logging.info(line)
            '''
            Possible error responses:
            Server error: Failed to play stream
            Input/output error
            '''
           
            if ("Stream #0:0: Video" in line):
                logging.info("Found stream " + stream)
                logging.info(line)
                return True
            elif ("error" in line):
                return False
            
        except Empty:
            pass
        
    
    return False

def run(q, ffcmd, thread_name):
    logging.info("Running " + ffcmd)
    p = Popen(ffcmd,shell=True, stderr=PIPE, stdin=PIPE, bufsize=1, close_fds=ON_POSIX)
    #q = Queue()
    #t = Thread(target=enqueue_output, args=(p.stdout, q))
    #t.daemon = True # thread dies with the program
    #t.start()
    t = Thread(target=enqueue_output, name=thread_name, args=(p.stderr, q))
    t.daemon = True
    t.start()
    return p

mainq = Queue()
mainencode = run(mainq, FFCMD, "mainencode")
colorbars = None
colorq = Queue()
colorbarson = False

while (True):
    # Check if process has died and restart
    if (not mainencode.poll() == None):
        logging.error("Main stream not available")
        
        feed_available = probe(RTMP_SRC)
        
        '''
        If stream not running then put up colour bars in one process
        Wait for x seconds
        Check if stream running (use ffprobe), if it is then kill the colour bar process and start main encode
        else do nothing
        '''

        # Only run colorbars if not main feed not available running and colorbars not running
        if (not feed_available and not colorbarson):
            logging.info("Starting color bars")
            colorbars = run(colorq, FFSMPTE, "colorbars")
            colorbarson = True
        # If the feed is now available and colorbars is running the terminate colorbars and start main
        elif (feed_available and colorbarson):
            logging.info("Terminating colorbars")
            colorbars.terminate()
            colorbarson = False
            mainencode = run(mainq, FFCMD,"mainencode")
        elif (feed_available and not colorbarson):
            mainencode = run(mainq, FFCMD,"mainencode")
               
    else: # got line
        try:  
            while (not mainq.empty()):
                line = mainq.get_nowait() # or q.get(timeout=.1)
                if (STREAM_RUNNING in line):
                    logging.info("Stream has started " + RTMP_DEST)
                logging.info(line)
        except Empty:
            pass
        except KeyboardInterrupt:
            mainencode.terminate()
            raise
        # ... do something with line
    
    time.sleep(1)

#p.communicate(input="q")
#p.terminate()
sys.exit()