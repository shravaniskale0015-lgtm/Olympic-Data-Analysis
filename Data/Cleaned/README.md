# Olympic Insights - Cleaned Data Package

Cleaned (not yet processed) data for the course project **Olympic Insights: A Global and Indian Data Analysis**.
Produced from your RAW ZIP; raw files were not changed. All CSVs are UTF-8, comma-separated, one header row, no index column - ready for Google Sheets / Looker Studio imports (the two athlete files are large: ~270-300k rows, so load them through Looker Studio/BigQuery or a CSV connector rather than a Sheets tab).

## What is inside

```
primary/            athlete_events_cleaned.csv             athlete x event, 1896-2016, athlete_id, height, weight
                    all_athlete_games_cleaned.csv          athlete x event, 1896-2020 + 2024/2026 roster rows (no medals/events)
                    olympics_medals_country_wise_cleaned.csv   all-time medals by country (Summer/Winter)
supporting/         regions_cleaned.csv                    NOC -> modern region lookup
                    summer_olympic_medals_1976_2008_cleaned.csv   medal winners 1976-2008 (+ discipline)
                    olympics_2024_country_gdp_population_cleaned.csv   OPTIONAL: Paris 2024 country medals + gdp/population
edition_specific/   paris_2024_medals_by_country_cleaned.csv     (authoritative Paris country table here)
                    paris_2024_medals_by_sport_cleaned.csv
                    paris_2024_athletes_cleaned.csv
                    tokyo_2020_medals_by_country_cleaned.csv
documentation/      DATA_CLEANING_REPORT.md   full report (BEFORE -> ACTION -> AFTER -> REASON in sections 5-15)
                    CLEANING_LOG.csv          84 auditable entries
                    DATASET_INVENTORY.csv, VALIDATION_SUMMARY.csv, VALIDATION_PROFILE.csv, VALIDATION_CHECKS.csv
                    REMOVED_ROWS_*.csv        the 22 removed duplicate medal rows (11 per athlete file)
                    scripts/                  the Python used (clean.py, validate.py, build_docs.py, load.py; paths are those of the cloud workspace)
```

Not cleaned (redundant, still in your raw data): `archive/Athletes_summer_games.csv`, `archive/Athletes_winter_games.csv` (= athlete_events + Tokyo 2020), `archive2/all_regions.csv` (= regions).

## Cleaning that was performed

Empty rows removed (117); 11 duplicated 1900 sailing medal records removed per athlete file; text `NA` -> blank; whitespace/non-breaking spaces fixed; encoding of the 1976-2008 file fixed; numbers stored as text fixed; placeholder zeros in the Paris roster -> blank; consistent snake_case headers; sex coded `M`/`F` in all athlete tables; markers (`*`, `[A]`, parentheses) stripped from country/NOC text with the original kept; IOC code added to two Paris country tables using only the provided Paris roster files. Details: `CLEANING_LOG.csv`.

## Intentionally unchanged

Missing values (no imputation); blank `medal` (= no medal, except 2024/2026 rows in `all_athlete_games`); historical NOCs and country names; sport, city and event labels; name formats; duplicate-looking rows that cannot be proven wrong (1,374 no-medal rows - mostly 1920s-40s Art Competitions); the India rows *Balbir Singh* (1968) and *SINGH, Singh* (1980), which look like duplicates but are different players.

## Important limitations

1. **Athlete rows are not medals.** A team medal appears once per team member (India 1980 hockey: 16 rows = 1 Gold). Use the country-level tables for country totals.
2. `all_athlete_games` rows for **2024 and 2026 have no sport, event or medal** (blank medal there means *unknown*); 2026 city is `Italy`; do not use them for medal analysis.
3. No athlete data for Winter 2018 and 2022. `olympics_medals_country_wise` ends around Tokyo 2020 (India 35 medals) and excludes Paris 2024 (India 6).
4. Accented characters are missing from athlete names in the source (cannot be repaired).
5. Athlete files include Art Competitions (1912-1948) and 1924 Alpinism medals, including 7 India Gold rows (Winter 1924); the country-wise table shows India with 0 winter medals.
6. Sport/city/event naming differs between files and eras; `regions` is a modern grouping and must not overwrite historical NOCs.
7. Paris 2024 and Tokyo 2020 totals come from the provided files and were not checked against an external official table. Edition labels for the 2024 files are inferred (see report).
8. `gdp` / `population` units in `olympics_2024_country_gdp_population_cleaned.csv` are undocumented (look like per-capita USD and millions).

## How to use in the next stage (processing / transformation)

* Use `athlete_events` for distinct-athlete counts (`COUNT DISTINCT athlete_id`) and height/weight; `all_athlete_games` for 1896-2020 trends and India's Tokyo 2020 participation.
* Join on `noc` (kept in original historical form); build a country dimension rather than editing source values. Do not join athlete tables to each other by name (no common key; athlete_id exists only in `athlete_events`).
* Build medal counts from distinct (games, sport, event, noc, medal) and reconcile with the country-level tables (this reproduces India's Summer 10/9/16 exactly; other countries need extra rules).
* Create derived columns, aggregates and KPIs only at that stage - none were created here.
