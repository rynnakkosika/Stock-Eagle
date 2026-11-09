# Feature Specification: Analyytikkosuositusten koontinäkymä (Stock Eagle)

**Feature Branch**: `001-analyst-consensus`

**Created**: 2026-11-09

**Status**: Clarified

**Input**: User description: "Omaan käyttöön tuleva sovellus, joka kokoaa osakkeiden analyytikkosuositukset
(osta / lisää / pidä / vähennä / myy) ja tavoitehinnat useista lähteistä yhteen näkymään ja järjestää
osakkeet paremmuusjärjestykseen. Painopiste Helsingin pörssissä, laajennettavissa myöhemmin."

## Clarifications

### Session 2026-11-09

Kysymyksiin vastattiin autonomisesti käyttäjän ohjeiden perusteella (ks. DECISIONS.md).

- Q: Mille yhteiselle asteikolle suositukset yhtenäistetään? → A: Viisiportainen numeerinen asteikko
  1–5 (1 = Myy, 2 = Vähennä, 3 = Pidä, 4 = Lisää, 5 = Osta). Viisiportaiset lähteet kuvataan suoraan,
  kolmiportaiset (buy/hold/sell) arvoihin 5/3/1.
- Q: Miten konsensus lasketaan, kun yksi lähde on koostettu usean analyytikon määristä ja toinen on
  yksittäinen analyytikko? → A: Painotettu keskiarvo, jossa kunkin lähteen paino on sen edustamien
  analyytikoiden määrä. Konsensusluokka saadaan pyöristämällä keskiarvo lähimpään portaaseen.
- Q: Miten nousuvara lasketaan, jos tavoitehintoja on eri valuutoissa tai kurssi puuttuu? → A:
  Nousuvara = keskimääräinen tavoitehinta / nykyinen kurssi − 1, vain kurssin valuutassa olevista
  tavoitehinnoista. Jos kurssi tai yhteensopiva tavoitehinta puuttuu, nousuvara näytetään tyhjänä
  ja osake järjestetään listan loppuun.
- Q: Mitkä osakkeet haetaan? → A: Muokattava seurantalista (oletuksena ~40 Helsingin pörssin
  suurinta/seuratuinta yhtiötä), jossa kullekin osakkeelle on lähdekohtaiset tunnisteet.
- Q: Mitä "tuoreus" tarkoittaa järjestämisessä? → A: Osakkeen uusimman suosituksen päivämäärä
  (lähteen ilmoittama, tai jos puuttuu, hakuajankohta).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Paremmuusjärjestetty osakelista (Priority: P1)

Käyttäjä avaa sovelluksen ja näkee seurattavat osakkeet taulukkona: konsensussuositus, suositusten
määrä, keskimääräinen tavoitehinta, nykyinen kurssi ja nousuvara %. Hän voi järjestää listan
konsensuksen, nousuvaran tai tuoreuden mukaan ja suodattaa lähteen, suosituksen ja toimialan mukaan.

**Why this priority**: Sovelluksen ydinarvo – yksi näkymä kaikista suosituksista.

**Independent Test**: Käynnistä sovellus demotilassa ilman API-avainta; listassa näkyy osakkeita
lajiteltuna, ja lajittelu/suodattimet muuttavat näkymää.

**Acceptance Scenarios**:

1. **Given** dataa on haettu, **When** käyttäjä avaa sovelluksen, **Then** näkyy taulukko, jossa
   jokaisella rivillä on konsensus, määrä, keskitavoitehinta, kurssi ja nousuvara.
2. **Given** lista näkyy, **When** käyttäjä valitsee järjestykseksi "nousuvara", **Then** suurin
   nousuvara on ylimpänä ja puuttuvat arvot alimpana.
3. **Given** lista näkyy, **When** käyttäjä suodattaa lähteellä X, **Then** konsensus lasketaan vain
   lähteen X suosituksista ja osakkeet ilman X:n suositusta piilotetaan.

---

### User Story 2 - Päivitys ja hakuajankohta (Priority: P1)

Käyttäjä painaa "Päivitä"-nappia, sovellus hakee kaikista käytössä olevista lähteistä uudet tiedot, ja
näkymässä lukee milloin dataa on viimeksi haettu (lähteittäin).

**Independent Test**: Paina Päivitä; viimeisin hakuaika päivittyy ja virheellinen lähde ei kaada muita.

**Acceptance Scenarios**:

1. **Given** sovellus on auki, **When** käyttäjä painaa Päivitä, **Then** jokainen lähde haetaan ja
   kunkin lähteen hakuaika ja tila (ok / virhe + syy) näytetään.
2. **Given** yksi lähde epäonnistuu, **When** päivitys ajetaan, **Then** muut lähteet päivittyvät ja
   aiempi data säilyy.

---

### User Story 3 - Osakkeen oma näkymä (Priority: P2)

Käyttäjä valitsee osakkeen ja näkee kaikki sen suositukset lähteittäin (alkuperäinen ja yhtenäistetty
suositus, tavoitehinta, päivämäärä, linkki alkuperään, hakuaika) sekä suositushistorian (nostot ja
laskut).

**Independent Test**: Valitse demodatasta osake; näkyy lähteittäinen taulukko ja historia, jossa
muutokset on merkitty nostoiksi/laskuiksi.

**Acceptance Scenarios**:

1. **Given** osakkeella on suosituksia kahdesta lähteestä, **When** käyttäjä avaa osakkeen, **Then**
   molemmat näkyvät linkkeineen.
2. **Given** lähteen suositus on muuttunut aiemmasta, **When** historia näytetään, **Then** muutos
   näkyy nostona tai laskuna päivämäärineen.

---

### User Story 4 - Viimeaikaiset suositusmuutokset (Priority: P3)

Käyttäjä näkee listan viimeaikaisista suositus- ja tavoitehintamuutoksista kaikista osakkeista,
uusimmat ensin, valittavalla aikaikkunalla.

**Independent Test**: Demodatassa on muutoksia; muutosnäkymä listaa ne uusin ensin.

**Acceptance Scenarios**:

1. **Given** suositus on noussut "Pidä" → "Lisää", **When** käyttäjä avaa muutosnäkymän, **Then**
   rivi näkyy nostona, lähde ja linkki mukana.

### Edge Cases

- Lähde palauttaa virheen, aikakatkaisun tai pääsy evätään (esim. maksullinen rajapinta) → lähteen
  tila "virhe", syy näytetään, muut lähteet jatkavat.
- API-avain puuttuu → demotila: esimerkkidata selvästi merkittynä.
- Osakkeella ei ole kurssia tai tavoitehintaa → nousuvara tyhjä.
- Lähteen suositusta ei voida tulkita → rivi ohitetaan ja kirjataan lokiin.
- Sama data haetaan uudelleen ilman muutoksia → historiaan ei synny uutta muutosta.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Järjestelmän MUST näyttää osakelista sarakkeilla konsensussuositus, suositusten määrä,
  keskimääräinen tavoitehinta, nykyinen kurssi ja nousuvara %.
- **FR-002**: Käyttäjän MUST voida järjestää lista konsensuksen, nousuvaran tai tuoreuden mukaan.
- **FR-003**: Käyttäjän MUST voida suodattaa listaa lähteen, (yhtenäistetyn) suosituksen ja toimialan
  mukaan.
- **FR-004**: Järjestelmän MUST näyttää osakkeen näkymässä kaikki suositukset lähteittäin, linkit
  alkuperäisiin ja suositushistorian nostoineen ja laskuineen.
- **FR-005**: Järjestelmän MUST näyttää viimeaikaisten suositusmuutosten näkymä.
- **FR-006**: Käyttäjän MUST voida käynnistää päivitys napista, ja viimeisin hakuajankohta MUST näkyä.
- **FR-007**: Järjestelmän MUST yhtenäistää lähteiden suositusasteikot asteikolle 1–5.
- **FR-008**: Jokaisella suosituksella MUST näkyä lähde, linkki alkuperään ja hakuajankohta.
- **FR-009**: Järjestelmän MUST toimia demotilassa esimerkkidatalla, kun API-avainta ei ole, ja
  käyttää oikeaa dataa heti kun avain on lisätty.
- **FR-010**: Uuden datalähteen lisääminen MUST onnistua lisäämällä yksi moduuli ilman muita muutoksia.
- **FR-011**: Käyttöliittymässä MUST näkyä maininta, ettei sovellus anna sijoitusneuvontaa.
- **FR-012**: Yksittäisen lähteen virhe MUST NOT estää muiden lähteiden päivitystä.

### Key Entities

- **Stock**: seurattava osake – tunnus, nimi, toimiala, pörssi, lähdekohtaiset tunnisteet.
- **Recommendation snapshot**: yhden lähteen suositus yhdelle osakkeelle tiettynä hakuhetkenä –
  alkuperäinen suositus, yhtenäistetty arvo 1–5, analyytikoiden määrä, tavoitehinta ja valuutta,
  suosituksen päivämäärä, linkki, hakuajankohta.
- **Quote**: osakkeen kurssi, valuutta, lähde ja hakuajankohta.
- **Fetch run**: päivityskerta lähteittäin – aloitus, tila, virheviesti, rivimäärä.
- **Recommendation change**: johdettu kahdesta peräkkäisestä erilaisesta snapshotista – nosto/lasku,
  tavoitehinnan muutos.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Käyttäjä näkee paremmuusjärjestetyn listan alle 5 sekunnissa sovelluksen avaamisesta
  (tallennetusta datasta).
- **SC-002**: Jokaisella näytetyllä suosituksella on lähde, linkki ja hakuaika (100 %).
- **SC-003**: Uuden lähteen lisääminen vaatii muutoksen vain yhteen uuteen tiedostoon.
- **SC-004**: Laskentalogiikan testit menevät läpi ilman verkkoyhteyttä.
- **SC-005**: Sovellus käynnistyy Windowsissa ohjeiden mukaan ilman maksullisia palveluita.

## Assumptions

- Yksi käyttäjä, oma kone; ei kirjautumista eikä palvelinta.
- Finnhubin ilmainen taso voi rajoittaa Helsingin osakkeiden dataa; rajoitukset näkyvät lähteen
  tilana eivätkä kaada sovellusta.
- Suositushistoria kertyy sovelluksen omista hakukerroista (lähteet eivät välttämättä tarjoa historiaa).
- Päivitys on käyttäjän käynnistämä; ajastettua hakua ei toteuteta.
