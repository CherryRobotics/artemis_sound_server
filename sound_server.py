import json
from utils.SWRAP import SWRAP
import logging
from watson_developer_cloud import SpeechToTextV1
logging.basicConfig(level=logging.INFO,
                    format='[%(asctime)s][%(name)s][%(levelname)s] %(message)s',
                    datefmt='%s',)
log = logging.getLogger(__name__)

class sound_server(object):
    def __init__(self):
        self.swrap = SWRAP(mode=SWRAP.STREAM)
        self.swrap.stream_start()
        self.get_key_and_pass()
        self.result = {}
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
            voice, content_type='audio/wav', timestamps=False,
            word_confidence=True
        )
        self.result = result
        # print self.result
        if len(self.result["results"]) >= 1:
            print self.result["results"][0]["alternatives"][0]["transcript"]
        else:
            print "No result"

    def waitforwav(self):
        log.info("Searching for voice")
        wav = self.swrap.listen()
        log.info("Voice found!")
        self.parse_voice(wav)

    def spin(self):
        while True:
            self.waitforwav()


if __name__ == '__main__':
    ss = sound_server()
