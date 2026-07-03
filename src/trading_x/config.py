from pathlib import Path


def load_tushare_token(env_path: Path = Path(".env"), env_value: str | None = None) -> str | None:
    if env_value is not None and env_value.strip() != "":
        return env_value
    if not env_path.exists():
        return None
    for line in env_path.read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if key.strip() == "TUSHARE_TOKEN" and separator == "=":
            return value.strip().strip('"').strip("'")
    return None

