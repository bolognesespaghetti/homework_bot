import logging
import os
import sys
import time
from json.decoder import JSONDecodeError
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv
from exception import (EmptyAPIResponse, 

                       NoHomework, NoTokenException,

                       TelegramSendMessageError, 
                       
                       UnexpectedHomeworkStatus)

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s - %(name)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)


def check_tokens():
    """Функция проверки токенов."""
    tokens = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    for i in range(len(tokens)):
        if not tokens[i]:
            logger.critical(f'Отсутствует переменная окружения {tokens[i]}.')
            raise NoTokenException(f'Отсутствует токен {tokens[i]}')
    logger.debug('Все токены прошли проверку.')
    return all(tokens)


def send_message(bot, message):
    """Функция отправки сообщения в телеграм-бота."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.debug(
            f'Пользователю с id {TELEGRAM_CHAT_ID} '
            f'отправлено сообщение {message}'
        )
    except telegram.TelegramError as error:
        logger.error('Ошибка при отправки сообщения в телеграмм')
        raise TelegramSendMessageError(error)


def get_api_answer(timestamp):
    """Функция отправки запроса к API.
    Возвращает запрос в формате json.
    """
    try:
        payload = {'from_date': timestamp}
        request = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=payload
        )
    except requests.RequestException as error:
        logger.warning(error)
        raise requests.exceptions(error)
    if request.status_code != HTTPStatus.OK:
        logger.error('Статус запроса к API не 200')
        raise requests.RequestException('Статус запроса к API не 200')
    logger.info('Ответ от API получен.')
    try:
        request.json()
    except JSONDecodeError:
        logger.error('Ответ не преобразуется JSON')
    return request.json()


def check_response(response):
    """Функция проверяющая содержимое запроса.
    Возвращает домашнюю работу по ключу.
    """
    if not isinstance(response, dict):
        logger.error('Полученный ответ не является словарём')
        raise TypeError('Полученный ответ не является словарём')
    if 'homeworks' not in response:
        logger.error('Пустой ответ от запроса к API')
        raise EmptyAPIResponse('Пустой ответ от запроса к API')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError('Ключ запроса не является списком')
    if not len(homeworks) != 0:
        raise NoHomework('Нет домашней работы')
    logger.info('Домашнаяя работа получена по ключу')
    return homeworks[0]


def parse_status(homework):
    """Функция прасинга статуса домашней работы.
    Возвращает готовый ответ для сообщения бота.
    """
    current_status = homework.get('status')
    if current_status not in HOMEWORK_VERDICTS:
        logger.error('Неожиданный статус работы')
        raise UnexpectedHomeworkStatus('Неожиданный статус работы')
    verdict = HOMEWORK_VERDICTS.get(homework.get('status'))
    homework_name = homework.get('homework_name')
    if not homework_name:
        logger.info('При парсинге не найдена домашняя работа')
        raise KeyError('При парсинге не найдена домашняя работа')

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота.
    Выполняется в порядке:
    1. Проверка токинов.
    2. Запрос к API
    3. Проверка корректности ответа
    4. Если ответ корректен происходит отправка сообщения
    5. Если ответ некорректен происходит отправка исключений.
    """
    if not check_tokens():
        sys.exit('Нет токинов')
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            query = get_api_answer(timestamp=timestamp)
            response = check_response(query)
            if response:
                get_message = parse_status(response)
                send_message(bot=bot, message=get_message)
        except TelegramSendMessageError as error:
            logger.exception(error)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot=bot, message=message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
