# DECISIONS – autonomiset päätökset ja oletukset

Projekti toteutettiin täysin automaattisesti Spec Kitillä (2026-11-09). Alla jokainen itse tehty
päätös, oletus ja ohitus.

## Työkalut ja ympäristö

1. **Spec Kit alustettiin** komennolla `specify init --here --integration claude --script ps
   --ignore-agent-tools`. `--ignore-agent-tools` tarvittiin, koska `claude`-CLI ei ollut PATHissa
   (sovellus ajetaan Claude-työpöytäsovelluksesta). PowerShell-skriptit valittiin, koska kohde on Windows.
2. **Spec Kit -skillit ajettiin käsin**: `.claude/skills/speckit-*` -tiedostot asentuivat kesken
   istunnon, joten niiden ohjeet luettiin ja vaiheet tehtiin samoin askelin (constitution → specify →
   clarify → plan → tasks → implement).
3. **Python**: koneella ei ole `python`-komentoa PATHissa, mutta `uv` on. Kehitys ja testit ajettiin
   uv:n Python 3.13:lla virtuaaliympäristössä `.venv`. `setup.bat` käyttää uv:tä, jos se löytyy, ja
   muuten `py`/`python`-komentoa.
4. **Gitiä ei alustettu**: käyttäjä ei pyytänyt committeja. `.gitignore` on silti valmiina (`.env`,
   tietokanta, `.venv`), jotta avaimet eivät päädy versionhallintaan, jos git otetaan käyttöön.

## Clarify-vaiheen vastaukset

5. **Yhteinen asteikko 1–5** (1 Myy, 2 Vähennä, 3 Pidä, 4 Lisää, 5 Osta). Se vastaa suomalaista
   viisiportaista käytäntöä, ja Finnhubin strongSell…strongBuy kuvautuu siihen suoraan.
   Kolmiportaiset lähteet (buy/hold/sell) → 5/3/1.
6. **Konsensus** = analyytikkomäärillä painotettu keskiarvo. Finnhubin rivi edustaa N analyytikkoa
   (N = määrien summa), Inderesin rivi yhtä analyytikkoa. Konsensusluokka saadaan pyöristämällä
   puolikkaat ylöspäin (esim. 3,5 → Lisää).
7. **Nousuvara** = painotettu keskitavoitehinta / kurssi − 1, vain kurssin valuutassa olevista
   tavoitehinnoista. Jos arvo puuttuu, nousuvara jää tyhjäksi ja osake järjestetään loppuun.
8. **Kurssi**: käytetään tuoreinta haettua kurssia mistä tahansa lähteestä. Lähde näytetään.
9. **Tuoreus** = osakkeen uusimman suosituksen päivämäärä.
10. **Osakejoukko** = muokattava `config/watchlist.toml`, oletuksena 40 Helsingin pörssin yhtiötä.
    Kaikkia Inderesin noin 1 900 yhtiötä ei haeta, jotta palvelua ei kuormiteta.
11. **Suodatin "lähde"** rajaa konsensuslaskennan valittuihin lähteisiin (ei pelkästään rivejä).
12. **Muutos** = saman lähteen ja analyytikon kaksi peräkkäistä snapshotia, joissa yhtenäistetty
    suositusluokka tai tavoitehinta eroaa. Luokan nousu on nosto, lasku on lasku, ja pelkkä
    tavoitehinnan muutos näytetään omana tyyppinään.
13. **Muutosnäkymän oletusikkuna** on 30 päivää (valittavissa 7–365).
14. **Päivitys** käynnistetään vain napista, ajastusta ei ole (ohjeen mukaisesti).

## Datalähteet

15. **Finnhub**: avain luetaan `.env`:stä (`FINNHUB_API_KEY`) ja välitetään `X-Finnhub-Token`
    -otsakkeessa, jolloin se ei näy URL:eissa eikä lokeissa. Käytössä ovat endpointit
    recommendation, quote, profile2 ja price-target. Kutsujen väli on vähintään 1,05 s (60/min).
16. **Finnhubin rajoitteet**: ilmainen taso kattaa pääosin USA:n osakkeet, ja price-target on
    premium-ominaisuus. Helsingin `.HE`-tunnukset voivat siksi palauttaa 403:n. Adapteri lopettaa
    endpointin kutsumisen kolmen peräkkäisen 403:n jälkeen ja näyttää syyn lähteen tilassa. Tätä
    **ei voitu testata oikealla avaimella**, koska avainta ei ollut. Testit käyttävät mockattuja
    vastauksia.
17. **Finnhubin linkki alkuperään**: Finnhubilla ei ole julkista osakekohtaista sivua, joten linkki
    osoittaa endpointin dokumentaatioon (esim. https://finnhub.io/docs/api/recommendation-trends).
18. **Demotila**: `demo`-lähde on käytössä vain, kun `FINNHUB_API_KEY` puuttuu. Se tuottaa
    deterministisen esimerkkidatan ja -historian, ja kaikki demon rivit on merkitty "DEMO". Kun avain
    lisätään, demo poistuu käytöstä ja sen rivit suodatetaan pois näkymistä automaattisesti, koska
    näkymät näyttävät vain käytössä olevat lähteet. Inderes hakee oikeaa dataa myös demotilassa.
19. **Inderes – virallinen rajapinta**: julkista API:a tai syötettä ei löytynyt. Premiumin
    MCP-palvelin on kirjautumisen takana, joten sitä ei käytetä.
20. **Inderes – robots.txt ja käyttöehdot**: robots.txt sallii kaiken (`Allow: /`). Käyttöehdot
    sallivat aineiston katselun ja lataamisen omaan, henkilökohtaiseen, ei-kaupalliseen käyttöön.
    Kiellettyjä ovat uudelleenjakelu, julkinen esittäminen, kaupallinen käyttö ja palvelun
    merkittävä kuormittaminen. Automaattista hakua ei kielletä erikseen. → **Toteutettiin**
    henkilökohtaiseen käyttöön näillä rajoituksilla: vain seurantalistan osakkeet, 1,5 s viive
    pyyntöjen välillä, tunnistettava User-Agent, haku vain napista, data pysyy paikallisena ja lähde
    sekä linkki näkyvät aina. Adapterin voi poistaa käytöstä asetuksella `INDERES_ENABLED=false`.
21. **Inderes – mitä luetaan**: julkisen yrityssivun HTML:ään upotettu `__NEXT_DATA__`-JSON
    (suositus, tavoitehinta, päivämäärä, analyytikko, kurssi, valuutta, toimiala). Sivun sisäistä
    GraphQL-rajapintaa ei kutsuta suoraan, koska sitä ei ole julkaistu käytettäväksi.
22. **Inderes – ohitettu osa**: `analyst-consensus`-sivua (muiden pankkien konsensus, Vara Research)
    ei käytetä. Kyse on lisensoidusta kolmannen osapuolen datasta, ja sen käytön sallittavuus on
    epäselvä.
23. **Inderesin asteikko**: koodi 1–5 tulkitaan 1=Myy … 5=Osta. Tulkinta varmistettiin Nokian sivulta
    (koodi 2 ja sivulla "reduce"-värinen suosituspilleri).
24. **OP, Nordea ja muut kirjautumisen takana olevat lähteet** jätettiin pois perustuslain
    mukaisesti.

## Toteutus

25. **Lähteiden automaattinen löytö**: `stock_eagle/sources/` skannataan `pkgutil`:lla. Uusi lähde
    vaatii vain uuden tiedoston ja tarvittaessa tunnisteen seurantalistaan, mikä on konfiguraatiota
    eikä koodimuutos.
26. **Historia** tallennetaan snapshotteina, joiden sormenjälki on muotoa
    lähde|osake|analyytikko|päivä|suositus|tavoite. Sama tieto uudelleen päivittää vain
    `last_seen_at`:n.
27. **Hakuajankohta**: tietueessa näytetään `last_seen_at`, eli milloin tieto viimeksi vahvistettiin
    lähteestä. Lähteen tilassa näytetään viimeisimmän ajon aika.

## Testaus ja varmistus

28. **Testit**: 77 pytest-testiä, verkkokutsut estetty `conftest.py`:ssä. Inderes-parsinta
    testataan synteettisellä sivulla, jolla on sama rakenne. Inderesin sisältöä ei kopioitu
    fixtureksi.
29. **Ajonaikainen tarkistus** 2026-11-09: sovellus käynnistettiin (Streamlit, localhost:8501) ja
    Päivitä-nappi ajettiin. Demo tuotti 264 snapshotia, ja Inderes 41 suositusta 44 osakkeesta.
    Konecranes, Hiab ja Citycon: sivulta löytyi kurssi mutta ei voimassa olevaa suositusta, joten
    ne näkyvät vain muiden lähteiden kautta. Tämä jätettiin ennalleen.
30. **Korjattu virhe**: osakenäkymän historiataulukon "Tavoite"-sarakkeessa sekoittuivat tekstit
    ja luvut, mikä aiheutti Arrow-sarjallistusvirheen. Sarake muotoillaan nyt aina tekstiksi.
31. **Remote Control** kytkettiin päälle käyttäjän viestin "claude rc" perusteella. Se ei liity
    sovellukseen.

## Finnhub oikealla avaimella (2026-11-09)

32. **Avain** luettiin käyttäjän tiedostosta `Apikey.txt` ja kopioitiin `.env`:iin
    (`FINNHUB_API_KEY`). Avainta ei tulostettu. `Apikey.txt` lisättiin `.gitignore`:en.
    Suositus: poista `Apikey.txt`, koska avain on nyt `.env`:ssä.
33. **Havainto**: ilmainen taso palauttaa 403 kaikille `.HE`-tunnuksille (recommendation, quote,
    price-target, profile2). Yhtiön USA-tunnus (ADR/OTC) palauttaa kuitenkin saman yhtiön
    analyytikkokonsensuksen: esim. `NOK` → vastauksen `symbol` = `NOKIA.HE`.
34. **Ratkaisu**: seurantalistaan lisättiin 20 yhtiölle tarkistettu USA-tunnus. Kukin tunnus
    tarkistettiin API:sta niin, että vastauksen symboli osoittaa oikeaan yhtiöön. Hylätyt, koska
    Finnhub yhdisti ne väärään yhtiöön: MTTRY (Metso → CEC.DE), HOKCY (Huhtamäki → 3.HK) ja
    SNMRF (Sanoma → SRG.MI). Kemiralle, Terveystalolle, Reveniolle, Cityconille, Mandatumille,
    Kalmarille ja Hiabille ei löytynyt toimivaa tunnusta. Telian TLSNY osoittaa `TELIA.ST`:hen,
    joka on sama yhtiö, joten se hyväksyttiin.
35. **ADR-tunnuksista haetaan vain suositukset**: ADR:n kurssi ja tavoitehinta ovat USD:nä per
    ADR, ja ADR-suhde voi poiketa 1:1:stä, joten niitä ei käytetä. Kurssi tulee Inderesiltä (EUR).
36. **Helsingin osakkeelle ilman finnhub-tunnusta Finnhubia ei kutsuta.** Aiempi oletus
    `<TICKER>.HE` poistettiin, koska se tuotti pelkkiä 403-vastauksia.
37. **Tulos**: päivitys onnistui, Finnhub 80 snapshotia (20 yhtiötä × 4 kk) ja Inderes 41.
    Demotila kytkeytyi automaattisesti pois.

## Julkaisu puhelinkäyttöä varten (2026-11-09)

38. **Väliaikainen puhelinnäkymä**: yksityinen claude.ai-sivu (tilannekuva CSV-tiedostoista),
    https://claude.ai/artifact/SUdn8SWCGwNQjqF3a5fnyV. Se ei päivity itse.
39. **GitHub**: koodi pushattiin repoon `rynnakkosika/Stock-Eagle` (käyttäjän luoma, julkinen).
    Ennen committia varmistettiin, ettei avain, `.env`, `Apikey.txt` tai tietokanta ole mukana.
    Git-identiteetiksi asetettiin repokohtaisesti `rynnakkosika` /
    `rynnakkosika@users.noreply.github.com`, koska globaalia ei ollut.
40. **Streamlit Cloud**: `app.py` kopioi `st.secrets`-arvot ympäristömuuttujiksi, joten avain
    annetaan Streamlitin Secrets-kenttään eikä koskaan repoon. Tilin luonti, kirjautuminen ja
    avaimen syöttö jäävät käyttäjälle. Sovellus kannattaa asettaa yksityiseksi Inderesin ehtojen
    vuoksi.

## Lisälähteiden selvitys (2026-11-09)

41. **Placera (Avanza)**: **ei toteutettu.** robots.txt sallii haun, mutta käyttöehdot
    (forum.placera.se/villkor, koskevat myös placera.se:tä) kieltävät suoraan kaikki robotit,
    spiderit, scraperit ja muut automaattiset työkalut (pl. suuret hakukoneet).
42. **Affärsvärlden**: **ei toteutettu.** robots.txt sallii haun (Crawl-delay 15), mutta ehdot
    sallivat aineiston käytön vain "palvelun normaalin käytön puitteissa" ja henkilökohtaiseen
    käyttöön. Automaattista hakua ei kielletä eikä sallita suoraan, joten sallittavuus on
    epäselvä (periaate I). Lisäksi kattavuus on pääosin Ruotsin osakkeissa.
43. **Muut ulkomaiset API:t**: EODHD:n analyytikkodata on maksullista. Alpha Vantagen
    ilmaistasolla (25 kutsua/vrk) ei ole selkeää analyytikkodataa. TipRanksilla ja Benzingalla ei
    ole käyttökelpoista ilmaista API:a. Näitä ei toteutettu.
44. **Financial Modeling Prep (FMP)**: **toteutettu** virallisena API:na
    (`stock_eagle/sources/fmp.py`), käytössä kun `FMP_API_KEY` on asetettu.
    - Endpointit `grades-consensus` (suositusmäärät) ja `price-target-consensus` (tavoite).
    - Tunnusjärjestys: `ids.fmp` → `<TICKER>.HE` → Finnhubin USA-tunnus (ADR). Jos kolme
      ensimmäistä `.HE`-kutsua evätään, `.HE` ohitetaan loppuajon ajan, jotta 250/vrk kiintiö
      säästyy. ADR-tunnukselta haetaan vain suositukset, ei tavoitehintaa (USD per ADR).
    - FMP vaatii avaimen URL-parametrina, joten avain poistetaan kaikista virheviesteistä
      (`***`). Tämä on testattu.
    - Grades-consensus ei kerro päivämäärää, joten suosituksen päivä = hakupäivä.
    - **Huomio**: FMP ja Finnhub voivat laskea osittain samoja analyytikoita, jolloin
      konsensuksen painotus ja suositusten määrä kasvavat. Lähdesuodattimella voi tarkastella
      kumpaakin erikseen.
    - **Ei testattu oikealla avaimella**: käyttäjällä ei vielä ole FMP-avainta. Testit
      käyttävät mockattuja vastauksia.
45. **Salaisuudet pilvessä**: `app.py` kopioi nyt kaikki Streamlitin Secrets-arvot
    ympäristömuuttujiksi, joten uuden lähteen avain ei vaadi koodimuutosta (periaate IV).
