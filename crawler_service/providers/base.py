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
            'supports_account_views': False,
            'supports_account_exposures': False,
            'supports_trend_views': False,
            'supports_trend_hot_value': False,
            'metric_notes': '',
        }

    @abstractmethod
    async def fetch_account_posts(self, payload):
        raise NotImplementedError

    @abstractmethod
    async def fetch_trends(self, payload):
        raise NotImplementedError
