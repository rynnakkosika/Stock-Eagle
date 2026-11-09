# 🦅 Stock Eagle

Henkilökohtaiseen käyttöön tehty sovellus, joka kokoaa osakkeiden analyytikkosuositukset
(osta / lisää / pidä / vähennä / myy) ja tavoitehinnat useista lähteistä yhteen näkymään ja
järjestää osakkeet. Painopiste on Helsingin pörssissä.

> **Ei sijoitusneuvontaa.** Sovellus vain esittää kolmansien osapuolten julkaisemia tietoja.
> Jokaisen tiedon kohdalla näkyy lähde, linkki alkuperään ja hakuajankohta.

## Käynnistys (Windows)

Vaatimus: Python 3.11+ ([python.org](https://www.python.org/downloads/)) **tai**
[uv](https://docs.astral.sh/uv/).

```bat
setup.bat
```

```bat
run.bat
```

`setup.bat` luo virtuaaliympäristön `.venv`, asentaa riippuvuudet ja kopioi `.env.example` →
`.env`. `run.bat` avaa sovelluksen selaimeen osoitteeseen http://localhost:8501. Paina sivupalkista
**🔄 Päivitä data**.

### Finnhub-avain (valinnainen)

1. Rekisteröidy ilmaiseksi osoitteessa https://finnhub.io/register.
2. Lisää avain `.env`-tiedostoon: `FINNHUB_API_KEY=...`
3. Käynnistä sovellus uudelleen ja paina **Päivitä data**.

Ilman avainta sovellus toimii **demotilassa**: Finnhubin tilalla näytetään selvästi merkittyä
keksittyä esimerkkidataa (lähde *DEMO*). Inderes hakee oikeaa dataa myös demotilassa (voi poistaa
käytöstä: `INDERES_ENABLED=false`).

### Puhelimella: Streamlit Community Cloud (ilmainen)

1. Kirjaudu osoitteessa https://share.streamlit.io GitHub-tunnuksella ja anna Streamlitille pääsy
   repoon `rynnakkosika/Stock-Eagle`.
2. **Create app** → **Deploy a public app from GitHub**: repo `rynnakkosika/Stock-Eagle`,
   branch `main`, main file `app.py`.
3. **Advanced settings**: Python 3.12 tai 3.13. Kirjoita kenttään **Secrets**:
   `FINNHUB_API_KEY = "oma-avaimesi"`
4. **Deploy**. Sovellus saa osoitteen `https://<nimi>.streamlit.app`.
5. Aseta sovellus yksityiseksi kohdassa **Settings → Sharing** ("Only specific people can view
   this app") ja lisää vain oma sähköpostisi. Inderesin ehdot sallivat vain henkilökohtaisen käytön.

Huomio: pilven levy tyhjenee, kun sovellus käynnistyy uudelleen tai nukahtaa. Tällöin paina
**Päivitä data**. Suositushistoria alkaa silloin alusta.

### Testit

```bat
test.bat
```

## Ominaisuudet

- **Paremmuusjärjestys**: konsensussuositus, suositusten määrä, keskitavoitehinta, kurssi ja
  nousuvara %. Järjestys konsensuksen, nousuvaran tai tuoreuden mukaan. Suodattimet lähteen,
  suosituksen ja toimialan mukaan.
- **Osake**: suositukset lähteittäin linkkeineen ja hakuaikoineen, suositushistoria (nostot,
  laskut ja tavoitehinnan muutokset) sekä kaavio.
- **Muutokset**: viimeaikaiset suositus- ja tavoitehintamuutokset (7–365 päivää).
- **Lähteet ja asteikko**: kunkin lähteen tila, viimeisin hakuaika ja yhtenäistetty asteikko
  (5 Osta · 4 Lisää · 3 Pidä · 2 Vähennä · 1 Myy).

Seurattavat osakkeet ovat tiedostossa `config/watchlist.toml` (oletuksena 44 Helsingin pörssin
yhtiötä).

## Rakenne

```
app.py                     Streamlit-käyttöliittymä
stock_eagle/scale.py       asteikkojen yhtenäistys
stock_eagle/consensus.py   konsensus, keskitavoite, nousuvara, järjestys, suodatus
stock_eagle/changes.py     nostojen ja laskujen tunnistus
stock_eagle/db.py          SQLite (data/stock_eagle.db): snapshot-historia, kurssit, hakuajot
stock_eagle/refresh.py     päivitysajo, yhden lähteen virhe ei kaada muita
stock_eagle/sources/       yksi moduuli per lähde (finnhub, inderes, demo)
specs/001-analyst-consensus/  Spec Kit -dokumentit (spec, plan, tasks …)
DECISIONS.md               kaikki autonomiset päätökset ja oletukset
```

### Uuden lähteen lisääminen

Luo `stock_eagle/sources/<nimi>.py` ja siihen luokka, joka perii `SourceAdapter`:n
(`availability()` + `fetch()`). Rekisteri löytää sen automaattisesti, eikä muuhun koodiin tarvita
muutoksia. Lähdekohtaiset tunnisteet voi lisätä seurantalistaan (`ids = { <nimi> = "..." }`).
Sopimus on kuvattu tiedostossa `specs/001-analyst-consensus/contracts/source-adapter.md`.

## Yhteenveto: mitä tehtiin

- Spec Kit alustettiin, ja vaiheet constitution → specify → clarify → plan → tasks → implement
  käytiin läpi (`.specify/memory/constitution.md`, `specs/001-analyst-consensus/`).
- Toteutettiin Finnhub-adapteri (recommendation trends, quote, profile, price target), demotila ja
  Inderes-adapteri (julkiset yrityssivut). Inderes toteutettiin, koska robots.txt ja käyttöehdot
  sallivat henkilökohtaisen käytön. Perustelut ovat DECISIONS.md:ssä.
- Toteutettiin ranking-, osake- ja muutosnäkymät, Päivitä-nappi ja lähteiden hakuajat.
- Tehtiin 79 pytest-testiä (asteikko, konsensus, nousuvara, järjestys, muutokset, tietokanta,
  adapterien parsinta ja päivitysajo), jotka eivät tee verkkokutsuja. Kaikki menevät läpi.
- Sovellus käynnistettiin ja testattiin selaimessa: demodata ja oikea Inderes-haku (41/44 osaketta
  sai suosituksen) toimivat.

## Mikä jäi kesken / rajoitukset

- **Finnhubin ilmainen taso estää Helsingin `.HE`-tunnukset.** Ratkaisuna 20 yhtiölle käytetään
  niiden USA-tunnusta (ADR/OTC, esim. `NOK`), joka palauttaa saman yhtiön analyytikkokonsensuksen.
  Näistä haetaan vain suositusmäärät. Tavoitehinnat ja kurssit tulevat Inderesiltä. Kemiralle,
  Terveystalolle, Reveniolle, Cityconille, Mandatumille, Kalmarille, Hiabille, Metsolle,
  Huhtamäelle ja Sanomalle ei löytynyt toimivaa Finnhub-tunnusta.
- Inderesiltä saadaan yksi analyytikon suositus per yhtiö. Muiden pankkien konsensussivua
  (Vara Research) ei käytetä. Konecranesilla, Hiabilla ja Cityconilla ei hakuhetkellä ollut
  Inderes-suositusta.
- Inderes-adapteri lukee sivulle upotettua dataa. Jos Inderes muuttaa sivurakennettaan, haku
  epäonnistuu hallitusti ja virhe näkyy lähteen tilassa.
- Suositushistoria kertyy lähteiden ilmoittamista ajankohdista ja omista hakukerroista. Inderesin
  aiempaa historiaa ei ole saatavilla ennen ensimmäistä hakua.
- Ajastettua automaattista päivitystä ei ole (vain nappi). Git-versionhallintaa ei alustettu.
