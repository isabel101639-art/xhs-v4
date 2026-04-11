from crawler_service.providers.mock_provider import MockCrawlerProvider
from crawler_service.providers.playwright_xhs import PlaywrightXHSCrawlerProvider


def build_provider(settings):
    provider_key = (settings.provider or 'mock').strip().lower()
    if provider_key == 'playwright_xhs':
        return PlaywrightXHSCrawlerProvider(settings)
    return MockCrawlerProvider(settings)
