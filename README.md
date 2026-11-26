# SALUS Video Relay

MediaMTX recibe por Tailscale el RTSP de la cámara panorámica del rover (`cam3`)
y lo sirve al Hikvision por RTSP/TCP en `/salus`. Abre la fuente cuando llega
un lector autorizado. El relay reenvía el video sin recodificar ni grabar.

## Prueba privada

1. Instalá Docker con Compose v2 y conectá el servidor a la misma red Tailscale
   que el rover. El contenedor debe poder llegar a la IP y el puerto RTSP del rover.
2. Copiá `.env.example` a `.env` (en PowerShell, `Copy-Item .env.example .env`).
   Definí `ROVER_RTSP_URL` con el valor `rtsp://IP_PRIVADA_DEL_ROVER:8554/cam3`
   y generá una contraseña única para `NVR_PASSWORD`, por ejemplo con
   `openssl rand -hex 24`. Guardá el archivo con acceso restringido.
3. Validá y levantá el servicio.

   ```sh
   docker compose config --quiet
   docker compose up -d
   docker compose logs --tail=50 mediamtx
   ```

4. Probá desde el propio servidor con VLC o FFmpeg usando
   `rtsp://nvr_salus:CONTRASEÑA@127.0.0.1:18554/salus` sobre TCP.
   Confirmá también que una conexión sin credenciales sea rechazada.

Si Windows llega al rover y el contenedor informa un timeout, verificá el
enrutamiento de Docker Desktop hacia Tailscale antes de cambiar el firewall
o la configuración de MediaMTX.

## Prueba con el Hikvision

Cuando esté validada la prueba privada, configurá `RTSP_BIND_IP` con la
dirección del servidor que deba recibir al NVR y recreá el contenedor con
`docker compose up -d`. Si cruza Internet, limitá el acceso al puerto TCP
a la IP pública del centro en el firewall perimetral antes de habilitar
el reenvío. RTSP convencional no cifra el tramo hasta el NVR.

| Parámetro | Valor |
| --- | --- |
| Protocolo personalizado | RTSP |
| Transporte | RTP sobre RTSP (TCP) |
| Dirección y puerto | Dirección alcanzable del relay y puerto configurado (18554 por defecto) |
| Ruta | `/salus` |
| Usuario | `nvr_salus` |
| Contraseña | Valor de `NVR_PASSWORD` |

Comprobá que el NVR graba, reproduce lo grabado y recupera la señal tras un
corte de conectividad del rover.

## Migración

Cloná este repositorio en el destino, trasladá `.env` por un canal seguro y
probá el acceso privado al rover y la salida local. Luego ajustá la dirección
de escucha y el acceso desde el NVR. El relay no tiene volúmenes de datos
que migrar.
