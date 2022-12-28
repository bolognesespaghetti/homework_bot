class NoTokenException(Exception):
    """Отсутствие токена."""
    pass


class EmptyAPIResponse(Exception):
    """Пустой ответ от API."""
    pass


class NoHomework(Exception):
    """Отсутствие домашней работы."""
    pass


class TelegramSendMessageError(Exception):
    """Ошибка при отправке сообщения в телеграм."""
    pass


class UnexpectedHomeworkStatus(Exception):
    """Неожиданный статус домашней работы."""
    pass
