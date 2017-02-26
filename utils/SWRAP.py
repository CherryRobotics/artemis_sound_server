
#------------------------------------------------------------------------------
# SWRAP.py
#------------------------------------------------------------------------------
# Software Recording and Processing class is a helper class
# to record audio in real time and send to the cloud selection
# of choice. by default it will set to wit.ai.
#
# This was inspired by
# http://www.swharden.com/wp/2016-07-19-realtime-audio-visualization-in-python/
# and his work.
#
#------------------------------------------------------------------------------
# Author: Kadyn Martinez (kadyn_martinez@hotmail.com)
#------------------------------------------------------------------------------
import pyaudio
import time
import numpy as np
import logging
import wave
import cStringIO
from array import array
from struct import pack
import matplotlib.pyplot as plt
log = logging.getLogger(__name__)

class TapeRecorder(object):
    def __init__(self, chunk=4096, rate=44100, tapeLength=2):
        self.chunk = chunk
        self.tapeLength = tapeLength
        self.rate = rate
        self.tape = np.empty(self.rate*self.tapeLength, dtype='<h')*0
    ### TAPE
    # "tape is like a circular magnetic ribbon of tape that's continously
    # recorded and recorded over in a loop. self.tape contains this data.
    # the newest data is always at the end. Don't modify data on the type,
    # but rather do math on it (like FFT) as you read from it."

    def tape_add(self, data):
        """ add a single chunk to the tape. """
        # self.tape[:-self.chunk] = self.tape[self.chunk:]
        # self.tape[-self.chunk:] = data
        self.tape = np.append(self.tape, data)
        log.debug("Adding chunk to tape")

    def tape_flush(self):
        """ completely fill tape with new data """
        # readsInTape = int(self.rate*self.tapeLength/self.chunk)
        # log.info (" Flushing %d s tape with %dx%.2f ms reads"%\
        #         (self.tapeLength, readsInTape, self.chunk/self.rate))
        # for i in range(readsInTape):
        #     self.tape_add()
        self.tape = np.empty(self.rate*self.tapeLength, dtype='<h')*0

    def get_tape(self):
        return self.tape



class SWRAP(object):
    STREAM = 0
    FILE_OUT = 1
    def __init__(self, device=None, startStreaming=False, threshold=2000,
                 mode=1):
        log.info(" Starting SWRAP")

        self.chunk = 4096 # num of data points to read at a time
        self.rate = 44100 # time resolution of the recording stream
        self.threshold = threshold # threshold for considering silence
        # The threshold for trigger is more than the threshold for trimming
        # due to variences in tone while speaking.
        self.trim_threshold = self.threshold/3

        self.mode = mode

        # for tape recording (continuous 'tape' of recent audio)
        self.tape = TapeRecorder()
        self.tape_is_recording = False # Is the tape being written to?

        self.p = pyaudio.PyAudio() # Start py audio class
        if startStreaming:
            self.stream_start()

    def stream_read(self):
        """ Returns values for a single chunk """
        data = np.fromstring(self.stream.read(self.chunk), dtype=np.int16)
        return data

    def stream_start(self):
        """ Connect to the audio device and start a stream """
        log.info(" Stream started!")
        self.stream = self.p.open(format=pyaudio.paInt16, channels=1,
                                  rate=self.rate, input=True,
                                  frames_per_buffer=self.chunk)

    def stream_stop(self):
        """ Close the stream but keep the pyaudio instance alive. """
        if 'stream' in locals():
            self.stream.stop_stream()
            self.stream.close()
        log.info(" Stream closed!")

    def close(self):
        """ gently detach from everything """
        self.stream_stop()
        self.p.terminate()

    def visualization(self):
        pass
        # while(True):
        #     if not self.is_silent(self.stream_read()):
        #         self.console_visualize()

    def console_visualize(self):
        data = self.stream_read()
        # data = np.fromstring(stream.read(CHUNK),dtype=np.int16)
        peak=np.average(np.abs(data))*2
        bars="#"*int(50*peak/2**16)
        log.info("%05d %s"%(peak,bars))

    def is_silent(self, data):
        """ returns true if below silent threshold """
        if max(data) < self.threshold:
            return True
        return False

    def normalize(self, data):
        """average the volume out"""
        maximum = 16384
        times = float(maximum)/max(abs(i) for i in data)
        log.debug("TIMES: %f" % times)

        ## bulding np arrays in inefficient. so we're making a list
        ## then converting it to np arrays
        r = array('h')
        for i in data:
            r.append(int(i*times))
        r = np.asarray(r, dtype='<h')
        return r

    def trim(self, data):
        # def _trimside(self, data):
        datacop = array('h')
        for chunk in data:
            if abs(chunk) > self.trim_threshold:
                datacop.append(chunk)
            else:
                datacop.append(0)
        # The array now has a bunch of 0's at the beginning and end

        return np.trim_zeros(np.asarray(datacop, dtype='<h'))

    def add_silence(self, data, seconds_of_silence):
        # I'm not too sure this is needed yet..
        pass

    def export_tape_to_file(self):
        wav = self.tape.get_tape()
        wav = self.clean_tape(wav)
        # self.plot(wav)
        sample_width = self.p.get_sample_size(pyaudio.paInt16)
        path = "cassette.wav"
        wav = pack('<' + ('h'*len(wav)), *wav)

        wav_writer = wave.open(path, 'wb')
        wav_writer.setnchannels(1)
        wav_writer.setsampwidth(sample_width)
        wav_writer.setframerate(self.rate)
        wav_writer.writeframes(wav)
        wav_writer.close()
        log.info("wav exported")
        self.tape.tape_flush()

    def pack_for_web(self):
        wav = self.tape.get_tape()
        wav = self.clean_tape(wav)
        wav = self.np2array(wav)
        sample_width = self.p.get_sample_size(pyaudio.paInt16)
        wavpack = cStringIO.StringIO()
        wav_writer = wave.open(wavpack, 'wb')
        wav_writer.setnchannels(1)
        wav_writer.setsampwidth(sample_width)
        wav_writer.setframerate(self.rate)
        wav_writer.writeframes(wav)
        wav_writer.close()
        log.info("Wav packed")
        self.tape.tape_flush()
        return wavpack.getvalue()

    def clean_tape(self, wav):
        wav = self.normalize(wav)
        wav = self.trim(wav)
        # wav = self.add_silence(wav, 0.5)

        return wav

    def listen(self):
        self.tape.tape_flush() # clear tape
        self.tape_is_recording = False
        num_silent = 0 # number of hits silent TODO: Get this to host seconds.
        while True:
            chunk_data = self.stream_read()
            silent = self.is_silent(chunk_data)

            # If we triggered recording and it's silent, increment.
            if silent and self.tape_is_recording:
                num_silent += 1
            # If we haven't triggered recording, and it's not silent,
            # begin to record.
            elif not silent and not self.tape_is_recording:
                self.tape_is_recording = True
                log.info("Triggered recording")
                num_silent = 0
            # If we're recording and not silent, reset the silent counter
            # this means we're not done yet.
            elif not silent and self.tape_is_recording:
                num_silent = 0

            # if we're actively recording, and it's been silent for a
            # prolonged period of time, we can assume we've captured
            # the entire sentence.
            if self.tape_is_recording and num_silent > 15:
                self.tape_is_recording = False # turn off the tape recorder.
                log.info("Recording stopped")
                if self.mode is self.FILE_OUT:
                    self.export_tape_to_file()
                elif self.mode is self.STREAM:
                    return self.pack_for_web()

            # if we're recording, write to the tape recorder.
            if self.tape_is_recording:
                self.tape.tape_add(chunk_data)

    def plot(self, data):
        plt.plot(data)
        plt.show()

    def array2np(self, array, dtype='<h'):
        return np.asarray(array, dtype)

    def np2array(self, nparr, dtype='h'):
        arr = array(dtype)
        for i in nparr:
            arr.append(i)
        return arr


if __name__ == '__main__':
    rap = SWRAP(threshold=2000, mode=SWRAP.FILE_OUT)
    rap.stream_start()
    rap.listen()
