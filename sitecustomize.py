import os, pathlib
try:
    import yaml
except Exception:
    yaml = None

def find_env_yaml(start: pathlib.Path, marker="env.yml"):
    for parent in [start] + list(start.parents):
        p = parent / marker
        if p.is_file():
            return p
    return None

if yaml:
    here = pathlib.Path(__file__).resolve()
    env_file = find_env_yaml(here)
    if env_file:
        try:
            data = yaml.safe_load(env_file.read_text(encoding="utf-8")) or {}
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(k, str) and k and (k[0].isalpha() or k[0] == "_") and all(c.isalnum() or c == "_" for c in k):
                        if os.getenv(k) is None and isinstance(v, (str, int, float, bool)):
                            os.environ[k] = str(v)
        except Exception:
            pass
