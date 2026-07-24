"""Prueba de conexión estándar del conector microsoft_sentinel.

Firma estándar Ruvic: def test_connection() -> tuple[bool, str]
- Lee la configuración EXCLUSIVAMENTE de las env vars RUVIC_MS_SENTINEL_*.
- Nunca lanza excepciones; retorna (ok, mensaje).

Ejecutable también como script para pruebas locales:
    python test_connection.py
"""

from __future__ import annotations


def test_connection() -> tuple[bool, str]:
    """Verifica las credenciales listando 1 incidente."""
    try:
        from ruvic_microsoft_sentinel_connector import (
            SentinelAuthError,
            SentinelClient,
            SentinelDataError,
            SentinelNetworkError,
        )
    except ImportError:
        return (
            False,
            "La librería ruvic-microsoft-sentinel-connector no está instalada. "
            "Instala con: pip install git+https://github.com/tu-org/"
            "conector-microsoft-sentinel.git#subdirectory=lib",
        )

    try:
        client = SentinelClient()  # valida config
    except ValueError as exc:
        return False, str(exc)

    try:
        client.ping()
    except SentinelAuthError as exc:
        return False, f"Autenticación fallida: {exc}"
    except SentinelNetworkError as exc:
        return False, f"Error de red: {exc}"
    except SentinelDataError as exc:
        return False, f"Error de datos: {exc}"
    except Exception as exc:  # red de seguridad: jamás propagar
        return False, f"Error inesperado: {exc}"

    return True, f"Conexión exitosa al workspace {client.config.workspace_name}"


if __name__ == "__main__":
    ok, message = test_connection()
    print(f"{'OK' if ok else 'FALLO'}: {message}")
    raise SystemExit(0 if ok else 1)
