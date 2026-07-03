from pathlib import Path

from trading_x.config import load_tushare_token


def test_load_tushare_token_reads_env_file_when_environment_missing(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("TUSHARE_TOKEN=local-token\n", encoding="utf-8")

    token = load_tushare_token(env_path, env_value=None)

    assert token == "local-token"

