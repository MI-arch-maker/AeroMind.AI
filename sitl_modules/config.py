from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class DemoCredentials:
    api_key: str
    jwt_secret: str
    operator_id: str
    allow_mock: bool

    @classmethod
    def from_env(cls) -> "DemoCredentials":
        return cls(
            api_key=os.getenv("AEROMIND_SITL_API_KEY", "sitl-demo-api-key-change-me"),
            jwt_secret=os.getenv("AEROMIND_SITL_JWT_SECRET", "sitl-demo-secret-change-me"),
            operator_id=os.getenv("AEROMIND_SITL_OPERATOR_ID", "demo-operator"),
            allow_mock=os.getenv("AEROMIND_SITL_ALLOW_MOCK", "1").lower() in {"1", "true", "yes"},
        )

    def assert_demo_only(self) -> None:
        if not self.allow_mock:
            raise RuntimeError("les identifiants mock sont désactivés")
        if "change-me" not in self.api_key or "change-me" not in self.jwt_secret:
            raise RuntimeError("Cette configuration est réservée à un environnement SITL de démonstration")
