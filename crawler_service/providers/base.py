from abc import ABC, abstractmethod


class BaseCrawlerProvider(ABC):
    def __init__(self, settings):
        self.settings = settings

    @property
    def name(self):
        return self.__class__.__name__

    async def healthcheck(self):
        return {
            'provider': self.name,
            'ready': True,
        }

    @abstractmethod
    async def fetch_account_posts(self, payload):
        raise NotImplementedError

    @abstractmethod
    async def fetch_trends(self, payload):
        raise NotImplementedError
