import pandas as pd
R='/home/claude/work/raw_copy/Raw/'
def rd(f,enc='utf-8-sig'):
    return pd.read_csv(R+f,dtype=str,keep_default_na=False,encoding=enc)
