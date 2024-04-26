from flask import Flask, request, jsonify
import logging
import random
import requests

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

cities = {
    'москва': ['1540737/2894c590796fd3076441', '1533899/2f77c7cc982f0ac961d3', '1533899/ab5f38d5f3ed3b2ce296'],
    'нью-йорк': ['997614/f2b057aba5c1844bff83', '1540737/8ff7f9ad5123b333ba8c', '1652229/d9a58990b0f4abc31c67'],
    'париж': ['937455/79e2f262cbd06e2fa876', '1521359/8857301fbc989dc37a48', '1030494/a2f42a7fa2cbe832eaf0']
}

sessionStorage = {}


def get_country(city_name):
    try:
        url = "https://geocode-maps.yandex.ru/1.x/"
        params = {
            "apikey": "40d1649f-0493-4b70-98ba-98533de7710b",
            'geocode': city_name,
            'format': 'json'
        }
        data = requests.get(url, params).json()

        return data['response']['GeoObjectCollection'][
            'featureMember'][0]['GeoObject']['metaDataProperty'][
            'GeocoderMetaData']['AddressDetails']['Country']['CountryName']
    except Exception as e:
        return e


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
    if req['request']['original_utterance'] == 'Помощь':
        response['response']['text'] = 'Вы должны угадать город по фото, а затем его страну'
        return jsonify(response)
    handle_dialog(response, request.json)
    if 'buttons' not in response['response']:
        response['response']['buttons'] = []
    response['response']['buttons'].append({"title": "Помощь", "hide": True})
    logging.info('Response: %r', response)
    return jsonify(response)


def handle_dialog(res, req):
    user_id = req['session']['user_id']
    if req['session']['new']:
        res['response']['text'] = 'Привет! Назови своё имя!'
        sessionStorage[user_id] = {
            'first_name': None,
            'game_started': False
        }
        return

    if sessionStorage[user_id]['first_name'] is None:
        first_name = get_first_name(req)
        if first_name is None:
            res['response']['text'] = 'Не расслышала имя. Повтори, пожалуйста!'
        else:
            sessionStorage[user_id]['first_name'] = first_name
            sessionStorage[user_id]['guessed_cities'] = []
            res['response']['text'] = f'Приятно познакомиться, {first_name.title()}. Я Алиса. Отгадаешь город по фото?'
            res['response']['buttons'] = [
                {
                    'title': 'Да',
                    'hide': True
                },
                {
                    'title': 'Нет',
                    'hide': True
                }
            ]
    else:
        if not sessionStorage[user_id]['game_started']:
            if 'да' in req['request']['nlu']['tokens']:
                if len(sessionStorage[user_id]['guessed_cities']) == 3:

                    res['response']['text'] = 'Ты отгадал все города!'
                    res['end_session'] = True
                else:

                    sessionStorage[user_id]['game_started'] = True

                    sessionStorage[user_id]['attempt'] = 1

                    play_game(res, req)
            elif 'нет' in req['request']['nlu']['tokens']:
                res['response']['text'] = 'Ну и ладно!'
                res['end_session'] = True
            else:
                if req['request']['original_utterance'] == 'Покажи город на карте':
                    res['response']['text'] = 'Вот. Сыграем ещё?'
                else:
                    res['response']['text'] = 'Не поняла ответа! Так да или нет?'
                res['response']['buttons'] = [
                    {
                        'title': 'Да',
                        'hide': True
                    },
                    {
                        'title': 'Нет',
                        'hide': True
                    }
                ]
        else:
            play_game(res, req)


def play_game(res, req):
    user_id = req['session']['user_id']
    attempt = sessionStorage[user_id]['attempt']
    if attempt == 1:

        city = random.choice(list(cities))

        while city in sessionStorage[user_id]['guessed_cities']:
            city = random.choice(list(cities))

        sessionStorage[user_id]['city'] = city

        res['response']['card'] = {}
        res['response']['card']['type'] = 'BigImage'
        res['response']['card']['title'] = 'Что это за город?'
        res['response']['card']['image_id'] = cities[city][attempt - 1]
        res['response']['text'] = 'Тогда сыграем!'
    elif attempt == -1:

        city = sessionStorage[user_id]['city']
        country = get_country(city)
        if country.lower() in req['request']['original_utterance'].lower():

            res['response']['text'] = 'Правильно! Сыграем ещё?'
            res['response']['buttons'] = [
                {'title': 'Покажи город на карте', 'url': f'https://yandex.ru/maps/?mode=search&text={city}',
                 'hide': True}]
            sessionStorage[user_id]['guessed_cities'].append(city)
            sessionStorage[user_id]['game_started'] = False
        else:

            res['response']['text'] = 'Нет( Попробуй ещё раз'
        return
    else:

        city = sessionStorage[user_id]['city']

        if get_city(req) == city:

            res['response']['text'] = 'Правильно! Теперь отгадай страну'
            res['response']['buttons'] = [
                {'title': 'Покажи город на карте', 'url': f'https://yandex.ru/maps/?mode=search&text={city}',
                 'hide': True}]
            sessionStorage[user_id]['attempt'] = -1
            return
        else:

            if attempt == 4:

                res['response']['text'] = f'Вы пытались. Это {city.title()}. Сыграем ещё?'
                sessionStorage[user_id]['game_started'] = False
                sessionStorage[user_id]['guessed_cities'].append(city)
                return
            else:

                res['response']['card'] = {}
                res['response']['card']['type'] = 'BigImage'
                res['response']['card']['title'] = 'Неправильно. Вот тебе дополнительное фото'
                res['response']['card']['image_id'] = cities[city][attempt - 1]
                res['response']['text'] = 'А вот и не угадал!'

    sessionStorage[user_id]['attempt'] += 1


def get_city(req):
    for entity in req['request']['nlu']['entities']:

        if entity['type'] == 'YANDEX.GEO':
            return entity['value'].get('city', None)


def get_first_name(req):
    for entity in req['request']['nlu']['entities']:

        if entity['type'] == 'YANDEX.FIO':
            return entity['value'].get('first_name', None)


if __name__ == '__main__':
    app.run()
