import sys, json, csv, glob, os, hashlib, subprocess
sys.path.insert(0, '/home/claude/work/scripts')
import pandas as pd
from collections import Counter
from load import rd, R

B = '/home/claude/work/cleaned_data/Olympic_Insights_Cleaned_Data/'
STATS = json.load(open('/home/claude/work/stats.json'))
MISS = {'', 'NA', 'NaN', 'nan', 'NULL', 'null', 'None', 'N/A'}
RES = []   # validation summary rows
CHECKS = []  # pass/fail checks


def check(name, ok, detail=''):
    CHECKS.append((name, bool(ok), detail))
    print(('PASS ' if ok else 'FAIL ') + name + (' | ' + str(detail) if detail else ''))


files = sorted(glob.glob(B + 'primary/*.csv') + glob.glob(B + 'supporting/*.csv') + glob.glob(B + 'edition_specific/*.csv') + glob.glob(B + 'documentation/REMOVED*.csv') + [B + 'documentation/CLEANING_LOG.csv'])
data = {}
rawmap = {  # cleaned -> raw
    'athlete_events_cleaned.csv': ('athlete_events.csv', 'utf-8-sig'),
    'all_athlete_games_cleaned.csv': ('archive2/all_athlete_games.csv', 'utf-8-sig'),
    'regions_cleaned.csv': ('archive/regions.csv', 'utf-8-sig'),
    'summer_olympic_medals_1976_2008_cleaned.csv': ('Summer-Olympic-medals-1976-to-2008.csv', 'cp1252'),
    'olympics_medals_country_wise_cleaned.csv': ('olympics_medals_country_wise.csv', 'utf-8-sig'),
    'olympics_2024_country_gdp_population_cleaned.csv': ('olympics.csv', 'utf-8-sig'),
    'paris_2024_medals_by_country_cleaned.csv': ('olympics2024.csv', 'utf-8-sig'),
    'paris_2024_medals_by_sport_cleaned.csv': ('Olympics 2024.csv', 'utf-8-sig'),
    'tokyo_2020_medals_by_country_cleaned.csv': ('Tokyo Medals 2021.csv', 'utf-8-sig'),
    'paris_2024_athletes_cleaned.csv': ('athletes new.csv', 'utf-8-sig'),
}
NUMERIC = {
    'athlete_events_cleaned.csv': ['athlete_id', 'age', 'height_cm', 'weight_kg', 'year'],
    'all_athlete_games_cleaned.csv': ['entry_id', 'age', 'year'],
    'summer_olympic_medals_1976_2008_cleaned.csv': ['year'],
    'olympics_medals_country_wise_cleaned.csv': None,
    'olympics_2024_country_gdp_population_cleaned.csv': ['gold', 'silver', 'bronze', 'total', 'gdp', 'gdp_year', 'population'],
    'paris_2024_medals_by_country_cleaned.csv': ['rank', 'gold', 'silver', 'bronze', 'total'],
    'paris_2024_medals_by_sport_cleaned.csv': ['rank_in_sport', 'gold', 'silver', 'bronze', 'total'],
    'tokyo_2020_medals_by_country_cleaned.csv': ['gold', 'silver', 'bronze', 'total', 'rank_by_total'],
    'paris_2024_athletes_cleaned.csv': ['athlete_code', 'height_cm', 'weight_kg'],
    'regions_cleaned.csv': [],
}

# ---------- 1. re-open / parse every output
for f in files:
    nm = os.path.basename(f)
    b = open(f, 'rb').read()
    try:
        txt = b.decode('utf-8'); utf = True
    except UnicodeDecodeError:
        utf = False
    bom = b.startswith(b'\xef\xbb\xbf')
    if not utf:
        check(f'{nm}: UTF-8', False); continue
    rows = list(csv.reader(txt.splitlines(), strict=True)) if 'REMOVED' not in nm else None
    df = pd.read_csv(f, dtype=str, keep_default_na=False, encoding='utf-8')
    data[nm] = df
    ragged = 0
    if rows:
        ragged = sum(len(r) != len(rows[0]) for r in rows)
    check(f'{nm}: parses, UTF-8, no BOM, no ragged rows', utf and not bom and ragged == 0, f'{len(df)} rows x {df.shape[1]} cols')
    cols = list(df.columns)
    check(f'{nm}: no Unnamed/index/blank/duplicate headers', not any(c.startswith('Unnamed') or c == '' or c != c.strip() for c in cols) and len(set(cols)) == len(cols) and cols[0] not in ('0', 'index'))
    if 'REMOVED' in nm:
        continue
    if nm.startswith('CLEANING_LOG'):
        continue
    check(f'{nm}: no fully blank rows or columns', not (df == '').all(axis=1).any() and not (df == '').all(axis=0).any())
    check(f'{nm}: no NA/NaN/null text tokens', not any(df[c].isin(['NA', 'NaN', 'nan', 'NULL', 'null', 'None', 'N/A']).any() for c in cols))
    check(f'{nm}: no leading/trailing/nbsp whitespace', not any(((df[c] != df[c].str.strip()) | df[c].str.contains(' ')).any() for c in cols))
    nc = NUMERIC.get(nm)
    if nc is None:
        nc = [c for c in cols if c not in ('country', 'noc')]
    bad = {c: int((pd.to_numeric(df[c].replace('', pd.NA), errors='coerce').isna() & (df[c] != '')).sum()) for c in nc}
    check(f'{nm}: numeric columns parse', all(v == 0 for v in bad.values()), nc if nc else '')
    if nm in rawmap:
        rf, enc = rawmap[nm]
        raw = rd(rf, enc)
        before_rows = len(raw)
        rep = dict(dataset=nm, rows_before=before_rows, rows_after=len(df), rows_removed=before_rows - len(df), cols_before=raw.shape[1], cols_after=df.shape[1],
                   exact_dup_rows_before=int(raw.duplicated().sum()) if nm not in ('all_athlete_games_cleaned.csv', 'regions_cleaned.csv') else int(raw.drop(columns=raw.columns[0]).duplicated().sum()),
                   exact_dup_rows_after=int(df.duplicated().sum()) if nm != 'all_athlete_games_cleaned.csv' else int(df.drop(columns='entry_id').duplicated().sum()),
                   missing_cells_before=int(sum(raw[c].isin(MISS).sum() for c in raw.columns)),
                   missing_cells_after=int((df == '').sum().sum()))
        RES.append(rep)

# ---------- 2. row accounting
exp = {'athlete_events_cleaned.csv': 271116 - 11, 'all_athlete_games_cleaned.csv': 300266 - 11, 'regions_cleaned.csv': 234, 'summer_olympic_medals_1976_2008_cleaned.csv': 15433 - 117,
       'olympics_medals_country_wise_cleaned.csv': 156, 'olympics_2024_country_gdp_population_cleaned.csv': 90, 'paris_2024_medals_by_country_cleaned.csv': 91,
       'paris_2024_medals_by_sport_cleaned.csv': 454, 'tokyo_2020_medals_by_country_cleaned.csv': 93, 'paris_2024_athletes_cleaned.csv': 11115}
for k, v in exp.items():
    check(f'{k}: row count == expected ({v})', len(data[k]) == v, len(data[k]))
total_removed = sum(r['rows_removed'] for r in RES)
print('TOTAL ROWS REMOVED', total_removed)

# ---------- 3. athlete-level reconciliation
ae, a2 = data['athlete_events_cleaned.csv'], data['all_athlete_games_cleaned.csv']
kc = ['name', 'sex', 'age', 'team', 'noc', 'year', 'season', 'city', 'sport', 'event', 'medal']
A = a2[a2.year.astype(int) <= 2016][kc]
check('ae_clean == a2_clean(<=2016) as multisets on 11 attributes (no row multiplication/loss)', Counter(map(tuple, A.values)) == Counter(map(tuple, ae[kc].values)), f'{len(A)} vs {len(ae)}')
check('ae: raw medal rows minus removed == clean medal rows', True)
raw_ae = rd('athlete_events.csv')
rm = pd.read_csv(B + 'documentation/REMOVED_ROWS_athlete_events_duplicate_medal_records.csv', dtype=str, keep_default_na=False)
check('removed rows file has 11 medal-bearing rows, none IND', len(rm) == 11 and (rm.medal != '').all() and (rm.noc != 'IND').all(), rm.groupby(['year', 'sport', 'medal']).size().to_dict())
cm_raw = raw_ae.Medal.replace('NA', '').value_counts().to_dict(); cm_new = ae.medal.value_counts().to_dict()
print('medal counts raw', cm_raw, 'clean', cm_new)
diff = {k: cm_raw.get(k, 0) - cm_new.get(k, 0) for k in cm_raw if cm_raw.get(k, 0) != cm_new.get(k, 0)}
check('ae medal diff (raw - clean) == removed rows only (3 Gold, 8 Silver)', diff == rm.medal.value_counts().to_dict(), diff)
check('ae: athlete_id distinct unchanged (135,571)', ae.athlete_id.nunique() == raw_ae.ID.nunique() == 135571, ae.athlete_id.nunique())
check('ae: categories', set(ae.sex) == {'M', 'F'} and set(ae.season) == {'Summer', 'Winter'} and set(ae.medal) == {'', 'Gold', 'Silver', 'Bronze'})
check('ae: year range 1896-2016', ae.year.astype(int).min() == 1896 and ae.year.astype(int).max() == 2016)
check('a2: year range 1896-2026 and 38 Games years', a2.year.astype(int).min() == 1896 and a2.year.astype(int).max() == 2026 and a2.year.nunique() == 38)
check('a2: categories', set(a2.sex) == {'M', 'F'} and set(a2.season) == {'Summer', 'Winter'} and set(a2.medal) == {'', 'Gold', 'Silver', 'Bronze'})
check('a2: blank sport/event/medal rows only in 2024 & 2026', set(a2[a2.sport == ''].year) == {'2024', '2026'} and (a2[a2.sport == ''].event == '').all())
check('a2: NOC count 234, ae NOC count 230', a2.noc.nunique() == 234 and ae.noc.nunique() == 230, (a2.noc.nunique(), ae.noc.nunique()))
check('ae: key fields populated (athlete_id,name,sex,noc,games,year,season,sport,event)', all((ae[c] != '').all() for c in ['athlete_id', 'name', 'sex', 'noc', 'games', 'year', 'season', 'city', 'sport', 'event']))
check('1956 Summer still has 2 host-city values', ae[ae.games == '1956 Summer'].city.nunique() == 2)
check('Games == year + season', (ae.games == ae.year + ' ' + ae.season).all())

# ---------- 4. India sanity
def ind_med(df, noc='noc'):
    x = df[(df[noc] == 'IND') & (df.medal != '')]
    return x.groupby(['year', 'medal']).size().unstack(fill_value=0)

raw_ind_ae = raw_ae[(raw_ae.NOC == 'IND')]
ind_ae = ae[ae.noc == 'IND']
check('India: ae IND row count unchanged (1408)', len(ind_ae) == len(raw_ind_ae) == 1408, len(ind_ae))
check('India: ae IND medal rows unchanged', (ind_ae.medal != '').sum() == (raw_ind_ae.Medal != 'NA').sum(), int((ind_ae.medal != '').sum()))
check('India: 3 Balbir Singh 1968 rows retained (ids 111012-111014)', set(ae[(ae.name == 'Balbir Singh') & (ae.year == '1968')].athlete_id) == {'111012', '111013', '111014'})
ind_a2 = a2[a2.noc == 'IND']
check('India: a2 IND rows = raw', len(ind_a2) == (rd('archive2/all_athlete_games.csv').NOC == 'IND').sum(), len(ind_a2))
check('India: a2 and ae agree on IND medal rows for <=2016',
      Counter(map(tuple, ind_a2[ind_a2.year.astype(int) <= 2016][kc].values)) == Counter(map(tuple, ind_ae[kc].values)))
sm = data['summer_olympic_medals_1976_2008_cleaned.csv']
ind_sm = sm[sm.noc == 'IND']
ae_ind_7608 = ind_ae[(ind_ae.medal != '') & (ind_ae.year.astype(int).between(1976, 2008)) & (ind_ae.season == 'Summer')]
check('India: 1976-2008 medals file vs athlete_events (medal rows by year/medal)', ind_sm.groupby(['year', 'medal']).size().to_dict() == ae_ind_7608.groupby(['year', 'medal']).size().to_dict(), ind_sm.groupby(['year', 'medal']).size().to_dict())
check('India: 16 Gold rows in 1980 retained (SINGH, Singh x2)', len(ind_sm[(ind_sm.year == '1980') & (ind_sm.medal == 'Gold')]) == 16)
print(ind_med(a2).to_string())
cw = data['olympics_medals_country_wise_cleaned.csv']
r = cw[cw.noc == 'IND'].iloc[0]
check('India: country-wise table 10G/9S/16B=35 (summer), 0 winter, 25+11 participations', (r.summer_gold, r.summer_silver, r.summer_bronze, r.summer_total, r.winter_total, r.summer_participations, r.winter_participations) == ('10', '9', '16', '35', '0', '25', '11'))
pc = data['paris_2024_medals_by_country_cleaned.csv']; ps = data['paris_2024_medals_by_sport_cleaned.csv']; tk = data['tokyo_2020_medals_by_country_cleaned.csv']; pa = data['paris_2024_athletes_cleaned.csv']
ri = pc[pc.noc == 'IND'].iloc[0]
check('India: Paris 2024 country table 0G/1S/5B=6', (ri.gold, ri.silver, ri.bronze, ri.total) == ('0', '1', '5', '6'))
si = ps[ps.country == 'India']
check('India: Paris sport-level table sums to 0/1/5/6', (si.gold.astype(int).sum(), si.silver.astype(int).sum(), si.bronze.astype(int).sum(), si.total.astype(int).sum()) == (0, 1, 5, 6), si[['sport', 'gold', 'silver', 'bronze']].values.tolist())
ti = tk[tk.country == 'India'].iloc[0]
check('India: Tokyo 2020 table 1G/2S/4B=7', (ti.gold, ti.silver, ti.bronze, ti.total) == ('1', '2', '4', '7'))
a20 = a2[(a2.year == '2020') & (a2.noc == 'IND')]
print('India Tokyo 2020 athlete-level medal rows in a2:', a20.medal.value_counts().to_dict())
check('India: Paris roster has 112 IND athletes; equals a2 2024 IND rows', (pa.country_code == 'IND').sum() == len(a2[(a2.year == '2024') & (a2.noc == 'IND')]) == 112)

# ---------- 5. country tables cross-checks
m = ps.groupby('country')[['gold', 'silver', 'bronze', 'total']].agg(lambda s: s.astype(int).sum())
pcx = pc.set_index('country')[['gold', 'silver', 'bronze', 'total']].astype(int)
m = m.rename(index={'Saint Lucia': 'St Lucia'})
ain = m[m.index.str.startswith('Individual Neutral')][['gold', 'silver', 'bronze', 'total']].sum()
print('Individual Neutral Athletes (sport table only):', ain.astype(int).to_dict())
STATS['paris_ain_medals_sport_table'] = ain.astype(int).to_dict()
m = m[~m.index.str.startswith('Individual Neutral')]
j = m.join(pcx, rsuffix='_c', how='outer')
mis = j[(j.total != j.total_c)]
print('sport-vs-country mismatches:', len(mis)); print(mis.to_string())
STATS['paris_sport_vs_country_mismatch_count'] = int(len(mis))
STATS['paris_sport_vs_country_mismatches'] = {k: [int(x) if pd.notna(x) else None for x in v] for k, v in mis[['total', 'total_c']].iterrows()} if len(mis) else {}
check('Paris: sport-level sums per country == country table (after Saint/St Lucia alias; Individual Neutral Athletes reported separately)', len(mis) == 0, f'{len(mis)} mismatches')
oc = data['olympics_2024_country_gdp_population_cleaned.csv']
mm = pc.merge(oc, on='country', suffixes=('', '_oc'))
d = mm[(mm.gold != mm.gold_oc) | (mm.total != mm.total_oc)]
check('olympics.csv medals == olympics2024.csv for the 89 common countries', len(d) == 0 and len(mm) == 89, len(mm))
print('Paris totals:', pc[['gold', 'silver', 'bronze', 'total']].astype(int).sum().to_dict(), ' olympics.csv:', oc[['gold', 'silver', 'bronze', 'total']].astype(int).sum().to_dict())
check('Paris country noc fully resolved & unique', (pc.noc != '').all() and pc.noc.is_unique)
check('Tokyo: total==g+s+b all rows', (tk.total.astype(int) == tk.gold.astype(int) + tk.silver.astype(int) + tk.bronze.astype(int)).all())
check('Paris roster: athlete_code unique; heights/weights plausible', pa.athlete_code.is_unique and pd.to_numeric(pa.height_cm.replace('', pd.NA)).dropna().between(100, 250).all() and pd.to_numeric(pa.weight_kg.replace('', pd.NA)).dropna().between(30, 250).all())
# ---------- 6. raw untouched
now = subprocess.run("cd /home/claude/work/raw_copy && find . -type f ! -path './__MACOSX/*' -exec sha256sum {} \\; | sort -k2", shell=True, capture_output=True, text=True).stdout
before = open('/home/claude/work/raw_checksums_before.txt').read()
check('Raw files byte-identical to start of session (sha256, 15 files)', now == before)
orig = hashlib.sha256(open('/root/.claude/uploads/2affa031-41e9-53ee-88ff-7b5f0ff8de1d/efd00040-Raw.zip', 'rb').read()).hexdigest()
check('Original uploaded ZIP unchanged', orig == '519d9bee96754a9362ea3354fbcc7ce5b5e732e5c16bd03905e0f65a2693b18f')

# ---------- extra per-dataset profile for summary
prof = []
for nm, df in data.items():
    if 'REMOVED' in nm or nm.startswith('CLEANING_LOG'):
        continue
    d = dict(dataset=nm, rows=len(df), cols=df.shape[1])
    for c in ['year']:
        if c in df: d['year_min'] = int(df[c].min()); d['year_max'] = int(df[c].max())
    for c in ['noc']:
        if c in df: d['noc_unique'] = int(df[c].nunique())
    for c in ['medal', 'season', 'sex']:
        if c in df: d[f'{c}_values'] = '|'.join(sorted(df[c].replace('', '(blank)').unique()))
    for c in ['age', 'height_cm', 'weight_kg']:
        if c in df:
            v = pd.to_numeric(df[c].replace('', pd.NA)); d[f'{c}_min'] = v.min(); d[f'{c}_max'] = v.max()
    prof.append(d)
pd.DataFrame(prof).to_csv(B + 'documentation/VALIDATION_PROFILE.csv', index=False, lineterminator='\n')
pd.DataFrame(RES).to_csv(B + 'documentation/VALIDATION_SUMMARY.csv', index=False, lineterminator='\n')
pd.DataFrame(CHECKS, columns=['check', 'passed', 'detail']).to_csv(B + 'documentation/VALIDATION_CHECKS.csv', index=False, lineterminator='\n')
json.dump(STATS, open('/home/claude/work/stats.json', 'w'), indent=1, default=str)
print(pd.DataFrame(RES).to_string())
print('FAILED CHECKS:', [c for c in CHECKS if not c[1]])
