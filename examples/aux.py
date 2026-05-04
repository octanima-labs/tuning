from time import sleep

import tunning

logger = tunning.getLogger(__name__)


def my_function() -> None:
    logger.info("Public INFO: Demo has finally started")
    sleep(1)


class MyClass:
    def __init__(self) -> None:
        self.logger = tunning.getLogger(__name__)

    def action(self, action: str) -> None:
        self.logger.critical(f"This is a CRITICAL step: removing generated log files ({action})")
