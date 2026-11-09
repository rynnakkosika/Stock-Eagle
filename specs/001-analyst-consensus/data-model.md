# Data Model

## stocks
| kenttä | tyyppi | huom |
|---|---|---|
| ticker (PK) | TEXT | sovelluksen sisäinen tunnus, esim. `NOKIA` |
| name | TEXT | |
| sector | TEXT | voi tulla lähteestä tai seurantalistasta |
| exchange | TEXT | esim. `XHEL` |
| currency | TEXT | oletus `EUR` |

## recommendations (snapshot)
| kenttä | tyyppi | huom |
|---|---|---|
| id (PK) | INTEGER | |
| fingerprint (UNIQUE) | TEXT | source/ticker/analyst/rec_date/rating_raw/target |
| source_id | TEXT | adapterin `id` |
| ticker | TEXT | |
| analyst | TEXT | `""` koostetuille lähteille |
| rating_raw | TEXT | lähteen oma suositus |
| rating | REAL | 1–5 |
| analyst_count | INTEGER | ≥1 |
| target_price | REAL NULL | |
| currency | TEXT NULL | |
| rec_date | TEXT | ISO-päivä |
| url | TEXT | linkki alkuperään |
| fetched_at | TEXT | ensimmäinen hakuhetki (UTC ISO) |
| last_seen_at | TEXT | viimeisin hakuhetki, jolloin sama tieto nähtiin |

## quotes
PK (ticker, source_id): price, currency, as_of, fetched_at, url.

## fetch_runs
id, source_id, started_at, finished_at, status (`ok`/`error`/`partial`/`skipped`), message, n_records.

## Johdetut
- **ConsensusRow**: ticker, name, sector, consensus (1–5), label, n_recommendations, avg_target,
  price, currency, upside, latest_date, sources.
- **Change**: ticker, source_id, analyst, date, old/new rating & label, direction (+1/0/−1),
  old/new target, url.

## Yhtenäistetty asteikko
| arvo | nimi |
|---|---|
| 5 | Osta |
| 4 | Lisää |
| 3 | Pidä |
| 2 | Vähennä |
| 1 | Myy |
