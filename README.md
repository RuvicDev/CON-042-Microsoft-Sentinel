# conector-microsoft-sentinel

Conector Ruvic para Microsoft Sentinel: listar incidentes, actualizar un incidente, y ejecutar consultas KQL.

## Capacidades

`list_incidents`, `update_incident`, `execute_kql_query`. No crea ni elimina incidentes ni reglas de detección.

## Instalación

Requiere **Python ≥ 3.10**.

```bash
pip install git+https://github.com/tu-org/conector-microsoft-sentinel.git#subdirectory=lib
```

Para desarrollo local (editable, en un venv limpio):

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ./lib
```

## Variables de entorno

| Variable | Obligatoria | Descripción |
|----------|-------------|-------------|
| `RUVIC_MS_SENTINEL_TENANT_ID` / `..._CLIENT_ID` / `..._CLIENT_SECRET` | Sí | Credenciales de la App Registration de Azure AD |
| `RUVIC_MS_SENTINEL_SUBSCRIPTION_ID` / `..._RESOURCE_GROUP` / `..._WORKSPACE_NAME` | Sí | Ubicación del workspace (API de gestión) |
| `RUVIC_MS_SENTINEL_WORKSPACE_ID` | Sí | GUID del workspace, para la API de Log Analytics (distinto del nombre) |
| `RUVIC_MS_SENTINEL_API_VERSION` | No | Default `2025-01-01-preview` |
| `RUVIC_MS_SENTINEL_REQUEST_TIMEOUT` | No | Segundos, default `30` |

## Permisos / prerrequisitos en Azure

1. Registra una app en **Azure Portal → Microsoft Entra ID → App registrations → New registration**.
2. Genera un **Client Secret** (Certificates & secrets) — cópialo de inmediato.
3. En el workspace de Sentinel, ve a **Access control (IAM)** y otorga a la app:
   - **Microsoft Sentinel Responder** (lectura + actualización de incidentes).
   - **Log Analytics Reader** (para ejecutar consultas KQL).
4. No otorgues **Microsoft Sentinel Contributor** completo ni roles de administrador de la suscripción salvo necesidad real.
5. Anota: Tenant ID, Client ID (Application ID), Client Secret, Subscription ID, Resource Group, nombre del workspace, y el **Workspace ID (GUID)** — este último se ve en la vista de resumen del workspace en Azure Portal, es distinto del nombre.

## Cómo correr las pruebas locales

Microsoft Sentinel no tiene una versión local/Docker (es un servicio de Azure) — hace falta un workspace real, idealmente uno de prueba separado del productivo.

```bash
export RUVIC_MS_SENTINEL_TENANT_ID=xxxx
export RUVIC_MS_SENTINEL_CLIENT_ID=xxxx
export RUVIC_MS_SENTINEL_CLIENT_SECRET=xxxx
export RUVIC_MS_SENTINEL_SUBSCRIPTION_ID=xxxx
export RUVIC_MS_SENTINEL_RESOURCE_GROUP=xxxx
export RUVIC_MS_SENTINEL_WORKSPACE_NAME=xxxx
export RUVIC_MS_SENTINEL_WORKSPACE_ID=xxxx

python test_connection.py
python validate_local.py
```

## Limitaciones conocidas

- No crea ni elimina incidentes, ni gestiona reglas de detección/analytics rules.
- No implementa comentarios ni tareas dentro de un incidente — solo estado/severidad/propietario.
- `update_incident` requiere leer el incidente completo antes de escribir (limitación de la API de Azure, que exige el recurso completo en el PUT) — dos llamadas por actualización, no una.

## Notas de integración

- El paquete pip es `ruvic-microsoft-sentinel-connector`; el import name es `ruvic_microsoft_sentinel_connector`.
- Única dependencia externa: `requests`.
- Ver `SKILL.md` para los ejemplos de uso que consume el agente.
