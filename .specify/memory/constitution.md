<!--
Sync Impact Report
- Version change: (template) → 1.0.0
- Added principles: I–VII (all new)
- Added sections: Tekniset rajoitteet, Kehitystyönkulku, Governance
- Removed sections: none
- Deferred TODOs: none
-->
# Stock Eagle Constitution

## Core Principles

### I. Laillinen ja sallittu datanhankinta (NON-NEGOTIABLE)
- Dataa MUST hakea vain virallisista rajapinnoista tai julkisilta sivuilta, joiden käyttöehdot
  ja robots.txt sallivat automaattisen haun.
- Kirjautumisen takaista dataa (esim. OP, Nordea) MUST NOT käyttää.
- Käyttöehtoja, rajoituksia tai botintunnistusta MUST NOT kiertää.
- Jos lähteen sallittavuus on epäselvä, lähdettä ei toteuteta ja syy kirjataan DECISIONS.md:hen.

Rationale: sovellus on henkilökohtainen työkalu, eikä se saa luoda oikeudellista riskiä.

### II. Jäljitettävyys
- Jokaisella näytetyllä suosituksella ja tavoitehinnalla MUST olla näkyvissä lähde, linkki
  alkuperäiseen ja hakuajankohta.
- Tallennettu data säilyttää lähdetunnisteen ja hakuajankohdan.

### III. Ei sijoitusneuvontaa
- Sovellus vain esittää ja yhdistää kolmansien osapuolten tietoja. Käyttöliittymässä MUST näkyä
  vastuuvapauslauseke. Sovellus ei tuota omia osto-/myyntisuosituksia; paremmuusjärjestys on
  pelkkä lajittelu kolmansien osapuolten datasta.

### IV. Laajennettavat datalähteet
- Jokainen datalähde on oma adapter-moduulinsa, joka toteuttaa yhteisen rajapinnan.
- Uuden lähteen lisääminen MUST NOT vaatia muutoksia muuhun sovellukseen (rekisteröinti
  tapahtuu automaattisesti moduulin löytymisen perusteella).

### V. Paikallinen ja maksuton
- Sovellus MUST toimia omalla Windows-koneella ilman palvelinta tai maksullisia palveluita.
- Kaikki tila tallennetaan paikalliseen SQLite-tietokantaan.

### VI. Salaisuuksien suojaus
- API-avaimet MUST NOT päätyä koodiin, testeihin, lokeihin tai versionhallintaan.
  Avaimet luetaan ympäristömuuttujista / `.env`-tiedostosta, joka on `.gitignore`:ssa.

### VII. Testattu laskentalogiikka
- Normalisointi, konsensus, nousuvara ja muutosten tunnistus MUST olla yksikkötestattuja
  (pytest). Testit eivät saa tehdä verkkokutsuja.

## Tekniset rajoitteet

Python 3.11+, Streamlit, SQLite, pytest. Ei ulkoisia palvelimia. Verkkokutsut vain adaptereissa.

## Kehitystyönkulku

Spec Kit -työnkulku: constitution → specify → clarify → plan → tasks → implement.
Autonomiset päätökset kirjataan `DECISIONS.md`:hen. Testien tulee mennä läpi ennen valmista.

## Governance

Tämä perustuslaki ohittaa muut käytännöt. Muutokset tehdään päivittämällä tämä tiedosto,
nostamalla versiota (semver) ja kirjaamalla syy DECISIONS.md:hen. Jokainen suunnitelma
tarkistetaan periaatteita vasten (Constitution Check plan.md:ssä).

**Version**: 1.0.0 | **Ratified**: 2026-11-09 | **Last Amended**: 2026-11-09
