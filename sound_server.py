import json
from utils.SWRAP import SWRAP
import logging
import threading
from watson_developer_cloud import SpeechToTextV1
logging.basicConfig(level=logging.INFO,
                    format='[%(asctime)s][%(name)s][%(levelname)s] %(message)s',
                    datefmt='%s',)
log = logging.getLogger(__name__)

class WatsonPrediction(object):
    def __init__(self, resultjson=None):
        self.word_confidences = None
        self.confidence = None
        self.transcript = None
        self.timestamps = None
        if resultjson:
            if len(resultjson["results"]) > 0:
                alts = resultjson["results"][0]["alternatives"][0]
                self.word_confidences = alts["word_confidence"]
                self.confidence = alts["confidence"]
                self.transcript = alts["transcript"]
                self.timestamps = alts["timestamps"]

class sound_server(object):
    def __init__(self):
        self.swrap = SWRAP(threshold=4  000, mode=SWRAP.STREAM)
        self.swrap.stream_start()
        self.get_key_and_pass()
        self.result = WatsonPrediction()
        self.watsonstt = SpeechToTextV1(
            username=self.username,
            password=self.password,
            x_watson_learning_opt_out=False
        )
        log.info("Watson activated")
        self.spin()

    ##### Set up #####
    def get_key_and_pass(self):
        log.info("getting key")
        with open("login.key", 'r') as f:
            keys = json.loads(f.read())
        self.username = keys['username']
        self.password = keys['password']

    ##### SpeechToText #####
    def parse_voice(self, voice):
        result = self.watsonstt.recognize(
            voice, content_type='audio/wav', timestamps=True,
            word_confidence=True
        )
        self.result = WatsonPrediction(result)

    def waitforwav(self):
        while True:
            log.info("Searching for voice")
            wav = self.swrap.listen()
            log.info("Voice found!")
            self.parse_voice(wav)

    def spin(self):
        thread = threading.Thread(target=self.waitforwav)
        thread.start()
        while True:
            if self.result.transcript:
                print self.result.transcript
                self.result = WatsonPrediction()


if __name__ == '__main__':
    ss = sound_server()
