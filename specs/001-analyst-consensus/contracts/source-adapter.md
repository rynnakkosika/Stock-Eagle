# Contract: SourceAdapter

Uusi lähde = uusi tiedosto `stock_eagle/sources/<nimi>.py`, jossa luokka perii `SourceAdapter`:n.
Rekisteri löytää sen automaattisesti; muuhun koodiin ei tehdä muutoksia.

```python
class SourceAdapter(ABC):
    id: str            # pysyvä tunniste, esim. "finnhub"
    name: str          # näyttönimi
    homepage: str      # lähteen etusivu

    def availability(self, settings: Settings) -> tuple[bool, str]:
        """(käytössä?, syy). Esim. puuttuva API-avain."""

    def fetch(self, stocks: list[Stock], settings: Settings) -> SourceResult:
        """Hae data. Ei saa nostaa poikkeusta yksittäisen osakkeen virheestä;
        kirjaa virheet SourceResult.errors-listaan."""
```

`SourceResult`: `recommendations: list[Recommendation]`, `quotes: list[Quote]`,
`stock_info: list[StockInfo]`, `errors: list[str]`, `notes: list[str]`.

Adapterin vastuulla on yhtenäistää suositus asteikolle 1–5 `stock_eagle.scale`-apufunktioilla ja
asettaa jokaiselle tietueelle `url`. Lähdekohtainen tunniste luetaan seurantalistan
`ids.<adapter id>`-kentästä, tai adapteri johtaa sen tickeristä (`default_symbol`).
