from flask import Flask, request, jsonify
import logging
from translatepy import Translator

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

sessionStorage = {}


@app.route('/post', methods=['POST'])
def main():
    logging.info('Request: %r', request.json)
    response = {
        'session': request.json['session'],
        'version': request.json['version'],
        'response': {
            'end_session': False
        }
    }
    req = request.json
    handle_dialog(response, request.json)
    logging.info('Response: %r', response)
    return jsonify(response)


def handle_dialog(res, req):
    user_id = req['session']['user_id']
    print(req['request']['original_utterance'])
    if req['request']['original_utterance']:
        translator = Translator()
        ind = req['request']['original_utterance'].lower().index('переведи')
        word = (req['request']['original_utterance']).split()[ind + 1]

        res['response']['text'] = str(translator.translate(word, 'English'))
        return


if __name__ == '__main__':
    app.run()
