import json

def load_config(filename='config.json'):
    try:
        with open(filename, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Error: The configuration file '{filename}' was not found.")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode the JSON in the file '{filename}'. Check its syntax.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None
