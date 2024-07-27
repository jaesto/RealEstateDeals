import pandas as pd
import json
import re

def load_zip_codes(filename='all_zip_codes.json'):
    try:
        with open(filename, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Error: The file '{filename}' was not found.")
        return []
    except json.JSONDecodeError:
        print(f"Error: The file '{filename}' could not be decoded.")
        return []

def normalize_phone_number(phone):
    if pd.isna(phone):
        return ''
    digits = re.sub(r'\D', '', str(phone))
    if len(digits) == 10:
        return f"+1{digits}"
    elif len(digits) == 11 and digits.startswith('1'):
        return f"+{digits}"
    return str(phone)

def load_astro_agents(filename):
    try:
        astro_agents = pd.read_csv(filename)
        astro_agents['Phone'] = astro_agents['Phone'].apply(normalize_phone_number)
        astro_agents['First Name'] = astro_agents['First Name'].astype(str)
        astro_agents['Last Name'] = astro_agents['Last Name'].astype(str)
        return astro_agents[['First Name', 'Last Name', 'Phone']]
    except Exception as e:
        print(f"Error loading astro agents from {filename}: {e}")
        return pd.DataFrame()
