from dotenv import load_dotenv
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    postgres_db: str = Field(..., env='POSTGRES_DB')
    postgres_user: str = Field(..., env='POSTGRES_USER')
    postgres_password: str = Field(..., env='POSTGRES_PASSWORD')
    host: str = Field(..., env='HOST')
    port: int = Field(..., env='PORT')

    api_id: int = Field(..., env='API_ID')
    api_hash: str = Field(..., env='API_HASH')
    channel_id: int = Field(..., env='CHANNEL_ID')

    api_key: str = Field(..., env='API_KEY')
    api_secret: str = Field(..., env='API_SECRET')

    is_test: bool = Field(..., env='IS_TEST')

    trading_pairs: str = Field(..., env='TRADING_PAIRS')

    @computed_field
    @property
    def websocket_url(self) -> str:
        if self.is_test:
            return 'wss://stream-testnet.bybit.com'
        else:
            return 'wss://stream.bybit.com'

    @computed_field
    def api_url(self) -> str:
        if self.is_test:
            return 'https://api-testnet.bybit.com'
        else:
            return 'https://api.bybit.com'


settings = Settings()
