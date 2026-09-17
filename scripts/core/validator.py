import yaml
from pathlib import Path
from typing import Any, Dict, List, Tuple
from scripts.core.config import get_schemas_dir

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

def load_yaml(file_path: Path) -> Dict[str, Any]:
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def validate_yaml_file(file_path: Path, schema_name: str) -> Tuple[bool, List[str]]:
    """Valida un file YAML a fronte di uno schema in schemas/<schema_name>."""
    schemas_dir = get_schemas_dir()
    schema_path = schemas_dir / schema_name
    if not schema_path.exists():
        return False, [f"Schema non trovato: {schema_path}"]

    if not file_path.exists():
        return False, [f"File da validare non trovato: {file_path}"]

    try:
        data = load_yaml(file_path)
    except Exception as e:
        return False, [f"Errore di sintassi YAML in {file_path.name}: {e}"]

    try:
        schema = load_yaml(schema_path)
    except Exception as e:
        return False, [f"Errore nel parsing dello schema {schema_path.name}: {e}"]

    errors = []
    if HAS_JSONSCHEMA:
        validator = jsonschema.Draft7Validator(schema)
        for err in validator.iter_errors(data):
            path_str = " -> ".join(str(p) for p in err.absolute_path) or "root"
            errors.append(f"[{path_str}] {err.message}")
    else:
        # Fallback deterministico essenziale sui campi required
        required = schema.get("required", [])
        for field in required:
            if field not in data:
                errors.append(f"Campo obbligatorio mancante: '{field}'")

    return (len(errors) == 0), errors
