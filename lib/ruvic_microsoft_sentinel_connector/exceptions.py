"""Excepciones propias del conector Microsoft Sentinel.

Separan los tipos de fallo que el usuario debe distinguir: configuración
inválida, autenticación (Azure AD), red, y datos (incidente inexistente,
KQL inválido).
"""


class SentinelConnectorError(Exception):
    """Error base del conector."""


class SentinelConfigError(SentinelConnectorError):
    """Configuración inválida: falta un campo requerido."""


class SentinelAuthError(SentinelConnectorError):
    """Azure AD rechazó la autenticación (tenant/client_id/client_secret
    inválidos), o la aplicación no tiene el rol de IAM necesario."""


class SentinelNetworkError(SentinelConnectorError):
    """No se pudo alcanzar Azure (DNS, timeout, red)."""


class SentinelDataError(SentinelConnectorError):
    """La operación es válida pero el incidente no existe, el KQL es
    inválido, o Azure rechazó la operación por otra razón."""
