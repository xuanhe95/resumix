from abc import ABC, abstractmethod


class BasePage(ABC):
    def __init__(
        self,
    ):
        pass

    @abstractmethod
    def render(self):
        pass
