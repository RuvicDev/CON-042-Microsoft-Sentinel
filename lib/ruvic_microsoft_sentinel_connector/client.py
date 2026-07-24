"""Cliente para gestionar incidentes y ejecutar consultas KQL en Microsoft Sentinel.

Capacidades:
- list_incidents():        listar incidentes, con filtros opcionales.
- update_incident():       actualizar estado/severidad/propietario de un incidente.
- execute_kql_query():     ejecutar una consulta KQL contra el workspace de Log Analytics.

Autenticación: Azure AD App Registration (Client Credentials OAuth2).
Sentinel combina dos APIs de Azure con audiencias de token distintas —
este cliente las maneja de forma transparente, cacheando un token por
cada audiencia. Las credenciales SIEMPRE provienen de variables de
entorno RUVIC_MS_SENTINEL_* (ver config.SentinelConfig.from_env).
Prohibido hardcodearlas.
"""

from __future__ import annotations

import time
from typing import Any

import requests
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import RequestException, Timeout

from .config import SentinelConfig
from .exceptions import SentinelAuthError, SentinelDataError, SentinelNetworkError
from .logging_utils import get_logger

_TOKEN_URL_TEMPLATE = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
_MANAGEMENT_SCOPE = "https://management.azure.com"
_LOG_ANALYTICS_SCOPE = "https://api.loganalytics.io"


class SentinelClient:
    """Cliente de Microsoft Sentinel autenticado vía Azure AD.

    Args:
        config: configuración de conexión. Si se omite, se lee de las
            variables de entorno RUVIC_MS_SENTINEL_* (comportamiento
            estándar en el runtime de la plataforma).

    Ejemplo:
        >>> client = SentinelClient()  # lee RUVIC_MS_SENTINEL_* del entorno
        >>> client.list_incidents(status="Active")
        [{'id': '...', 'title': '...', 'severity': 'High', ...}, ...]
    """

    def __init__(self, config: SentinelConfig | None = None) -> None:
        self.config = config or SentinelConfig.from_env()
        self._logger = get_logger()
        self._tokens: dict[str, tuple[str, float]] = {}  # scope -> (token, expires_at)

    # ------------------------------------------------------------------ #
    # Autenticación (Azure AD, un token por audiencia/scope)
    # ------------------------------------------------------------------ #

    def _get_token(self, scope: str) -> str:
        cached = self._tokens.get(scope)
        if cached and time.time() < cached[1] - 60:
            return cached[0]

        url = _TOKEN_URL_TEMPLATE.format(tenant_id=self.config.tenant_id)
        try:
            resp = requests.post(
                url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                    "scope": f"{scope}/.default",
                },
                timeout=self.config.timeout,
            )
        except Timeout as exc:
            raise SentinelNetworkError("Tiempo de espera agotado autenticando con Azure AD.") from exc
        except RequestsConnectionError as exc:
            raise SentinelNetworkError(f"No se pudo conectar a Azure AD: {exc}") from exc
        except RequestException as exc:
            raise SentinelNetworkError(f"Error de red autenticando con Azure AD: {exc}") from exc

        if resp.status_code != 200:
            raise SentinelAuthError(
                f"Azure AD rechazó la autenticación (HTTP {resp.status_code}): {resp.text[:300]}. "
                "Revisa tenant_id, client_id y client_secret."
            )

        payload = resp.json()
        token = payload["access_token"]
        expires_in = int(payload.get("expires_in", 3600))
        self._tokens[scope] = (token, time.time() + expires_in)
        return token

    # ------------------------------------------------------------------ #
    # Peticiones HTTP
    # ------------------------------------------------------------------ #

    def _request(self, method: str, url: str, scope: str, **extra: Any) -> requests.Response:
        token = self._get_token(scope)
        headers = extra.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        try:
            return requests.request(method, url, headers=headers, timeout=self.config.timeout, **extra)
        except Timeout as exc:
            raise SentinelNetworkError(f"Tiempo de espera agotado llamando a {url}.") from exc
        except RequestsConnectionError as exc:
            raise SentinelNetworkError(f"No se pudo conectar a {url}: {exc}") from exc
        except RequestException as exc:
            raise SentinelNetworkError(f"Error de red: {exc}") from exc

    def _raise_for_error(self, resp: requests.Response, context: str) -> None:
        try:
            payload = resp.json()
            message = payload.get("error", {}).get("message", resp.text[:300])
        except ValueError:
            message = resp.text[:300] or "Error desconocido"

        if resp.status_code in (401, 403):
            raise SentinelAuthError(
                f"Permisos insuficientes en {context} (HTTP {resp.status_code}): {message}. "
                "La aplicación necesita el rol 'Microsoft Sentinel Responder' (o superior) "
                "sobre el workspace."
            )
        if resp.status_code == 404:
            raise SentinelDataError(f"No encontrado en {context}: {message}")
        if resp.status_code == 400:
            raise SentinelDataError(f"Solicitud inválida en {context}: {message}")
        raise SentinelDataError(f"Error de Azure en {context} (HTTP {resp.status_code}): {message}")

    def _management_base_url(self) -> str:
        c = self.config
        return (
            f"https://management.azure.com/subscriptions/{c.subscription_id}"
            f"/resourceGroups/{c.resource_group}"
            f"/providers/Microsoft.OperationalInsights/workspaces/{c.workspace_name}"
            f"/providers/Microsoft.SecurityInsights"
        )

    # ------------------------------------------------------------------ #
    # Ping / prueba de conexión
    # ------------------------------------------------------------------ #

    def ping(self) -> bool:
        """Verifica las credenciales listando incidentes (1 resultado, barato)."""
        self.list_incidents(max_results=1)
        self._logger.info("Ping exitoso a Microsoft Sentinel (workspace: %s)", self.config.workspace_name)
        return True

    # ------------------------------------------------------------------ #
    # Capacidad 1: listar incidentes
    # ------------------------------------------------------------------ #

    def list_incidents(
        self, status: str | None = None, severity: str | None = None, max_results: int = 50
    ) -> list[dict[str, Any]]:
        """Lista incidentes del workspace, con filtros opcionales.

        Args:
            status: filtra por estado ("New", "Active", "Closed").
            severity: filtra por severidad ("Informational", "Low", "Medium", "High").
            max_results: máximo de resultados (default 50).

        Returns:
            Lista de dicts con "id" (GUID del incidente), "title",
            "severity", "status", "created_time", "owner".

        Ejemplo:
            >>> client.list_incidents(status="Active", severity="High")
            [{'id': '...', 'title': 'Suspicious sign-in', ...}, ...]
        """
        url = f"{self._management_base_url()}/incidents"
        params: dict[str, Any] = {"api-version": self.config.api_version, "$top": max_results}
        filters = []
        if status:
            filters.append(f"properties/status eq '{status}'")
        if severity:
            filters.append(f"properties/severity eq '{severity}'")
        if filters:
            params["$filter"] = " and ".join(filters)

        resp = self._request("GET", url, _MANAGEMENT_SCOPE, params=params)
        if resp.status_code != 200:
            self._raise_for_error(resp, "list_incidents")

        items = resp.json().get("value", [])
        incidents = [self._incident_to_dict(item) for item in items]
        self._logger.info("list_incidents: %d incidente(s)", len(incidents))
        return incidents

    @staticmethod
    def _incident_to_dict(item: dict[str, Any]) -> dict[str, Any]:
        props = item.get("properties", {})
        return {
            "id": item.get("name"),
            "title": props.get("title"),
            "severity": props.get("severity"),
            "status": props.get("status"),
            "created_time": props.get("createdTimeUtc"),
            "owner": (props.get("owner") or {}).get("email"),
        }

    # ------------------------------------------------------------------ #
    # Capacidad 2: actualizar un incidente
    # ------------------------------------------------------------------ #

    def update_incident(
        self,
        incident_id: str,
        status: str | None = None,
        severity: str | None = None,
        owner_email: str | None = None,
    ) -> dict[str, Any]:
        """Actualiza el estado, severidad y/o propietario de un incidente.

        Args:
            incident_id: GUID del incidente (obtenido de `list_incidents`).
            status: nuevo estado ("New", "Active", "Closed"). Opcional.
            severity: nueva severidad. Opcional.
            owner_email: email a asignar como propietario. Opcional.

        Returns:
            Dict con el incidente actualizado (mismo formato que `list_incidents`).

        Ejemplo:
            >>> client.update_incident("abc-123", status="Closed")
            {'id': 'abc-123', 'status': 'Closed', ...}
        """
        if not incident_id or not incident_id.strip():
            raise SentinelDataError("incident_id no puede estar vacío.")
        if not any([status, severity, owner_email]):
            raise SentinelDataError("Debes indicar al menos un campo a actualizar (status/severity/owner_email).")

        url = f"{self._management_base_url()}/incidents/{incident_id.strip()}"

        # Azure requiere PUT con el recurso completo — se lee primero y se fusiona.
        get_resp = self._request("GET", url, _MANAGEMENT_SCOPE, params={"api-version": self.config.api_version})
        if get_resp.status_code != 200:
            self._raise_for_error(get_resp, f"update_incident (leer) {incident_id}")

        body = get_resp.json()
        if status:
            body["properties"]["status"] = status
        if severity:
            body["properties"]["severity"] = severity
        if owner_email:
            body["properties"]["owner"] = {"email": owner_email}

        put_resp = self._request(
            "PUT", url, _MANAGEMENT_SCOPE,
            params={"api-version": self.config.api_version}, json=body,
        )
        if put_resp.status_code not in (200, 201):
            self._raise_for_error(put_resp, f"update_incident (escribir) {incident_id}")

        self._logger.info("Incidente %s actualizado", incident_id)
        return self._incident_to_dict(put_resp.json())

    # ------------------------------------------------------------------ #
    # Capacidad 3: ejecutar una consulta KQL
    # ------------------------------------------------------------------ #

    def execute_kql_query(self, query: str, timespan: str = "P1D") -> dict[str, Any]:
        """Ejecuta una consulta KQL contra el workspace de Log Analytics.

        Args:
            query: consulta en Kusto Query Language.
            timespan: rango de tiempo en formato ISO 8601 (ej. "P1D" =
                último día, "PT4H" = últimas 4 horas). Default "P1D".

        Returns:
            Dict con "columns" (nombres de columna) y "rows" (lista de dicts).

        Ejemplo:
            >>> client.execute_kql_query("SecurityAlert | take 10")
            {'columns': ['TimeGenerated', 'AlertName', ...], 'rows': [...]}
        """
        if not query or not query.strip():
            raise SentinelDataError("La consulta KQL no puede estar vacía.")

        url = f"https://api.loganalytics.io/v1/workspaces/{self.config.workspace_id}/query"
        resp = self._request(
            "POST", url, _LOG_ANALYTICS_SCOPE,
            json={"query": query, "timespan": timespan},
        )
        if resp.status_code != 200:
            self._raise_for_error(resp, "execute_kql_query")

        payload = resp.json()
        table = (payload.get("tables") or [{}])[0]
        columns = [c["name"] for c in table.get("columns", [])]
        rows = [dict(zip(columns, row)) for row in table.get("rows", [])]

        self._logger.info("execute_kql_query: %d fila(s)", len(rows))
        return {"columns": columns, "rows": rows}
