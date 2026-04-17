from .karzanddolls import KarzAndDollsScraper
from .giftgalaxy import GiftGalaxyScraper
from .keraladiecastcars import KeralaDialcastCarsScraper
from .kolkatakomics import KolkataKomicsScraper
from .notatoy import NotAToyStubScraper
from .isto64 import Isto64Scraper

SCRAPER_REGISTRY = {
    "karzanddolls":      KarzAndDollsScraper,
    "giftgalaxy":        GiftGalaxyScraper,
    "keraladiecastcars": KeralaDialcastCarsScraper,
    "kolkatakomics":     KolkataKomicsScraper,
    "notatoy":           NotAToyStubScraper,
    "1isto64":           Isto64Scraper,
}
