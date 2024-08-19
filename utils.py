import re
import os, sys
import pandas as pd
import traceback

def normalize_phone_number(phone):
    if pd.isna(phone):
        return ''
    digits = re.sub(r'\D', '', str(phone))
    if len(digits) == 10:
        return f"+1{digits}"
    elif len(digits) == 11 and digits.startswith('1'):
        return f"+{digits}"
    return str(phone)

def get_traceback():
    try:
        tb = sys.exc_info()[2]
        pymsg = traceback.format_tb(tb)[0]
        if sys.exc_type:
            pymsg = pymsg + "\n" + str(sys.exc_type) + ": " + str(sys.exc_value)
        return pymsg
    except Exception as e:
        return f'Problem getting traceback object: {e}'
