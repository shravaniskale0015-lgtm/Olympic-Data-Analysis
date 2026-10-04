import sys, json, re
sys.path.insert(0, '/home/claude/work/scripts')
import pandas as pd
from collections import Counter
from load import rd, R

OUT = '/home/claude/work/cleaned_data/Olympic_Insights_Cleaned_Data/'
LOG = []
STATS = {}
MISSING_TOKENS = {'', 'NA', 'NaN', 'nan', 'NULL', 'null', 'None', 'N/A'}


def log(dataset, column, issue_type, original, action, reason, rows, validation='', notes=''):
    LOG.append(dict(dataset=dataset, column=column, issue_type=issue_type, original_condition=original,
                    action_taken=action, reason=reason, rows_affected=rows, validation_result=validation, notes=notes))


def n_missing(df):
    return int(sum(df[c].isin(MISSING_TOKENS).sum() for c in df.columns))


def n_missing_by_col(df):
    return {c: int(df[c].isin(MISSING_TOKENS).sum()) for c in df.columns}


def norm_ws(s):
    return (s.str.replace(' ', ' ', regex=False).str.replace(r'\s+', ' ', regex=True).str.strip())


def clean_text_cols(df, cols, dataset):
    """trim, collapse internal whitespace, convert nbsp; log per column."""
    for c in cols:
        new = norm_ws(df[c])
        ch = int((new != df[c]).sum())
        if ch:
            lead = int((df[c] != df[c].str.strip()).sum())
            log(dataset, c, 'whitespace',
                f'{lead} cells with leading/trailing whitespace; {ch} cells with extra/hidden whitespace in total (double spaces, non-breaking spaces)',
                'Trimmed, collapsed repeated whitespace to a single space, converted non-breaking spaces to normal spaces',
                'Whitespace is a formatting artefact; it breaks grouping/joins and has no analytical meaning',
                ch, f'{int((new != new.str.strip()).sum())} cells with whitespace remain')
        df[c] = new
    return df


def blank_missing(df, cols, dataset, label='NA'):
    for c in cols:
        m = df[c].isin(['NA', 'NaN', 'nan', 'NULL', 'null', 'None', 'N/A'])
        k = int(m.sum())
        if k:
            df.loc[m, c] = ''
            log(dataset, c, 'missing_value_representation', f"{k} cells contain the text '{label}'",
                "Replaced with an empty cell (true missing)", 'One consistent missing-value representation; text "NA" breaks numeric typing in Sheets/Looker. Nothing imputed.',
                k, "0 'NA' text cells remain")
    return df


def num_check(s, name, dataset, integer=True):
    v = pd.to_numeric(s.replace('', pd.NA), errors='coerce')
    bad = int((v.isna() & (s != '')).sum())
    assert bad == 0, f'{dataset}.{name}: {bad} non-numeric'
    return v


def fmt_num(v):
    """Format numeric series to clean text (no .0 for whole numbers)."""
    def f(x):
        if pd.isna(x):
            return ''
        return str(int(x)) if float(x).is_integer() else repr(float(x))
    return v.map(f)


def write(df, rel):
    df.to_csv(OUT + rel, index=False, encoding='utf-8', lineterminator='\n')


def dup_count(df):
    return int(df.duplicated().sum())


# ---------------------------------------------------------------- reference data from provided files
an_raw = rd('athletes new.csv')
a2_raw = rd('archive2/all_athlete_games.csv')
ioc_codes = set(an_raw.country_code) | set(a2_raw[a2_raw.Year == '2024'].NOC)
name2codes = {}
for _, r in an_raw[['country', 'country_full', 'country_code']].drop_duplicates().iterrows():
    for nm in (r.country, r.country_full):
        name2codes.setdefault(nm, set()).add(r.country_code)
for _, r in a2_raw[a2_raw.Year == '2024'][['Team', 'NOC']].drop_duplicates().iterrows():
    name2codes.setdefault(r.Team, set()).add(r.NOC)


# explicit, documented aliases: country label used in the medal tables -> label used in the Paris roster files
ALIASES = {'Iran': 'IR Iran', 'Hong Kong': 'Hong Kong, China', 'Taiwan': 'Chinese Taipei'}


def std_ioc(code, country):
    """Return (std_code, method). Only uses codes/names that exist in the provided Paris roster files."""
    if code in ioc_codes:
        return code, 'original_code_valid'
    cands = name2codes.get(country, set())
    if len(cands) == 1:
        return next(iter(cands)), 'matched_by_country_name'
    cands = name2codes.get(ALIASES.get(country, ''), set())
    if len(cands) == 1:
        return next(iter(cands)), 'matched_by_documented_alias'
    return '', 'unresolved'


# ================================================================= 1. athlete_events (PRIMARY)
DS = 'athlete_events_cleaned.csv'
raw = rd('athlete_events.csv')
before = dict(rows=len(raw), cols=raw.shape[1], dups=dup_count(raw), missing=n_missing(raw))
df = raw.rename(columns={'ID': 'athlete_id', 'Name': 'name', 'Sex': 'sex', 'Age': 'age', 'Height': 'height_cm', 'Weight': 'weight_kg',
                         'Team': 'team', 'NOC': 'noc', 'Games': 'games', 'Year': 'year', 'Season': 'season', 'City': 'city',
                         'Sport': 'sport', 'Event': 'event', 'Medal': 'medal'})
log(DS, 'all', 'column_naming', 'Mixed-case column names (ID, Name, Sex, Height ...) with no units',
    'Renamed to snake_case; Height->height_cm, Weight->weight_kg, ID->athlete_id (units follow the Kaggle 120-years documentation: cm / kg)',
    'Consistent naming across all cleaned files', df.shape[1], '15 columns, same order')
df = blank_missing(df, ['age', 'height_cm', 'weight_kg', 'medal'], DS)
log(DS, 'medal', 'meaning_preserved', 'Medal missing for 231,333 rows', 'Kept blank (NOT replaced with "No Medal" / 0)',
    'Blank medal = athlete competed but did not medal; derived labels belong to the processing stage', int((df.medal == '').sum()), 'Blank medal rows preserved')
df = clean_text_cols(df, ['name', 'team', 'event', 'city', 'sport'], DS)
for c, nm in [('age', 'age'), ('height_cm', 'height_cm'), ('weight_kg', 'weight_kg')]:
    v = num_check(df[c], nm, DS)
    df[c] = fmt_num(v)
    log(DS, c, 'data_type', 'Numeric column read as text (contains NA tokens)', 'Validated all non-missing values numeric; stored as plain numbers',
        'Enable numeric use in Sheets/Looker', int(v.notna().sum()), f'min={v.min():g}, max={v.max():g}, no non-numeric values')
for c in ['athlete_id', 'year']:
    num_check(df[c], c, DS)
log(DS, 'age/height_cm/weight_kg', 'impossible_values', 'Checked for impossible ages/heights/weights',
    'No change: age 10-97, height 127-226 cm, weight 25-214 kg are all within plausible Olympic ranges (e.g. age 10 = a child gymnast in 1896, age 97 = art competitor, 214 kg = judo)',
    'No evidence of invalid values; extreme values are plausible and were not altered', 0, 'No values removed or capped')
STATS['ae_extremes'] = {'age': [10, 97], 'height': [127, 226], 'weight': [25, 214]}

# duplicates (after whitespace normalisation)
dups_all = df.duplicated(keep='first')
extra_medal = dups_all & (df.medal != '')
extra_nomedal = dups_all & (df.medal == '')
STATS['ae_dup_extra_total'] = int(dups_all.sum())
STATS['ae_dup_extra_medal'] = int(extra_medal.sum())
STATS['ae_dup_extra_nomedal'] = int(extra_nomedal.sum())
STATS['ae_dup_nomedal_sport'] = df[extra_nomedal].sport.value_counts().to_dict()
STATS['ae_dup_nomedal_games'] = df[extra_nomedal].games.value_counts().to_dict()
removed_ae = df[extra_medal].copy()
removed_ae.to_csv(OUT + 'documentation/REMOVED_ROWS_athlete_events_duplicate_medal_records.csv', index=False, encoding='utf-8', lineterminator='\n')
ae_confirmed_extra_keys = Counter(map(tuple, df[extra_medal][['name', 'sex', 'age', 'team', 'noc', 'year', 'season', 'city', 'sport', 'event', 'medal']].values))
log(DS, 'all', 'exact_duplicates_medal_bearing', f'{int(dups_all.sum())} rows are exact copies (all 15 columns incl. athlete_id) of an earlier row; {int(extra_medal.sum())} of them carry a medal (all 1900 Paris sailing crew entries, boats Olle / Favorite-1 / Quand-Mme-2)',
    f'REMOVED the {int(extra_medal.sum())} extra copies of medal-bearing exact duplicates; first occurrence kept (athlete still has their medal row)',
    'The same athlete cannot win the same medal twice in the same event; keeping the copies would double-count athlete-level medals. Removed rows saved in documentation/',
    int(extra_medal.sum()), f'{int(df[extra_medal].duplicated().sum())} dup copies of those remain after removal; no IND rows affected',
    f"MEDAL-STATISTICS IMPACT: {int((removed_ae.medal=='Gold').sum())} Gold-row and {int((removed_ae.medal=='Silver').sum())} Silver-row extras removed ({removed_ae.noc.unique().tolist()}, {removed_ae.year.unique().tolist()}). India unaffected.")
log(DS, 'all', 'exact_duplicates_retained', f'{int(extra_nomedal.sum())} exact-duplicate-looking rows without a medal ({df[extra_nomedal].sport.value_counts().to_dict()}), all in 1900-1948 Games',
    'RETAINED (not removed)', 'Art Competitions: one artist entering several works in the same category produces identical rows (e.g. Louis-Martin Rey x3). Remaining cases are not provably erroneous and carry no medal, so cannot distort medal totals. Not safe to dedupe without evidence.',
    int(extra_nomedal.sum()), 'Documented; analyst should use COUNT DISTINCT athlete_id for athlete counts', 'Flagged for processing stage')
df = df[~extra_medal].reset_index(drop=True)
log(DS, 'name', 'false_duplicate_protection', "Three different India hockey players named 'Balbir Singh' (1968, ids 111012/111013/111014); two share identical age 23 only when athlete_id is ignored",
    'Kept all rows; duplicate test performed WITH athlete_id', 'Name-only de-duplication would wrongly delete a real Indian Bronze medallist', 1, 'All 3 Balbir Singh 1968 rows retained',
    'India-specific integrity decision')
log(DS, 'name', 'encoding_loss', "Accented characters are missing from names in the source (e.g. 'Andr Auffray' for Andre, 'Henri Lon Victor Susse'); 0 non-ASCII characters in the whole column",
    'No change - cannot be repaired without inventing text', 'Characters were dropped upstream (not mis-encoded); restoring them would require external data/guessing', 0, 'Flagged', 'Unresolved source limitation')
log(DS, 'city', 'host_city', "1956 Summer has two city values (Melbourne + Stockholm - equestrian events were held in Stockholm)", 'No change', 'Legitimate; Games edition is not forced to one city', 0, 'Preserved')
log(DS, 'games/year/season', 'consistency', 'Checked games == year + " " + season for all rows', 'No change needed', 'Fully consistent', 0, '0 mismatches; seasons = Summer/Winter only')
log(DS, 'sex/medal', 'categorical_consistency', 'Sex {M,F}; Medal {Gold,Silver,Bronze,blank}', 'No change needed', 'Already consistent; no spelling/casing variants', 0, 'Categories verified')
mrow = df[df.medal != '']
n_art = int((mrow.sport == 'Art Competitions').sum()); n_alp = int((mrow.sport == 'Alpinism').sum()); n_alp_ind = int(((mrow.sport == 'Alpinism') & (mrow.noc == 'IND')).sum())
STATS['ae_art_medal_rows'] = n_art; STATS['ae_alpinism_medal_rows'] = n_alp; STATS['ae_alpinism_ind_rows'] = n_alp_ind
log(DS, 'sport/medal', 'olympic_specific_non_standard_medals', f"{n_art} medal rows are in Art Competitions (1912-1948) and {n_alp} in Alpinism (1924 Chamonix); {n_alp_ind} of them are India (7 athletes with the surname Sherpa, Gold, 'Alpinism Mixed Alpinism', 1924 Winter, team India)",
    'Kept unchanged', 'They are genuine source records, but these events are not reflected in the provided country-wise table (it shows India winter medals = 0). Removing them would be an unsupported assumption',
    n_art + n_alp, 'Flagged', 'MEDAL-STATISTICS IMPACT: India winter Gold (1924 Alpinism) exists at athlete level but not in olympics_medals_country_wise; decide treatment in processing stage')
df['sex'] = df['sex'].str.upper()
write(df, 'primary/' + DS)
STATS[DS] = dict(before=before, after_rows=len(df))
ae_clean = df.copy()

# ================================================================= 2. all_athlete_games (PRIMARY)
DS = 'all_athlete_games_cleaned.csv'
raw = a2_raw.copy()
before = dict(rows=len(raw), cols=raw.shape[1], dups=dup_count(raw.drop(columns='Entry ID')), missing=n_missing(raw))
df = raw.rename(columns={'Entry ID': 'entry_id', 'Name': 'name', 'Gender': 'sex', 'Age': 'age', 'Team': 'team', 'NOC': 'noc', 'Year': 'year',
                         'Season': 'season', 'City': 'city', 'Sport': 'sport', 'Event': 'event', 'Medal': 'medal',
                         'Sport Disciplines': 'sport_disciplines', 'Event List': 'event_list'})
log(DS, 'all', 'column_naming', "Names with spaces and capitals ('Entry ID', 'Sport Disciplines', 'Event List'); athlete sex column called 'Gender'",
    "Renamed to snake_case; Gender->sex to match athlete_events_cleaned", 'Consistent naming across cleaned files', df.shape[1], '14 columns, same order')
g = df.sex.map({'Male': 'M', 'Female': 'F'})
assert g.notna().all()
df['sex'] = g
log(DS, 'sex', 'categorical_consistency', "Values 'Male' / 'Female'", "Mapped to 'M' / 'F'", 'Same coding as athlete_events_cleaned (lossless, 1:1 mapping)', len(df), 'Categories: M, F')
df = clean_text_cols(df, ['name', 'team', 'event', 'city', 'sport'], DS)
for c in ['age']:
    v = num_check(df[c], c, DS)
    df[c] = fmt_num(v)
for c in ['entry_id', 'year']:
    num_check(df[c], c, DS)
log(DS, 'age', 'data_type', 'Age stored as text with blanks', 'Validated numeric (10-97 range); blanks left blank', 'Numeric typing without imputation', int((df.age != '').sum()), 'No non-numeric values')
key_cols = ['name', 'sex', 'age', 'team', 'noc', 'year', 'season', 'city', 'sport', 'event', 'medal']
# remove only the extras CONFIRMED in athlete_events (which has athlete_id) -> avoids deleting same-name different athletes
df = df.sort_values('entry_id', key=lambda s: s.astype(int)).reset_index(drop=True)
drop_idx = []
rm_keys = pd.DataFrame(list(ae_confirmed_extra_keys.keys()), columns=key_cols)
rm_keys['n'] = list(ae_confirmed_extra_keys.values())
df['_k'] = df[key_cols].apply(tuple, axis=1)
kmap = {tuple(r[key_cols]): r['n'] for _, r in rm_keys.iterrows()}
cand = df[df['_k'].isin(kmap.keys())]
for k, grp in cand.groupby('_k'):
    n = kmap[k]
    assert len(grp) > n
    drop_idx += list(grp.index[-n:])
removed_a2 = df.loc[drop_idx].drop(columns='_k')
removed_a2.to_csv(OUT + 'documentation/REMOVED_ROWS_all_athlete_games_duplicate_medal_records.csv', index=False, encoding='utf-8', lineterminator='\n')
df = df.drop(index=drop_idx).drop(columns='_k').reset_index(drop=True)
STATS['a2_removed'] = len(drop_idx)
log(DS, 'all', 'exact_duplicates_medal_bearing', 'File has no athlete id, so identical-looking rows may be different people. 11 medal-bearing duplicate records were confirmed in athlete_events (same athlete_id)',
    f'REMOVED {len(drop_idx)} rows - exactly the confirmed 1900 sailing duplicate medal records (matched on all attributes, last Entry ID of each group)',
    'Keeps medal counts identical across the two athlete-level files. A name-only rule would have wrongly deleted a real India 1968 hockey Bronze row (Balbir Singh) - this was avoided',
    len(drop_idx), 'Cleaned a2 rows for years <= 2016 reconcile exactly with athlete_events_cleaned (see validation)', f"MEDAL-STATISTICS IMPACT: same {int((removed_a2.medal=='Gold').sum())} Gold + {int((removed_a2.medal=='Silver').sum())} Silver rows as athlete_events")
log(DS, 'all', 'exact_duplicates_retained', 'Remaining attribute-identical rows (Art Competitions 1912-1948, early Sailing/Cycling, India 1968/1980 hockey)', 'RETAINED', 'Cannot be proven erroneous; same reasoning as athlete_events',
    int(df.drop(columns='entry_id').duplicated().sum()), 'Documented', 'Count is 1 higher than athlete_events (1,374) because the India 1968 hockey pair of 23-year-old Balbir Singh rows is only distinguishable by athlete_id, which this file lacks')
# empties
df = df.replace({'sport_disciplines': {}})
blank_sport = df[df.sport == ''].year.value_counts().to_dict()
STATS['a2_blank_sport_by_year'] = blank_sport
log(DS, 'sport/event/medal', 'structural_missingness', f'{sum(blank_sport.values())} rows (2024 Summer: {blank_sport.get("2024",0)}, 2026 Winter: {blank_sport.get("2026",0)}) have blank sport, event AND medal; sport_disciplines/event_list populated instead',
    'Kept as-is (blank)', 'These are entry-roster rows without results; a blank medal here means "results not in the source", NOT "no medal". Cannot be filled without external data',
    sum(blank_sport.values()), 'Preserved; flagged in README', 'IMPORTANT: do not use 2024/2026 rows for medal or sport analysis from this file')
log(DS, 'team', 'missing', '2026 Winter rows (2,916) have blank team', 'Kept blank', 'Not guessable (noc is populated and unchanged)', int((df.team == '').sum()), 'Preserved')
log(DS, 'city', 'host_city_vs_country', "2026 Winter rows have city = 'Italy' (a host COUNTRY; Games were hosted by Milano-Cortina)", 'Kept original value, flagged',
    'Correcting it would mean choosing/inventing a single host city for a co-hosted edition; not supported by the source', int((df.city == 'Italy').sum()), 'Flagged as unresolved', 'Unresolved - decide in processing stage')
log(DS, 'sport', 'inconsistent_sport_labels', "Era-specific labels co-exist: Canoeing vs Canoe Sprint/Slalom, Equestrian vs Equestrianism, Trampolining vs Trampoline Gymnastics, Gymnastics vs Artistic Gymnastics, Cycling vs Cycling Road/Track/MTB/BMX",
    'Not merged', 'Merging would change sport/discipline meaning and medal grain; needs a documented mapping table in the processing stage', 0, 'Flagged')
yrs = set(df.year)
assert '2018' not in yrs and '2022' not in yrs
log(DS, 'year', 'coverage_gap', 'Winter 2018 (PyeongChang) and Winter 2022 (Beijing) are absent from all athlete-level files (winter years run ...2014, then 2026); Summer 2020 has medals, Summer 2024 and Winter 2026 are roster-only',
    'No change - cannot be added without external data', 'Athlete-level winter history ends at 2014 for results; olympics_medals_country_wise includes later winter medals', 0, 'Flagged',
    'Unresolved: India winter participation 2018/2022 cannot be analysed from athlete files')
write(df, 'primary/' + DS)
a2_clean = df.copy()
STATS[DS] = dict(before=before, after_rows=len(df))

# ================================================================= 3. regions (SUPPORTING)
DS = 'regions_cleaned.csv'
raw = rd('archive/regions.csv')
before = dict(rows=len(raw), cols=raw.shape[1], dups=dup_count(raw), missing=n_missing(raw))
df = raw.drop(columns=['Unnamed: 0']).rename(columns={'NOC': 'noc', 'region': 'region', 'notes': 'notes'})
log(DS, 'Unnamed: 0', 'accidental_index_column', 'Pandas index (0..233) saved as an unnamed first column', 'Dropped', 'Row counter with no meaning', len(raw), '3 columns remain: noc, region, notes')
df = clean_text_cols(df, ['noc', 'region', 'notes'], DS)
df = blank_missing(df, ['region', 'notes'], DS, label='NaN')
log(DS, 'region', 'missing', "3 NOCs have no region (ROT, TUV, UNK) although 'notes' holds a name for two of them", 'Kept blank', 'Filling region from notes or world knowledge would be a guess/enrichment; flagged',
    int((df.region == '').sum()), 'Preserved', 'Unresolved')
log(DS, 'noc', 'mapping_gaps', "NOC 'AIN' (in all_athlete_games 2024) is absent; 'TRI','IOP' (in 1976-2008 medals) absent; region is a MODERN grouping (YUG->Serbia, URS->Russia, FRG/GDR->Germany)",
    'No rows added, no historical names overwritten', 'Rule: never invent mappings / rename historical entities from a modern lookup', 0, 'Flagged', 'Use as a lookup only; keep original noc/team in facts')
log('archive2/all_regions.csv', 'all', 'redundant_file', 'Identical NOC->Region content (234 rows, same order) to archive/regions.csv minus the notes column', 'Not cleaned separately', 'Redundant', 234, 'Verified identical on noc and region')
write(df, 'supporting/' + DS)
STATS[DS] = dict(before=before, after_rows=len(df))
regions_clean = df.copy()

# ================================================================= 4. Summer medals 1976-2008 (SUPPORTING)
DS = 'summer_olympic_medals_1976_2008_cleaned.csv'
raw = rd('Summer-Olympic-medals-1976-to-2008.csv', 'cp1252')
before = dict(rows=len(raw), cols=raw.shape[1], dups=dup_count(raw), missing=n_missing(raw))
log(DS, 'all', 'encoding', "File is Windows-1252 (not UTF-8): accented names such as KÖHLER appear corrupted when opened as UTF-8", 'Decoded as cp1252, saved as UTF-8', 'Text encoding fix; no characters lost', len(raw), 'Accented characters verified (e.g. KÖHLER, Christa)')
blank = raw.apply(lambda c: c.str.strip() == '').all(axis=1)
df = raw[~blank].copy()
log(DS, 'all', 'empty_rows', f'{int(blank.sum())} rows where every field is empty (",,,,,,,,,,")', 'Removed', 'Contain no information', int(blank.sum()), f'{len(df)} data rows remain; 0 empty rows')
df = df.rename(columns={'City': 'city', 'Year': 'year', 'Sport': 'sport', 'Discipline': 'discipline', 'Event': 'event', 'Athlete': 'athlete',
                        'Gender': 'sex', 'Country_Code': 'noc', 'Country': 'country', 'Event_gender': 'event_gender', 'Medal': 'medal'})
log(DS, 'all', 'column_naming', 'Mixed-case / underscore names (Country_Code, Event_gender)', 'Renamed to snake_case; Country_Code->noc, Gender->sex', 'Consistent naming', df.shape[1], '11 columns')
df = clean_text_cols(df, list(df.columns), DS)
sx = df.sex.map({'Men': 'M', 'Women': 'F'}); assert sx.notna().all()
df['sex'] = sx
log(DS, 'sex', 'categorical_consistency', "Athlete gender coded 'Men'/'Women'", "Mapped to 'M'/'F'", 'Same coding as other athlete-level files; event_gender (M/W/X) kept unchanged because it describes the EVENT', len(df), 'Categories: M, F')
log(DS, 'sex/event_gender', 'source_inconsistency', "1 row: CHEPCHUMBA, Joyce (Kenya, 2000 marathon, event_gender W) has gender 'Men'", 'Left unchanged, flagged', 'Likely an entry error but correcting it is an assumption', 1, 'Flagged', 'Unresolved')
df['country_original'] = df['country']
df['country'] = df.country.str.replace(r'\*$', '', regex=True).str.strip()
star = int((df.country != df.country_original).sum())
df = df[['city', 'year', 'sport', 'discipline', 'event', 'athlete', 'sex', 'noc', 'country', 'country_original', 'event_gender', 'medal']]
log(DS, 'country', 'formatting', f"{star} rows have a trailing '*' (Puerto Rico*, Hong Kong*, Bermuda*, Netherlands Antilles*, Virgin Islands*) - meaning is not documented in the source",
    "Added 'country' without the asterisk; original text preserved in 'country_original'", 'Asterisk blocks joins/grouping; original kept so nothing is lost', star, 'country_original retains all original values')
log(DS, 'noc/country', 'historical_codes', "Codes URS, EUN, GDR, FRG, SCG, SRB, IOP, AHO etc. and country 'Serbia' used for BOTH SCG (2004) and SRB (2008)", 'Preserved exactly', 'Historical NOC context must not be modernised', 0, 'Flagged', 'SCG and SRB both carry country=Serbia')
log(DS, 'noc', 'mapping_gap', "'TRI' (Trinidad and Tobago in this file) is not in regions (which has TTO)", 'Unchanged', 'No reliable mapping in provided data; flagged', int((df.noc == 'TRI').sum()), 'Flagged')
log(DS, 'athlete', 'source_quality', "Names with repeated given/surnames such as 'SINGH, Singh', 'CHETTRI, Chettri' (India 1980 hockey) - truncated source names", 'Unchanged', 'Cannot be repaired without external data', int(df.athlete.str.match(r'^(.+), \1$', case=False).sum()), 'Flagged')
dd = df.duplicated(keep=False)
log(DS, 'all', 'exact_duplicates_retained', f"{int(df.duplicated().sum())} exact duplicate row: India 1980 Hockey 'SINGH, Singh' appears twice (two different players with the same truncated name; India's squad of 16 requires both)",
    'RETAINED', 'Removing it would drop a real Indian Gold-medal record (16 expected, 16 present)', int(df.duplicated().sum()), '16 India 1980 Gold rows retained', 'India-specific integrity decision')
df['year'] = df.year.astype(int).astype(str)
write(df, 'supporting/' + DS)
STATS[DS] = dict(before=before, after_rows=len(df))

# ================================================================= 5. country-wise all-time (PRIMARY)
DS = 'olympics_medals_country_wise_cleaned.csv'
raw = rd('olympics_medals_country_wise.csv')
before = dict(rows=len(raw), cols=raw.shape[1], dups=dup_count(raw), missing=n_missing(raw))
df = raw.copy()
oldcols = list(df.columns)
df.columns = [c.strip() for c in df.columns]
log(DS, 'countries / ioc_code / total_total', 'column_naming', f"Header names contain trailing spaces: {[c for c in oldcols if c != c.strip()]}", 'Trimmed; countries->country, ioc_code->noc, total_participation->total_participations (matches summer_/winter_ plural); all other medal columns unchanged',
    'Clean, consistent names', 3, '17 columns')
df = df.rename(columns={'countries': 'country', 'ioc_code': 'noc', 'total_participation': 'total_participations'})
df = clean_text_cols(df, ['country', 'noc'], DS)
pn = df.noc.str.match(r'^\([A-Z0-9]{3}\)$')
assert pn.all()
df['noc'] = df.noc.str.strip('()')
log(DS, 'noc', 'formatting', "IOC codes stored in parentheses, e.g. '(AFG)'", 'Removed parentheses', 'Codes must match NOC codes used in other files', len(df), 'All 156 codes are 3 characters')
comma_cells = 0
numcols = [c for c in df.columns if c not in ('country', 'noc')]
for c in numcols:
    m = df[c].str.contains(',')
    if m.any():
        comma_cells += int(m.sum())
        df[c] = df[c].str.replace(',', '')
log(DS, 'summer_gold, summer_total, total_gold, total_total', 'numeric_stored_as_text', f"{comma_cells} cells use thousands separators, e.g. '1,060', '2,629' (United States)", 'Removed commas; converted to integers', 'Numbers stored as text cannot be summed', comma_cells, 'All 15 numeric columns parse as integers')
for c in numcols:
    num_check(df[c], c, DS)
n = df[numcols].astype(int)
ok = ((n.summer_total == n.summer_gold + n.summer_silver + n.summer_bronze) & (n.winter_total == n.winter_gold + n.winter_silver + n.winter_bronze) &
      (n.total_total == n.summer_total + n.winter_total) & (n.total_gold == n.summer_gold + n.winter_gold) & (n.total_silver == n.summer_silver + n.winter_silver) &
      (n.total_bronze == n.summer_bronze + n.winter_bronze) & (n.total_participations == n.summer_participations + n.winter_participations))
log(DS, 'medal columns', 'arithmetic_consistency', 'Checked gold+silver+bronze=total and summer+winter=total for every row', 'No change needed', 'Internal consistency confirms values are intact', int((~ok).sum()), f'{int(ok.sum())}/{len(df)} rows consistent')
assert ok.all()
log(DS, 'country/noc', 'historical_entities', 'Includes Soviet Union (URS), East/West Germany, Czechoslovakia, Yugoslavia, Russian Empire (RU1), Mixed Team (ZZX), ROC, OAR, Independent Olympic Participants', 'Preserved as separate rows (no merging into modern countries)', 'Historical context must not be renamed/merged', 0, 'Flagged')
log(DS, 'all', 'coverage', 'India row: 25 summer + 11 winter participations; 10G 9S 16B = 35 summer medals - equals India\'s total through Tokyo 2020 (7 medals in 2020), i.e. does NOT include Paris 2024', 'Unchanged', 'Edition coverage inferred from the India row; document before combining with Paris 2024 tables', 1, 'Flagged', 'Do not add Paris 2024 totals without checking double counting')
for c in numcols:
    df[c] = df[c].astype(int).astype(str)
write(df, 'primary/' + DS)
STATS[DS] = dict(before=before, after_rows=len(df))

# ================================================================= 6. olympics.csv GDP/population (SUPPORTING)
DS = 'olympics_2024_country_gdp_population_cleaned.csv'
raw = rd('olympics.csv')
before = dict(rows=len(raw), cols=raw.shape[1], dups=dup_count(raw), missing=n_missing(raw))
df = raw.copy()
df = clean_text_cols(df, list(df.columns), DS)
for c in ['gold', 'silver', 'bronze', 'total', 'gdp_year']:
    num_check(df[c], c, DS)
for c in ['gdp', 'population']:
    v = num_check(df[c], c, DS)
    df[c] = fmt_num(v)
assert (df.total.astype(int) == df.gold.astype(int) + df.silver.astype(int) + df.bronze.astype(int)).all()
sc = df.apply(lambda r: std_ioc(r.country_code, r.country), axis=1)
df = df.rename(columns={'country_code': 'country_code_original'})
df.insert(2, 'noc', [a for a, b in sc])
df['noc_standardization'] = [b for a, b in sc]
cnt = Counter(b for a, b in sc)
changed = int((df.noc != df.country_code_original).sum())
log(DS, 'country_code', 'inconsistent_noc_codes', f"Codes are ISO-3-style (e.g. DEU, NLD, DNK, ZAF) or other non-IOC codes, so they don't match NOC codes used in athlete files; {changed} codes differ from the IOC code in the Paris roster files",
    "Original preserved in 'country_code_original'; added 'noc' (IOC code) + 'noc_standardization' (method). IOC code taken only from the provided Paris roster files (athletes new.csv / all_athlete_games 2024) by exact country-name match",
    'Allows reliable joins to athlete files without external data; unresolved codes left blank rather than guessed', changed, f'Methods: {dict(cnt)}',
    'Source: provided files only; no external data used. Aliases used: Iran->IR Iran, Hong Kong->Hong Kong, China, Taiwan->Chinese Taipei (label differences only)')
log(DS, 'country', 'source_difference', "'Taiwan' here vs 'Chinese Taipei' in olympics2024.csv; Refugee Olympic Team (EOR, 1 Bronze) absent so medal totals are 1 Bronze lower than olympics2024.csv", 'Unchanged; flagged', 'Not a cleaning error - a coverage difference. Use olympics2024.csv as the authoritative Paris medal table', 1, 'Flagged')
log(DS, 'gdp / population', 'undocumented_units', "gdp (e.g. United States 81,695.19) matches GDP PER CAPITA in USD, population (334.9) matches MILLIONS; units/source not documented; gdp_year mixes 2023 (88 rows) and 2022 (2 rows)", 'Values and column names unchanged', 'Renaming would assert a unit not stated in the source', 90, 'Flagged', 'Verify units before using in dashboards')
log(DS, 'region', 'categorical_consistency', 'Region values (Europe, Asia, Africa, North America, South America, Caribbean, Oceania)', 'No change needed', 'Consistent; note: this is a geographic grouping created by the dataset author', 90, '7 categories')
df = df[['country', 'country_code_original', 'noc', 'noc_standardization', 'region', 'gold', 'silver', 'bronze', 'total', 'gdp', 'gdp_year', 'population']]
write(df, 'supporting/' + DS)
STATS[DS] = dict(before=before, after_rows=len(df))
olymp_csv = df.copy()

# ================================================================= 7. olympics2024.csv (EDITION: Paris 2024 by country)
DS = 'paris_2024_medals_by_country_cleaned.csv'
raw = rd('olympics2024.csv')
before = dict(rows=len(raw), cols=raw.shape[1], dups=dup_count(raw), missing=n_missing(raw))
df = raw.rename(columns={'Rank': 'rank', 'Country': 'country', 'Country Code': 'country_code_original', 'Gold': 'gold', 'Silver': 'silver', 'Bronze': 'bronze', 'Total': 'total'})
log(DS, 'all', 'column_naming', "Capitalised names with spaces ('Country Code')", 'Renamed to snake_case', 'Consistent naming', df.shape[1], '7 -> 9 columns after adding noc fields')
df = clean_text_cols(df, list(df.columns), DS)
for c in ['rank', 'gold', 'silver', 'bronze', 'total']:
    num_check(df[c], c, DS)
assert (df.total.astype(int) == df.gold.astype(int) + df.silver.astype(int) + df.bronze.astype(int)).all()
sc = df.apply(lambda r: std_ioc(r.country_code_original, r.country), axis=1)
df.insert(3, 'noc', [a for a, b in sc]); df['noc_standardization'] = [b for a, b in sc]
cnt = Counter(b for a, b in sc)
changed = int((df.noc != df.country_code_original).sum())
log(DS, 'country_code', 'inconsistent_noc_codes', f"Mixed code styles: IOC (USA, CHN), 2-letter (US, NZ, HK, SA) and invented/legacy forms (SIN, SPA, SWI, GBG, BRZ, PKN, SER, ROM, MOR, IRE); {changed} of {len(df)} differ from IOC codes in the Paris roster",
    "Original kept in 'country_code_original'; 'noc' = IOC code from provided Paris roster files by exact country name; method in 'noc_standardization'", 'Join key must match athlete files; unresolved left blank', changed, f'Methods: {dict(cnt)}',
    'Source: provided files only. Aliases used: Iran->IR Iran, Hong Kong->Hong Kong, China (label differences only)')
log(DS, 'rank', 'ties', 'Ranks repeat (ties on identical medal counts, e.g. many countries share a rank) and run to 84+ ', 'Unchanged', 'Legitimate ranking ties', 0, 'Preserved')
log(DS, 'total', 'meaning', 'Country medal COUNTS (a team medal counts once)', 'Unchanged', 'Grain: one row = one country/NOC at Paris 2024. Not comparable to athlete-level medal rows', 0, 'Totals: ' + f"{df.gold.astype(int).sum()}G/{df.silver.astype(int).sum()}S/{df.bronze.astype(int).sum()}B")
write(df, 'edition_specific/' + DS)
STATS[DS] = dict(before=before, after_rows=len(df))
paris_country = df.copy()

# ================================================================= 8. Olympics 2024.csv (EDITION: Paris 2024 by sport x country)
DS = 'paris_2024_medals_by_sport_cleaned.csv'
raw = rd('Olympics 2024.csv')
before = dict(rows=len(raw), cols=raw.shape[1], dups=dup_count(raw), missing=n_missing(raw))
df = raw.rename(columns={'Competitions': 'sport', 'Rank': 'rank_in_sport', 'NOC': 'country', 'Gold': 'gold', 'Silver': 'silver', 'Bronze': 'bronze', 'Total': 'total'})
log(DS, 'Competitions / NOC', 'column_naming', "'Competitions' holds SPORT names; 'NOC' holds COUNTRY NAMES (not NOC codes)", "Renamed to 'sport' and 'country'; Rank->rank_in_sport (rank is within each sport)", 'Misleading headers would cause wrong joins', len(df), 'Renamed')
nb = int((raw.NOC.str.contains(' ')).sum())
df = clean_text_cols(df, ['sport', 'country'], DS)
log(DS, 'country', 'hidden_spaces', f'{nb} of {len(raw)} country cells start with a non-breaking space (U+00A0)', 'Converted/trimmed (included in whitespace action above)', 'Hidden characters break joins to other country lists', nb, '0 cells with leading/trailing/nbsp whitespace')
df['country_original'] = df['country']
df['country'] = df.country.str.replace(r'\*$', '', regex=True).str.replace(r'\[[A-Za-z0-9]+\]$', '', regex=True).str.strip()
st = int((df.country != df.country_original).sum())
fn = int(df.country_original.str.contains(r'\[[A-Za-z0-9]+\]').sum())
log(DS, 'country', 'formatting', f"{st} rows carry a marker that is not part of the country name: 'France*' ({st - fn} rows; asterisk = host nation, Wikipedia convention) and 'Individual Neutral Athletes[A]' ({fn} row; '[A]' is a Wikipedia footnote tag)", "Added 'country' without the marker; original (trimmed) value kept in 'country_original'", 'Joinable country name while keeping the marker information', st, 'country_original retains markers; country has none')
log(DS, 'country', 'coverage_difference', "'Individual Neutral Athletes' (neutral athletes) medals appear here (Gymnastics, Rowing, Tennis, Weightlifting) but not in paris_2024_medals_by_country; 'Saint Lucia' here is 'St Lucia' there", 'Unchanged', 'Real differences between source tables, not errors to fix; sport-level totals = country-table totals + Individual Neutral Athletes', 5, 'Reconciled in validation', 'Do not mix this table with the country table without handling Individual Neutral Athletes')
dash = int((df.rank_in_sport == '–').sum()) + int((~df.rank_in_sport.str.match(r'^\d+$')).sum()) - int((df.rank_in_sport == '–').sum())
nr = df.rank_in_sport[~df.rank_in_sport.str.match(r'^\d+$')]
df.loc[nr.index, 'rank_in_sport'] = ''
log(DS, 'rank_in_sport', 'invalid_numeric', f"{len(nr)} rank cell = '–' (en dash) for 'Individual Neutral Athletes' (Gymnastics)", 'Set to blank', 'Not a number: athletes competed neutrally (unranked); blank = not applicable. Medals kept', len(nr), 'rank_in_sport otherwise integer')
for c in ['rank_in_sport', 'gold', 'silver', 'bronze', 'total']:
    num_check(df[c], c, DS)
assert (df.total.astype(int) == df.gold.astype(int) + df.silver.astype(int) + df.bronze.astype(int)).all()
log(DS, 'sport', 'categorical_consistency', "Sport labels use sentence case (e.g. 'Field hockey', 'Rugby sevens', 'Artistic swimming') unlike other files (Hockey, Rugby Sevens, Synchronized Swimming)", 'Unchanged', 'Mapping across files is a processing-stage task', len(df), '35 sports')
write(df[['sport', 'rank_in_sport', 'country', 'country_original', 'gold', 'silver', 'bronze', 'total']], 'edition_specific/' + DS)
df = df[['sport', 'rank_in_sport', 'country', 'country_original', 'gold', 'silver', 'bronze', 'total']]
STATS[DS] = dict(before=before, after_rows=len(df))
paris_sport = df.copy()

# ================================================================= 9. Tokyo (EDITION)
DS = 'tokyo_2020_medals_by_country_cleaned.csv'
raw = rd('Tokyo Medals 2021.csv')
before = dict(rows=len(raw), cols=raw.shape[1], dups=dup_count(raw), missing=n_missing(raw))
df = raw.rename(columns={'Country': 'country', 'Gold Medal': 'gold', 'Silver Medal': 'silver', 'Bronze Medal': 'bronze', 'Total': 'total', 'Rank By Total': 'rank_by_total'})
log(DS, 'all', 'column_naming', "'Gold Medal', 'Rank By Total' etc.", 'Renamed to gold, silver, bronze, total, rank_by_total', 'Consistent naming', df.shape[1], '6 columns')
df = clean_text_cols(df, list(df.columns), DS)
for c in ['gold', 'silver', 'bronze', 'total', 'rank_by_total']:
    num_check(df[c], c, DS)
assert (df.total.astype(int) == df.gold.astype(int) + df.silver.astype(int) + df.bronze.astype(int)).all()
log(DS, 'country', 'country_names', "Official-style names ('People's Republic of China', 'Republic of Korea', 'Islamic Republic of Iran', 'ROC', 'Hong Kong, China') differ from other files; no NOC code column", 'Unchanged; no code added', 'No reliable code mapping inside this file; mapping is a processing-stage join (flagged)', len(df), 'Flagged')
log(DS, 'file', 'edition_label', "File is named 'Tokyo Medals 2021' (Games held in 2021); athlete files label this edition Year 2020", 'File renamed tokyo_2020_*; value content unchanged', 'Edition is Tokyo 2020 (held 2021) - avoid year misalignment', len(df), 'Flagged')
write(df, 'edition_specific/' + DS)
STATS[DS] = dict(before=before, after_rows=len(df))
tokyo = df.copy()

# ================================================================= 10. athletes new.csv (EDITION: Paris 2024 roster)
DS = 'paris_2024_athletes_cleaned.csv'
raw = an_raw.copy()
before = dict(rows=len(raw), cols=raw.shape[1], dups=dup_count(raw), missing=n_missing(raw))
df = raw.rename(columns={'code': 'athlete_code', 'height': 'height_cm', 'weight': 'weight_kg', 'gender': 'sex'})
log(DS, 'code/gender/height/weight', 'column_naming', 'Ambiguous names', 'Renamed code->athlete_code, gender->sex, height->height_cm, weight->weight_kg', 'Consistent naming across athlete tables', 4, '17 columns')
df = clean_text_cols(df, [c for c in df.columns if c not in ('height_cm', 'weight_kg')], DS)
sx = df.sex.map({'Male': 'M', 'Female': 'F'}); assert sx.notna().all(); df['sex'] = sx
log(DS, 'sex', 'categorical_consistency', "'Male'/'Female'", "Mapped to 'M'/'F'", 'Consistent coding', len(df), 'Categories: M, F')
h = pd.to_numeric(df.height_cm); w = pd.to_numeric(df.weight_kg.replace('', pd.NA))
hz = int((h == 0).sum()); wz = int((w == 0).sum()); wb = int(w.isna().sum())
STATS['an_zero_height'] = hz; STATS['an_zero_weight'] = wz; STATS['an_blank_weight'] = wb
h = h.where(h > 0); w = w.where(w > 0)
df['height_cm'] = fmt_num(h); df['weight_kg'] = fmt_num(w)
log(DS, 'height_cm', 'invalid_numeric_sentinel', f'{hz} rows (of {len(df)}) have height = 0 (impossible; placeholder for unknown)', 'Set to blank (missing)', 'A height of 0 would corrupt averages; true value unknown, nothing imputed', hz, f'min height now {h.min():g}, max {h.max():g}')
log(DS, 'weight_kg', 'invalid_numeric_sentinel', f'{wz} rows have weight = 0.0 and {wb} are already blank', 'Zeros set to blank; blanks kept blank', 'Same reason as height', wz + wb, f'min weight now {w.min():g}, max {w.max():g}; {int(w.isna().sum())} missing in total')
bd = pd.to_datetime(df.birth_date, format='%Y-%m-%d', errors='raise')
log(DS, 'birth_date', 'date_format', 'Dates already ISO yyyy-mm-dd', 'Validated (all parse, 1954-12-01 to 2012-08-11); no change', 'Consistent date format', len(df), '0 invalid dates')
log(DS, 'disciplines / events', 'nested_values', "List-like strings with mixed quotes, e.g. [\"Women's Individual\", 'Mixed Team']", 'Unchanged', 'Exploding lists changes the grain (athlete -> athlete-event); belongs in processing stage', len(df), 'Flagged')
nd = int(df.name.duplicated(keep=False).sum())
log(DS, 'name', 'duplicates_investigated', f'{nd} rows share a name with another row (e.g. ELSAYED Mohamed, WATANABE Yuta, SUN Yue)', 'Retained', 'athlete_code is unique (11,115 distinct) and birth dates/disciplines differ: different people', nd, 'athlete_code unique')
mm = int((df.country_code != df.nationality_code).sum())
log(DS, 'country_code / nationality_code', 'meaning', f'{mm} athletes represent an NOC different from their nationality (e.g. PUR/ISV athletes with nationality USA)', 'Both kept', "country_code = NOC represented; use it (not nationality) for country totals", mm, 'Preserved')
log(DS, 'function', 'categorical_consistency', "'Athlete' (10,920) and 'Alternate Athlete' (195)", 'Both retained', 'Alternates are not competitors; filter in processing stage', int((df.function == 'Alternate Athlete').sum()), 'Preserved')
log(DS, 'file', 'edition_label', "File has no year/edition field; identified as Paris 2024 because it has 206 NOCs, 112 IND athletes (same as all_athlete_games 2024) and Paris disciplines", 'Named paris_2024_athletes; no year column added', 'Inference documented; nothing fabricated', len(df), 'Flagged')
write(df, 'edition_specific/' + DS)
STATS[DS] = dict(before=before, after_rows=len(df))

# ---------------------------------------------------------------- save log + stats
pd.DataFrame(LOG).to_csv(OUT + 'documentation/CLEANING_LOG.csv', index=False, encoding='utf-8', lineterminator='\n')
json.dump(STATS, open('/home/claude/work/stats.json', 'w'), indent=1, default=str)
print(len(LOG), 'log rows'); print(json.dumps({k: v for k, v in STATS.items() if k.endswith('.csv')}, indent=0, default=str))
