from voicerag.application.logging_config import configure_logging


def test_configure_logging_does_not_raise():
    configure_logging()
