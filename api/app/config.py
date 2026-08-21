from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def repo_root() -> Path:
    here = Path(__file__).resolve()
    for cand in [here.parents[1], here.parents[2], Path.cwd()]:
        if (cand / "knowledge").exists():
            return cand
    return here.parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = "JBFqnCBsd6RMkjVDRZzb"
    elevenlabs_tts_model: str = "eleven_flash_v2_5"

    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-20b"
    groq_max_tokens: int = 48
    generate_deadline_ms: float = 120.0

    hf_token: str = ""

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    index_dir: str = ""

    dense_k: int = 24
    bm25_k: int = 24
    fuse_k: int = 8
    rrf_k: int = 60
    ground_min_dense: float = 0.22
    ground_min_bm25: float = 0.0
    rag_deadline_ms: float = 200.0

    @property
    def root(self) -> Path:
        return repo_root()

    @property
    def index_path(self) -> Path:
        if self.index_dir:
            return Path(self.index_dir)
        return self.root / "data" / "index"

    @property
    def origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
