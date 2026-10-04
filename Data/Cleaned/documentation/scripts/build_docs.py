import sys, json, os
sys.path.insert(0, '/home/claude/work/scripts')
import pandas as pd
from load import rd, R

B = '/home/claude/work/cleaned_data/Olympic_Insights_Cleaned_Data/'
S = json.load(open('/home/claude/work/stats.json'))
V = pd.read_csv(B + 'documentation/VALIDATION_SUMMARY.csv').set_index('dataset')
LOG = pd.read_csv(B + 'documentation/CLEANING_LOG.csv', dtype=str, keep_default_na=False)

# ------------------------------------------------------------------ inventory
inv = [
 ('Olympics 2024.csv', '', 'Olympics 2024.csv', 'utf-8-sig', 'Medal table split by sport and country (Paris 2024, inferred - India 1S+5B matches)', 'sport x country medal tally', '2024 (Summer)', '93 countries/teams', 'Sums by country reconcile exactly to olympics2024.csv (except Individual Neutral Athletes)', 'EDITION-SPECIFIC', 'Keep: only source with medals by sport for Paris 2024', 'edition_specific/paris_2024_medals_by_sport_cleaned.csv'),
 ('Summer-Olympic-medals-1976-to-2008.csv', '', 'Summer-Olympic-medals-1976-to-2008.csv', 'cp1252', 'Medal winners, Summer Games 1976-2008', 'medal-level: one row = one medal-winning athlete in one event', '1976-2008 (9 Summer Games)', '128 countries (NOC codes)', 'Subset of athlete_events for those Games (medal rows only); adds Discipline and event gender', 'SUPPORTING', 'Keep as cross-check / discipline lookup; do not merge with athlete tables without keys', 'supporting/summer_olympic_medals_1976_2008_cleaned.csv'),
 ('Tokyo Medals 2021.csv', '', 'Tokyo Medals 2021.csv', 'utf-8-sig', 'Medal table, Tokyo 2020 (held 2021)', 'country: one row = one country at one edition', 'Tokyo 2020', '93 countries', 'Country totals; India 1G 2S 4B = 7', 'EDITION-SPECIFIC', 'Keep', 'edition_specific/tokyo_2020_medals_by_country_cleaned.csv'),
 ('archive/Athletes_summer_games.csv', 'archive', 'archive/Athletes_summer_games.csv', 'utf-8-sig', 'Athlete-event records, Summer Games', 'athlete-event: one row = athlete x event x Games', '1896-2020', 'all NOCs', 'Equals athlete_events Summer rows (222,552) + Tokyo 2020 (15,121); has saved pandas index; Age as float; no Height/Weight', 'REDUNDANT', 'Do not use; superseded by archive2/all_athlete_games (same rows + Winter + 2024/2026)', 'not cleaned (redundant)'),
 ('archive/Athletes_winter_games.csv', 'archive', 'archive/Athletes_winter_games.csv', 'utf-8-sig', 'Athlete-event records, Winter Games', 'athlete-event', '1924-2014', 'all NOCs', 'Equals athlete_events Winter rows (48,564) exactly (same attributes); has saved pandas index', 'REDUNDANT', 'Do not use', 'not cleaned (redundant)'),
 ('archive/regions.csv', 'archive', 'archive/regions.csv', 'utf-8-sig', 'NOC -> region lookup with notes', 'lookup: one row = one NOC', 'n/a', '234 NOCs', 'Superset of archive2/all_regions.csv (adds notes); has saved pandas index', 'SUPPORTING', 'Keep as NOC lookup; modern region names only', 'supporting/regions_cleaned.csv'),
 ('archive2/README.md', 'archive2', 'archive2/README.md', 'text', 'Dataset description of "The Olympics Legacy 1896-2026"', 'documentation', '1896-2026', 'n/a', 'Describes archive2 files; kept untouched', 'DOCUMENTATION', 'Reference only', 'not cleaned (documentation)'),
 ('archive2/all_athlete_games.csv', 'archive2', 'archive2/all_athlete_games.csv', 'utf-8-sig', 'Athlete-event records, Summer and Winter, with Entry ID', 'athlete-event: one row = athlete x event x Games (no athlete id)', '1896-2026 (38 Games; no Winter 2018/2022)', '234 NOCs', 'Rows <=2016 identical to athlete_events (minus Height/Weight); adds Tokyo 2020 results, Paris 2024 and Milano-Cortina 2026 rosters (no sport/event/medal)', 'PRIMARY', 'Use for 1896-2020 time series and India 2020; do not use 2024/2026 rows for medals', 'primary/all_athlete_games_cleaned.csv'),
 ('archive2/all_regions.csv', 'archive2', 'archive2/all_regions.csv', 'utf-8-sig', 'NOC -> region lookup', 'lookup', 'n/a', '234 NOCs', 'Identical NOC/region to archive/regions.csv', 'REDUNDANT', 'Do not use', 'not cleaned (redundant)'),
 ('athlete_events.csv', '', 'athlete_events.csv', 'utf-8-sig', '120 years of Olympic history (Kaggle-style) with athlete id, height, weight', 'athlete-event: one row = athlete x event x Games', '1896-2016 (35 Games)', '230 NOCs', 'Only file with athlete_id, Height and Weight; subset of all_athlete_games for <=2016', 'PRIMARY', 'Use for demographics/physical attributes and athlete-distinct counts', 'primary/athlete_events_cleaned.csv'),
 ('athletes new.csv', '', 'athletes new.csv', 'utf-8-sig', 'Athlete roster (Paris 2024 inferred: 206 NOCs, 112 IND)', 'athlete: one row = one registered athlete (not an event)', '2024 (Summer)', '206 NOCs', 'Overlaps all_athlete_games 2024 rows (different name format); includes alternates; no medals', 'EDITION-SPECIFIC', 'Keep for Paris 2024 India roster/demographics', 'edition_specific/paris_2024_athletes_cleaned.csv'),
 ('olympics.csv', '', 'olympics.csv', 'utf-8-sig', 'Paris 2024 country medals + region, GDP, population', 'country: one row = one country', '2024 (Summer)', '90 countries', 'Near-duplicate of olympics2024.csv medals (89 identical countries); missing Refugee Olympic Team; unique enrichment = region/gdp/population', 'OPTIONAL (SUPPORTING enrichment)', 'Use only for gdp/population enrichment; use olympics2024.csv for medals', 'supporting/olympics_2024_country_gdp_population_cleaned.csv'),
 ('olympics2024.csv', '', 'olympics2024.csv', 'utf-8-sig', 'Paris 2024 medal table by country', 'country: one row = one country', '2024 (Summer)', '91 countries/teams', 'Authoritative Paris country table in this collection (includes Refugee Olympic Team)', 'EDITION-SPECIFIC', 'Keep', 'edition_specific/paris_2024_medals_by_country_cleaned.csv'),
 ('olympics_medals_country_wise.csv', '', 'olympics_medals_country_wise.csv', 'utf-8-sig', 'All-time Summer and Winter medals and participations by country', 'country (all-time): one row = one country / historical NOC', 'all-time, through ~Tokyo 2020 / Beijing 2022 (inferred from India = 35 medals)', '156 NOCs/entities', 'Country totals; not derivable from athlete rows (team medals count once)', 'PRIMARY', 'Use for all-time country medal totals', 'primary/olympics_medals_country_wise_cleaned.csv'),
]
rows = []
for (fname, folder, path, enc, purpose, grain, years, geo, overlap, cls, rec, out) in inv:
    full = R + path
    ftype = os.path.splitext(path)[1].lstrip('.').upper()
    if path.endswith('.csv'):
        d = rd(path, 'cp1252' if enc == 'cp1252' else 'utf-8-sig')
        n, c, cols = len(d), d.shape[1], ' | '.join(d.columns)
    else:
        n, c, cols = '', '', ''
    rows.append(dict(file=fname, folder=folder or '(root)', file_type=ftype, size_bytes=os.path.getsize(full), data_rows=n, columns=c, column_names=cols, apparent_purpose=purpose,
                     grain=grain, year_coverage=years, geographic_coverage=geo, overlap_notes=overlap, classification=cls, recommendation=rec, cleaned_output=out))
pd.DataFrame(rows).to_csv(B + 'documentation/DATASET_INVENTORY.csv', index=False, encoding='utf-8', lineterminator='\n')

# ------------------------------------------------------------------ report
def v(ds, col):
    return int(V.loc[ds, col])

removed_total = int(V.rows_removed.sum())
_a = S.get('paris_ain_medals_sport_table', {})
ain_txt = f"{_a.get('gold')}G/{_a.get('silver')}S/{_a.get('bronze')}B"
_pc = pd.read_csv(B + 'edition_specific/paris_2024_medals_by_country_cleaned.csv', dtype=str, keep_default_na=False)
_oc = pd.read_csv(B + 'supporting/olympics_2024_country_gdp_population_cleaned.csv', dtype=str, keep_default_na=False)
chg_pc = int((_pc.noc != _pc.country_code_original).sum()); chg_oc = int((_oc.noc != _oc.country_code_original).sum())
m_pc = _pc.noc_standardization.value_counts().to_dict(); m_oc = _oc.noc_standardization.value_counts().to_dict()
rep = f"""# DATA CLEANING REPORT - Olympic Insights: A Global and Indian Data Analysis

Stage: **Data Cleaning** (not yet processing/transformation). Raw files were never modified; every output is a new file.
Method: inspect -> clean -> validate -> document. Priority: data integrity over a "perfect-looking" dataset.

---

## 1. Executive summary

* **13 raw data files** (+1 README, + macOS metadata files ignored) were inspected. **10 cleaned CSVs** were produced; **4 files** were classified redundant/documentation and deliberately **not** cleaned (they are verified copies/subsets of cleaned files).
* **{removed_total} rows were removed in total** (all documented): 117 completely empty rows (1976-2008 medals file) and 11 duplicated medal records in each of the two athlete-level files (the same 11 records: 1900 Paris sailing crews).
* **Nothing was imputed, guessed or added from outside the provided data.** Missing heights/weights/ages/medals stay blank. The only "added" fields are IOC codes in two 2024 country tables, derived exclusively from the provided Paris roster files (see section 9).
* Two seemingly obvious clean-ups were **deliberately not done** because they would have deleted real India records: removing "duplicate" *Balbir Singh* (India hockey, 1968 - three different players) and *SINGH, Singh* (India hockey, 1980 - two different players).
* Biggest unresolved issues: accents missing from athlete names in the source; Winter 2018/2022 missing from athlete files; 2024/2026 rows in `all_athlete_games` have no sport/event/medal; sport/country label drift between files; the 7 India "Gold" rows for 1924 Winter Alpinism that are not in the country medal table.
* All {sum(1 for _ in open(B + 'documentation/VALIDATION_CHECKS.csv')) - 1} automated validation checks pass (section 17).

## 2. Files inspected

| # | Raw file | Rows | Cols | Classification | Cleaned output |
|---|---|---|---|---|---|
""" + "\n".join(f"| {i+1} | `{r['file']}` | {r['data_rows']} | {r['columns']} | {r['classification']} | `{r['cleaned_output']}` |" for i, r in enumerate(rows)) + f"""

macOS artefacts (`.DS_Store`, `__MACOSX/`) were ignored.

## 3. Dataset inventory

Full machine-readable inventory (column names, grain, coverage, overlaps): `DATASET_INVENTORY.csv`.

Key overlap findings (all verified by comparing the data, not just names):

* `archive2/all_athlete_games.csv` rows for years <= 2016 are **identical** (11 attributes, as multisets) to `athlete_events.csv` (271,116 rows). `archive2` adds Tokyo 2020 results (15,121 rows), Paris 2024 roster rows (11,113) and 2026 Winter roster rows (2,916), but has no Height/Weight and no athlete id.
* `archive/Athletes_summer_games.csv` = `athlete_events` Summer rows (222,552) + Tokyo 2020 (15,121) = 237,673. `archive/Athletes_winter_games.csv` = `athlete_events` Winter rows (48,564). Both are therefore redundant.
* `archive/regions.csv` and `archive2/all_regions.csv` are identical on NOC and region (234 rows); the former adds `notes`.
* `olympics.csv` and `olympics2024.csv` give identical medal counts for the 89 countries they share; `olympics.csv` lacks the Refugee Olympic Team (1 Bronze) and uses "Taiwan" instead of "Chinese Taipei".
* `Olympics 2024.csv` (by sport) sums exactly to `olympics2024.csv` per country, except that it additionally lists *Individual Neutral Athletes* ({ain_txt}) and spells "Saint Lucia" for "St Lucia".

**Grain of each cleaned table** (never mixed in this package):

| Cleaned file | One row = |
|---|---|
| athlete_events_cleaned | athlete x event x Games (has athlete_id) |
| all_athlete_games_cleaned | athlete x event x Games (no athlete id); for 2024/2026 one row = roster entry |
| summer_olympic_medals_1976_2008_cleaned | one medal-winning athlete x event (medal level) |
| olympics_medals_country_wise_cleaned | country / historical NOC, all-time |
| regions_cleaned | NOC |
| paris_2024_medals_by_country_cleaned | country at Paris 2024 |
| paris_2024_medals_by_sport_cleaned | country x sport at Paris 2024 |
| tokyo_2020_medals_by_country_cleaned | country at Tokyo 2020 |
| paris_2024_athletes_cleaned | registered athlete at Paris 2024 (alternates included) |
| olympics_2024_country_gdp_population_cleaned | country at Paris 2024 + external-style indicators |

## 4. Dataset selection recommendations

* **PRIMARY:** `athlete_events` (athlete id, height, weight, 1896-2016), `all_athlete_games` (1896-2020 incl. Tokyo; roster-only 2024/2026), `olympics_medals_country_wise` (all-time country totals).
* **SUPPORTING:** `regions` (NOC lookup), `Summer-Olympic-medals-1976-to-2008` (medal-level cross-check, adds discipline), `olympics.csv` (GDP/population/region enrichment only - optional).
* **EDITION-SPECIFIC:** Paris 2024 (country table, sport table, athlete roster), Tokyo 2020 (country table).
* **REDUNDANT (not cleaned, raw kept):** `archive/Athletes_summer_games.csv`, `archive/Athletes_winter_games.csv`, `archive2/all_regions.csv`.
* **DOCUMENTATION:** `archive2/README.md`.
* **PROBLEMATIC:** none were excluded, but the 2024/2026 rows of `all_athlete_games` have serious limitations (section 16).

## 5. Cleaning operations performed

Every operation is itemised with counts in `CLEANING_LOG.csv` ({len(LOG)} entries). Summary:

| Operation | Where | Rows/cells |
|---|---|---|
| Removed completely empty rows | 1976-2008 medals | 117 rows |
| Removed duplicate medal records (same athlete, event, medal) | athlete_events, all_athlete_games | 11 + 11 rows |
| Converted text `NA` to true blank | athlete_events (age 9,474; height 60,171; weight 62,875; medal 231,333); regions notes (4) | see log |
| Trimmed / collapsed whitespace, converted non-breaking spaces | athlete files (names 310-312 cells, 42 event cells), medals files, Paris tables, country-wise | see log |
| Converted numbers stored as text (`1,060`) to integers | country-wise (6 cells) | 6 |
| Set impossible zeros (height 0, weight 0) to blank | Paris roster | {S['an_zero_height']} heights, {S['an_zero_weight']} weights |
| Fixed file encoding (Windows-1252 -> UTF-8) | 1976-2008 medals | whole file |
| Dropped accidental index column | regions | 234 rows |
| Standardised column names to snake_case, with units on height/weight | all | all |
| Standardised athlete sex to `M`/`F` | all_athlete_games, 1976-2008 medals, Paris roster (athlete_events already M/F) | all rows |
| Removed parentheses from IOC codes (`(AFG)`->`AFG`) | country-wise | 156 |
| Stripped marker characters from country names, original kept | 1976-2008 (`*`), Paris by sport (`*`, `[A]`) | 11 / 22 |
| Added IOC code column using only the Paris roster files | olympics2024.csv, olympics.csv | {chg_pc} / {chg_oc} changed |

## 6. Duplicate handling

Rule applied: **a row is only removed if the same person cannot legitimately have it twice.**

| Case | Finding | Decision |
|---|---|---|
| `athlete_events` exact duplicates (all 15 columns incl. athlete_id) | 1,385 extra rows (612 groups), all Summer 1900-1948 | Investigated by sport/medal |
| ...of which carry a **medal** | 11 rows, all 1900 sailing crews (boats Olle, Favorite-1, Quand-Mme-2): same athlete, same event, same medal twice | **Removed** (3 Gold + 8 Silver rows). Saved in `REMOVED_ROWS_*.csv`. India unaffected. |
| ...of which have **no medal** | 1,374 rows: Art Competitions {S['ae_dup_nomedal_sport'].get('Art Competitions')}, Cycling {S['ae_dup_nomedal_sport'].get('Cycling')}, Sailing {S['ae_dup_nomedal_sport'].get('Sailing')}, Equestrianism {S['ae_dup_nomedal_sport'].get('Equestrianism')} | **Retained.** Art competitors entered several works in one category (e.g. Louis-Martin Rey appears 3x per category); the rest cannot be proven erroneous and cannot distort medal totals. Use `COUNT DISTINCT athlete_id` for headcounts. |
| `all_athlete_games` (no athlete id) | name-only matching would flag 1,386 rows | Removed only the **same 11 confirmed** medal records; 1,375 remain (1 more than athlete_events because the two identical 23-year-old *Balbir Singh* India 1968 rows are only distinguishable by athlete_id) |
| 1976-2008 medals: 117 "duplicates" | all are the empty rows | Removed as empty rows |
| 1976-2008 medals: *SINGH, Singh* India 1980 hockey | 1 exact duplicate | **Retained** - two different players with the same truncated name; India's gold squad needs 16 rows and has 16 |
| Paris roster: 20 rows share a name | different athlete_code, birth date, discipline | Retained (different people) |

**Impact on medal statistics (flagged):** 3 Gold and 8 Silver athlete-level rows fewer (France/GBR crews, 1900). No other medal counts changed.

## 7. Missing-value handling

* `NA` text -> blank cell (one representation). **No imputation of any kind.**
* A blank `medal` means *competed, did not medal* in `athlete_events` and in `all_athlete_games` up to 2020. In `all_athlete_games` for **2024 and 2026 a blank medal means "results not in source"** (those rows also have blank sport and event).
* Rows with missing age/height/weight/team were **kept** (Age: 9,474 missing in athlete_events; Height 60,171; Weight 62,875).
* Paris roster: height 0 (6,032) and weight 0 (10,783) are placeholders, not measurements -> set blank; 16 weights were already blank.
* `regions`: 3 NOCs without a region (ROT, TUV, UNK) stay blank even though `notes` holds text for two of them (no guessing).

## 8. Standardisation performed

See section 5. Intentionally **not** standardised: sport names across files (`Canoeing`/`Canoe Sprint`, `Equestrian`/`Equestrianism`, `Field hockey`/`Hockey`), city labels (`Athina` vs `Athens`), event wording, name capitalisation (`Tulika MAAN`, `SINGH, Singh`), historical country names, event-gender codes.

## 9. Country / NOC handling

* Original `noc`/`team`/`country` values are preserved everywhere. Historical entities (URS, EUN, GDR, FRG, TCH, YUG, SCG, SRB, RU1, ZZX, ROC, OAR, IOP) remain separate rows/values.
* `regions` is a *modern* grouping (YUG->Serbia, URS->Russia, GDR/FRG->Germany) and was **not** used to overwrite anything.
* **IOC code derivation (the only enrichment):** `olympics2024.csv` mixes code styles (US, NZ, HK, SA, SIN, SPA, SWI, GBG, BRZ, PKN, SER, ROM, MOR, IRE...) and `olympics.csv` uses ISO-style codes (DEU, NLD, DNK, ZAF...). For each row: (1) if the code is already an IOC code present in the Paris roster files -> keep (`original_code_valid`); (2) else look up the country name in the Paris roster files (`athletes new.csv`, `all_athlete_games` 2024) -> `matched_by_country_name`; (3) else a 3-entry alias list (Iran->IR Iran, Hong Kong->Hong Kong, China, Taiwan->Chinese Taipei) -> `matched_by_documented_alias`; (4) else blank + `unresolved`. Original code kept in `country_code_original`; method in `noc_standardization`. Results (method: rows): Paris country table - {', '.join(f'{k}: {v}' for k, v in m_pc.items())}; `olympics.csv` - {', '.join(f'{k}: {v}' for k, v in m_oc.items())}.
* Source: provided files only. No external data was introduced.
* Left unresolved: `TRI` (1976-2008 file, Trinidad and Tobago; regions has `TTO`), `AIN` (in `all_athlete_games`, not in regions), Tokyo 2020 table has names only (no codes), `SCG` and `SRB` both carry country "Serbia" in the 1976-2008 file.

## 10. Olympic-specific considerations

* Summer and Winter are kept distinct (`season`); `games` = `year season`. 1956 Summer legitimately has two host cities (Melbourne; Stockholm for equestrian) - preserved.
* **Host city vs host country:** 2026 Winter rows in `all_athlete_games` have city = `Italy` (a country; co-hosted Milano-Cortina). Left as is and flagged.
* **Athlete-level medal rows are not medals.** Examples from this very data (India): 1980 hockey = 16 Gold rows but 1 Gold medal; Tokyo 2020 = 24 medal rows (21 Bronze, 2 Silver, 1 Gold) for 7 medals. Counting distinct (year, season, sport, event, noc, medal) from `all_athlete_games` reproduces India's Summer 10G/9S/16B exactly, but the same recipe does *not* reproduce all other countries (country table includes later Winter Games and excludes some non-standard events), so country totals should come from the country-level tables.
* **Non-standard medals:** {S['ae_art_medal_rows']} medal rows in Art Competitions (1912-1948) and {S['ae_alpinism_medal_rows']} in Alpinism (1924). Genuine source records, kept, flagged.
* **Coverage gaps:** no Winter 2018 / 2022 in any athlete file; `olympics_medals_country_wise` ends around Tokyo 2020 / Beijing 2022 (does not include Paris 2024).
* Tokyo Games are labelled 2020 in athlete files and 2021 in the filename of the country table; the cleaned file is called `tokyo_2020_*`.

## 11. India-specific validation

| Check | Result |
|---|---|
| `athlete_events` India rows before / after | 1,408 / 1,408 (none removed) |
| India medal rows (athlete level) before / after | 197 / 197 |
| 3 x *Balbir Singh* 1968 (ids 111012, 111013, 111014) | all retained |
| `all_athlete_games` India rows | 1,673 before / 1,673 after |
| India medal rows in both athlete files for Games <= 2016 | identical |
| 1976-2008 medals file vs athlete_events (India by year and medal) | identical (1980: 16 Gold; 1996 Bronze; 2000 Bronze; 2004 Silver; 2008: 1 Gold, 2 Bronze) |
| India 1980 hockey Gold rows in 1976-2008 file | 16 (incl. both *SINGH, Singh*) |
| Country-wise table, India | 10 Gold / 9 Silver / 16 Bronze = 35 Summer; 0 Winter; 25 + 11 participations |
| Athlete level (distinct event/medal) India Summer through 2020 | 10 / 9 / 16 - matches the country-wise table |
| Tokyo 2020 country table, India | 1 / 2 / 4 = 7 |
| Paris 2024 country table, India | 0 / 1 / 5 = 6 (sport table: Athletics S1, Field hockey B1, Shooting B3, Wrestling B1 - sums to the same) |
| Paris roster India | 112 athletes = India rows for 2024 in `all_athlete_games` |
| Flag | 7 India Gold rows, Winter 1924 Chamonix, Alpinism (athlete files) but 0 India winter medals in the country-wise table |
| Note | country-wise India (35) stops at Tokyo 2020; adding Paris 2024 (6) would give 41 - verify before combining |

## 12. Rows removed

| File | Rows removed | Why |
|---|---|---|
| summer_olympic_medals_1976_2008 | 117 | completely empty rows |
| athlete_events | 11 | duplicate medal records (1900 sailing) |
| all_athlete_games | 11 | the same 11 records |
| all others | 0 | |
| **Total** | **{removed_total}** | |

Removed rows are listed in `REMOVED_ROWS_athlete_events_duplicate_medal_records.csv` and `REMOVED_ROWS_all_athlete_games_duplicate_medal_records.csv`.

## 13. Rows retained despite missing values

* All athlete-event rows with missing age/height/weight/medal/team.
* 14,029 `all_athlete_games` rows with blank sport/event/medal (2024 Summer {S['a2_blank_sport_by_year'].get('2024')}, 2026 Winter {S['a2_blank_sport_by_year'].get('2026')}).
* 2,916 rows with blank team (2026).
* Paris roster rows with unknown height/weight; 1 sport-table row with no rank (Individual Neutral Athletes, gymnastics: rank `-`).
* 3 `regions` rows without a region.

## 14. Columns modified

* Whitespace-normalised: name, team, event, city, sport (athlete files); all text columns in small files.
* NA->blank: age, height_cm, weight_kg, medal; regions.notes.
* Numeric text fixed: country-wise (commas); Paris roster height/weight (0 -> blank).
* Value recoded: sex (Male/Female, Men/Women -> M/F); noc (parentheses removed in country-wise); country (marker characters stripped, original kept in `country_original`); rank_in_sport (`-` -> blank).
* Added columns: `country_original` (1976-2008, Paris by sport); `noc`, `country_code_original`, `noc_standardization` (olympics.csv, olympics2024.csv).
* Dropped: `Unnamed: 0` (regions only).

## 15. Columns renamed

* athlete_events: ID->athlete_id, Sex->sex, Height->height_cm, Weight->weight_kg, all others to lower-case.
* all_athlete_games: Entry ID->entry_id, Gender->sex, Sport Disciplines->sport_disciplines, Event List->event_list, others lower-case.
* 1976-2008: Gender->sex, Country_Code->noc, Event_gender->event_gender, others lower-case.
* country-wise: countries->country, ioc_code->noc, total_participation->total_participations (trailing spaces removed from headers).
* Paris by sport: Competitions->sport, Rank->rank_in_sport, NOC->country (it held country names). Paris by country: Country Code->country_code_original. Tokyo: Gold Medal->gold, Silver Medal->silver, Bronze Medal->bronze, Rank By Total->rank_by_total. Paris roster: code->athlete_code, gender->sex, height->height_cm, weight->weight_kg. regions: NOC->noc.

## 16. Unresolved issues

1. **Accents are missing from names** in every athlete file (0 non-ASCII characters; e.g. `Andr Auffray`). Characters were dropped upstream and cannot be restored without external data.
2. `all_athlete_games` 2024/2026 rows: no sport/event/medal; 2026 has blank team and city `Italy`.
3. No Winter 2018 / 2022 athlete data.
4. Sport/discipline labels differ by era and file (list in log); mapping table needed in processing.
5. City/event label differences between files (e.g. `Athina` vs `Athens`).
6. Historical NOC mapping: `TRI`, `AIN`, `IOP` missing from regions; SCG/SRB both labelled Serbia; Tokyo table has no codes.
7. 1,374 duplicate-looking no-medal rows retained (section 6).
8. Source quirks kept as-is: *CHEPCHUMBA, Joyce* (2000 marathon, event W) has gender "Men"; truncated names such as `SINGH, Singh`; mixed upper/lower-case name formats.
9. `olympics.csv`: `gdp` looks like GDP per capita (USD) and `population` like millions, but units are undocumented; `gdp_year` mixes 2023 and 2022.
10. Paris totals in the provided tables (328 G / 327 S / 384 B in `olympics2024.csv`) are internally consistent and agree with the sport table, but were **not** verified against an external official table. Individual Neutral Athletes ({ain_txt}) appear only in the sport table.
11. Paris roster `disciplines`/`events` are list-like strings (mixed quotes) - unexploded.
12. Alpinism 1924 / Art Competitions medals (section 10).
13. Edition labels for `Olympics 2024.csv`, `olympics*.csv`, `athletes new.csv` are inferred (e.g. India medal and roster counts), not stated in the files.

## 17. Validation results

Automated checks (`VALIDATION_CHECKS.csv`), all passing, include:

* Every output CSV re-opened: parses with the strict CSV reader, UTF-8, no BOM, no ragged rows, no `Unnamed` / index columns, no blank rows or columns, no `NA`/`NaN` text, no stray whitespace, numeric columns parse.
* Row counts equal expected (raw minus documented removals).
* `athlete_events_cleaned` and `all_athlete_games_cleaned` (<= 2016) are identical as multisets on 11 attributes - no row multiplication or loss between files.
* Raw medal totals minus cleaned medal totals = exactly the 3 Gold + 8 Silver removed rows.
* Athlete id distinct count unchanged (135,571). Year ranges, season, sex and medal categories as expected.
* Country tables: gold+silver+bronze=total in every row; Paris sport table = Paris country table; `olympics.csv` = `olympics2024.csv` for the 89 common countries.
* India checks (section 11).
* **Raw files byte-identical** to the start of the session (SHA-256 of 15 files) and the uploaded ZIP is unchanged.

Before / after per dataset (`VALIDATION_SUMMARY.csv`, `VALIDATION_PROFILE.csv`):

| Dataset | Rows before | Rows after | Cols before | Cols after | Exact dup rows before | after | Missing cells before | after |
|---|---|---|---|---|---|---|---|---|
""" + "\n".join(f"| {k} | {r.rows_before} | {r.rows_after} | {r.cols_before} | {r.cols_after} | {r.exact_dup_rows_before} | {r.exact_dup_rows_after} | {r.missing_cells_before} | {r.missing_cells_after} |" for k, r in V.iterrows()) + """

Notes: "exact dup rows" for the two files with an index/Entry ID column are counted ignoring that column. "Missing cells before" counts blank, `NA`, `NaN` tokens; after = blank cells. Increases/decreases come from the documented actions only (e.g. Paris roster zeros -> blank adds missing cells; 117 empty rows removed).

Ranges after cleaning: age 10-97; height 127-226 cm (athlete_events), 140-222 (Paris roster); weight 25-214 kg, 51-113 (Paris roster); years 1896-2016 (athlete_events), 1896-2026 (all_athlete_games), 1976-2008 (medals file); sex M/F; season Summer/Winter; medal Gold/Silver/Bronze/blank; NOC counts 230 / 234 / 128 / 156 / 91.

## 18. Recommended next steps for data processing

1. Build a **sport/discipline mapping table** and a **country/NOC dimension** (keep historical entities; add `modern_country` as a *separate* column).
2. Define a **medal fact table** at grain *Games x sport x event x NOC x medal* (distinct), validated against the country-level tables; decide treatment of Art Competitions / Alpinism and of unofficial medals.
3. Use `athlete_events` for athlete-distinct counts and physical attributes; use `all_athlete_games` for the long time series and 2020; use roster rows (2024/2026) only for participation, never for medals.
4. Treat the three country-level tables as the authority for country totals; reconcile Paris 2024 totals externally if the dashboard will show them.
5. Explode list-like columns (Paris roster `events`, `disciplines`) into a separate table.
6. Decide on the Winter 2018/2022 gap (external data would need explicit documentation).
7. Create derived fields (age bands, medal flags, decades) only now, in the processing stage.
"""
open(B + 'documentation/DATA_CLEANING_REPORT.md', 'w', encoding='utf-8').write(rep)

# ------------------------------------------------------------------ README
readme = f"""# Olympic Insights - Cleaned Data Package

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
                    CLEANING_LOG.csv          {len(LOG)} auditable entries
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
"""
open(B + 'README.md', 'w', encoding='utf-8').write(readme)
print('docs written', len(rep), len(readme))
