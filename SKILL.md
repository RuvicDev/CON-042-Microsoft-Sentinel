---
name: microsoft-sentinel
description: "Usa la librería ruvic_microsoft_sentinel_connector para gestionar incidentes en Microsoft Sentinel - listar incidentes con filtros (list_incidents), actualizar estado/severidad/propietario de un incidente (update_incident), y ejecutar una consulta KQL contra el workspace (execute_kql_query). Úsala cuando el usuario pida revisar incidentes de Sentinel, cambiar su estado, o consultar eventos/logs con KQL. No crea ni elimina incidentes ni reglas de detección."
triggers:
- sentinel
- azure sentinel
- kql
- incidente sentinel
- log analytics
---

# Conector Microsoft Sentinel (ruvic_microsoft_sentinel_connector)

Librería Python para gestionar incidentes y ejecutar consultas KQL en Microsoft Sentinel, autenticada vía Azure AD (App Registration). Está **preinstalada en el runtime** cuando el conector está configurado (si no, instálala con `pip install git+https://github.com/tu-org/conector-microsoft-sentinel.git#subdirectory=lib`).

## Regla crítica de credenciales

El código generado **NUNCA hardcodea credenciales**. Siempre se leen de variables de entorno, disponibles cuando el conector `microsoft_sentinel` está configurado:

| Variable | Contenido |
|----------|-----------|
| `RUVIC_MS_SENTINEL_TENANT_ID` / `..._CLIENT_ID` / `..._CLIENT_SECRET` | Credenciales de Azure AD |
| `RUVIC_MS_SENTINEL_SUBSCRIPTION_ID` / `..._RESOURCE_GROUP` / `..._WORKSPACE_NAME` | Ubicación del workspace (API de gestión) |
| `RUVIC_MS_SENTINEL_WORKSPACE_ID` | GUID del workspace (API de Log Analytics — distinto del nombre) |
| `RUVIC_MS_SENTINEL_REQUEST_TIMEOUT` | (opcional) segundos, default `30` |

Si estas variables NO existen, el conector no está configurado: no generes código que lo use; indica al usuario que lo configure en **Settings → Conectores**.

El código generado **NUNCA** usa nombres de variable con segmento de alias (`_DEFAULT_`, `_TEST_`, `_PRODUCCION_`, etc.) — siempre `{ENV_PREFIX}{CAMPO}` tal cual, sin importar cuántas instancias de este conector haya configuradas. Esto aplica salvo que dichos nombres aparezcan explícitamente en una sección autogenerada al final de este skill.

## Conexión (siempre igual)

```python
from ruvic_microsoft_sentinel_connector import SentinelClient

client = SentinelClient()  # lee RUVIC_MS_SENTINEL_* del entorno automáticamente
```

El cliente gestiona automáticamente **dos tokens de Azure AD distintos** (uno para gestión de incidentes, otro para consultas KQL) — no necesitas manejarlo tú.

## Capacidad 1 — Listar incidentes

```python
incidentes = client.list_incidents(status="Active", severity="High")
for i in incidentes:
    print(f"{i['id']}: {i['title']} ({i['severity']})")
```

## Capacidad 2 — Actualizar un incidente

```python
client.update_incident("abc-123-guid", status="Closed")
client.update_incident("abc-123-guid", severity="Medium", owner_email="analista@empresa.com")
```

Antes de cerrar un incidente, confirma la intención del usuario — es una acción con impacto real en el seguimiento de seguridad.

## Capacidad 3 — Ejecutar una consulta KQL

```python
resultado = client.execute_kql_query("SecurityAlert | take 10", timespan="P7D")
for fila in resultado["rows"]:
    print(fila)
```

`timespan` usa formato ISO 8601 de duración (`P1D` = 1 día, `PT4H` = 4 horas, `P7D` = 7 días) — siempre inclúyelo, evita consultas sin límite de tiempo.

## Manejo de errores

```python
from ruvic_microsoft_sentinel_connector import SentinelAuthError, SentinelNetworkError, SentinelDataError

try:
    client.list_incidents()
except SentinelAuthError:
    print("Credenciales inválidas o permisos insuficientes — revisa la configuración del conector")
except SentinelNetworkError:
    print("No se pudo conectar a Azure — revisa la red")
except SentinelDataError as e:
    print(f"Error de datos: {e}")  # ej. incidente no encontrado, KQL inválido
```

## Buenas prácticas al generar código

1. Lee credenciales SOLO de las variables `RUVIC_MS_SENTINEL_*` (el constructor de `SentinelClient` ya lo hace).
2. Nunca imprimas `RUVIC_MS_SENTINEL_CLIENT_SECRET` en logs ni en la salida.
3. Antes de cerrar/modificar un incidente, confirma la intención del usuario.
4. Siempre incluye un `timespan` acotado en las consultas KQL — evita escanear todo el histórico sin necesidad.
5. No intentes crear ni eliminar incidentes, ni gestionar reglas de detección: este conector no lo soporta.
