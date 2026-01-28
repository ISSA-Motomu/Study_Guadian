import json
import os

TEMPLATE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "templates", "bot"
)


def load_template(filename, **kwargs):
    """
    Loads a JSON template file and substitutes variables.
    Variables in the JSON should be in the format ${variable_name}.
    """
    path = os.path.join(TEMPLATE_DIR, filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return _recursive_replace(data, kwargs)
    except FileNotFoundError:
        print(f"Template file not found: {filename}")
        return None
    except Exception as e:
        print(f"Error loading template {filename}: {e}")
        return None


def _recursive_replace(data, replacements):
    if isinstance(data, dict):
        return {k: _recursive_replace(v, replacements) for k, v in data.items()}
    elif isinstance(data, list):
        return [_recursive_replace(i, replacements) for i in data]
    elif isinstance(data, str):
        # Simple replacement of ${key} markers
        # We iterate over replacements to ensure we catch all provided keys
        result = data
        for k, v in replacements.items():
            placeholder = f"${{{k}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(v))
        return result
    else:
        return data
