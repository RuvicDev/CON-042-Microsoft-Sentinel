"""Validación local del conector microsoft_sentinel: ejercita las 3 capacidades.

Requiere las env vars RUVIC_MS_SENTINEL_* exportadas contra un workspace
de Sentinel real (no existe una versión local/Docker — es un servicio
de Azure). Usa un workspace de prueba, no uno productivo.
"""

from ruvic_microsoft_sentinel_connector import SentinelClient, setup_logging

setup_logging("INFO")
client = SentinelClient()

print("== 1. Listar incidentes ==")
incidentes = client.list_incidents(max_results=5)
print(f"  {len(incidentes)} incidente(s)")
for i in incidentes:
    print(f"    {i}")

print("== 2. Ejecutar una consulta KQL simple ==")
resultado = client.execute_kql_query("SecurityAlert | take 5", timespan="P7D")
print(f"  columnas: {resultado['columns']}")
print(f"  {len(resultado['rows'])} fila(s)")

if incidentes:
    primer_id = incidentes[0]["id"]
    print(f"== 3. Actualizar el incidente {primer_id} (cambiar severidad, sin cerrar) ==")
    actualizado = client.update_incident(primer_id, severity=incidentes[0]["severity"])  # no-op real, solo confirma que el flujo funciona
    print(f"  {actualizado}")
else:
    print("== 3. Se omite (no hay incidentes para actualizar en este workspace) ==")

print("\nValidación completa.")
