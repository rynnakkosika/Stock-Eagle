# Research: Analyytikkosuositusten koontinäkymä

## R1 Finnhub (ilmainen taso)

- **Decision**: Käytetään `/stock/recommendation` (kuukausittaiset strongBuy/buy/hold/sell/strongSell
  -määrät), `/quote` (kurssi), `/stock/profile2` (nimi, toimiala, valuutta) ja yritetään
  `/stock/price-target` (tavoitehinta). Avain otsakkeessa `X-Finnhub-Token`.
- **Rationale**: Virallinen API. Recommendation trends -data on kuukausittainen, joten se tuottaa
  suoraan historian.
- **Rajoitteet**: Price target on Finnhubissa premium-ominaisuus, ja ilmainen taso kattaa
  pääasiassa USA:n osakkeet. Helsingin `.HE`-tunnukset voivat palauttaa 403:n. Adapteri lopettaa
  saman endpointin kutsumisen kolmen peräkkäisen 403:n jälkeen ja raportoi syyn lähteen tilana.
  Kutsujen väli on vähintään 1,05 s (60/min).
- **Alternatives**: Yahoo Finance (ei virallista API:a, käyttöehdot kieltävät), Alpha Vantage (ei
  analyytikkosuosituksia ilmaiseksi).

## R2 Inderes

- **Virallinen rajapinta**: Julkista API:a tai RSS/datasyötettä suosituksille ei löytynyt. Premium-
  tilaukseen kuuluu MCP-palvelin tekoälysovelluksille → kirjautumisen takana, ei käytetä.
- **robots.txt** (haettu 2026-11-09): `User-agent: * / Allow: /`, sitemapit julkisia.
- **Käyttöehdot** (inderes.fi/fi/kayttoehdot): oikeus katsella ja ladata aineistoja omaan,
  henkilökohtaiseen, ei-kaupalliseen käyttöön; kielletty muokkaus, julkinen esittäminen,
  uudelleenjakelu, kaupallinen käyttö ja palvelun merkittävä kuormittaminen. Automaattista hakua ei
  erikseen kielletä.
- **Decision**: Toteutetaan. Yrityssivun (`/companies/<slug>`) julkisesta HTML:stä luetaan sivuun
  upotettu `__NEXT_DATA__`-JSON: suositus (1–5), tavoitehinta, päivämäärä, kurssi, valuutta, toimiala,
  analyytikko. Vain seurantalistan osakkeet, 1,5 s viive, User-Agent tunnistaa sovelluksen, vain
  käyttäjän käynnistämä haku, data jää paikalliseksi. Lähde ja linkki näytetään aina.
- **Ei toteuteta**: `analyst-consensus`-sivu (muiden pankkien konsensus, Vara Research) – lisensoitua
  kolmannen osapuolen dataa, jonka julkisuus/sallittavuus on epäselvä.
- **Asteikko**: Inderesin numerokoodi 1=Myy, 2=Vähennä, 3=Pidä, 4=Lisää, 5=Osta (varmistettu: Nokia
  koodi 2 ↔ sivun "reduce"-värinen suosituspilleri).

## R3 Konsensus ja nousuvara

- Painotettu keskiarvo analyytikkomäärillä; luokka pyöristämällä (x.5 ylöspäin).
- Keskitavoitehinta painotettuna analyytikkomäärillä, vain kurssin valuutassa.
- Nousuvara = tavoite / kurssi − 1.

## R4 Historia

- Snapshotit tallennetaan sormenjäljellä (lähde, osake, analyytikko, päivä, suositus, tavoite);
  uudelleenhaku samalla datalla päivittää vain `last_seen_at`:n. Muutokset johdetaan peräkkäisistä
  snapshoteista.
