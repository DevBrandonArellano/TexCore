import pandas as pd

def _fecha_a_texto(val):
    if pd.isna(val) or val is None or val == '':
        return ''
    try:
        ts = pd.Timestamp(val)
        return ts.strftime('%d-%m-%Y')
    except Exception:
        try:
            s = str(val).strip()
            ts = pd.to_datetime(s)
            return ts.strftime('%d-%m-%Y')
        except Exception:
            return ''

print("Result:", _fecha_a_texto("15-03-2026"))
