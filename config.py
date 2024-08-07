import json

def load_config():
    """
    Load configuration settings from a JSON file.

    Returns:
        dict: A dictionary containing configuration settings.
    """
    try:
        with open('config.json', 'r') as file:
            config = json.load(file)
            return config
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading config file: {e}")
        return None

