from .karzanddolls import KarzAndDollsScraper
from .giftgalaxy import GiftGalaxyScraper
from .keraladiecastcars import KeralaDialcastCarsScraper
from .kolkatakomics import KolkataKomicsScraper
from .notatoy import NotAToyStubScraper
from .isto64 import Isto64Scraper
from .toymarche import ToyMarcheScraper
from .tooneywheels import TooneyWheelsScraper
from .toyssam import ToysSamScraper
from .playfolio import PlayfolioScraper

SCRAPER_REGISTRY = {
    "karzanddolls":      KarzAndDollsScraper,
    "giftgalaxy":        GiftGalaxyScraper,
    "keraladiecastcars": KeralaDialcastCarsScraper,
    "kolkatakomics":     KolkataKomicsScraper,
    "notatoy":           NotAToyStubScraper,
    "1isto64":           Isto64Scraper,
    "toymarche":         ToyMarcheScraper,
    "tooneywheels":      TooneyWheelsScraper,
    "toyssam":           ToysSamScraper,
    "playfolio":         PlayfolioScraper,
}
