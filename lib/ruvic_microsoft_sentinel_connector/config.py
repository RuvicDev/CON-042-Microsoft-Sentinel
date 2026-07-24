"""Configuración del conector leída desde variables de entorno.

Convención de la plataforma: cada campo del formulario de configuración
llega como variable de entorno {ENV_PREFIX}{CAMPO} en mayúsculas.
Para este conector el prefijo es RUVIC_MS_SENTINEL_.

Sentinel combina dos APIs de Azure con audiencias (scopes) de token
distintas:
- La API de administración (management.azure.com) para incidentes,
  identificada por subscription_id + resource_group + workspace_name.
- La API de Log Analytics (api.loganalytics.io) para consultas KQL,
  identificada por workspace_id (un GUID, distinto del workspace_name).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

ENV_PREFIX = "RUVIC_MS_SENTINEL_"

_API_VERSION = "2025-01-01-preview"


@dataclass(frozen=True)
class SentinelConfig:
    """Parámetros de conexión a un workspace de Microsoft Sentinel."""

    tenant_id: str
    client_id: str
    client_secret: str
    subscription_id: str
    resource_group: str
    workspace_name: str
    workspace_id: str
    api_version: str = _API_VERSION
    timeout: int = 30

    @classmethod
    def from_env(cls) -> "SentinelConfig":
        """Construye la configuración desde las variables RUVIC_MS_SENTINEL_*.

        Raises:
            ValueError: si falta algún campo obligatorio.
        """
        fields = {
            "tenant_id": "TENANT_ID",
            "client_id": "CLIENT_ID",
            "client_secret": "CLIENT_SECRET",
            "subscription_id": "SUBSCRIPTION_ID",
            "resource_group": "RESOURCE_GROUP",
            "workspace_name": "WORKSPACE_NAME",
            "workspace_id": "WORKSPACE_ID",
        }
        values = {k: os.environ.get(f"{ENV_PREFIX}{v}", "").strip() for k, v in fields.items()}
        missing = [f"{ENV_PREFIX}{fields[k]}" for k, v in values.items() if not v]
        if missing:
            raise ValueError(
                "Faltan variables de entorno del conector microsoft_sentinel: "
                + ", ".join(missing)
                + ". Configura el conector en Settings → Conectores."
            )

        return cls(
            **values,
            api_version=os.environ.get(f"{ENV_PREFIX}API_VERSION", "").strip() or _API_VERSION,
            timeout=int(os.environ.get(f"{ENV_PREFIX}REQUEST_TIMEOUT", "30")),
        )
