# SALUS Video Relay

MediaMTX ofrece las tres cámaras del rover al Hikvision por RTSP/TCP. El
control privado activa la recepción del rover por Tailscale. En pausa, MediaMTX
emite un cartel local de «Rover detenido» en las mismas rutas. El relay entrega
solo video H.264 y no recodifica las cámaras ni graba.

| Cámara | Fuente | Ruta |
| --- | --- | --- |
| Panorámica | cam3 | /salus |
| PTZ | cam4 | /salus-ptz |
| Trasera | cam5 | /salus-trasera |

## Prueba privada

1. Instalá Docker con Compose v2 y conectá el servidor a la misma red
   Tailscale que el rover. Docker debe poder alcanzar su puerto RTSP.
2. Copiá `.env.example` a `.env`. Definí las tres URLs privadas correspondientes
   a las fuentes de la tabla, la contraseña del NVR y dos secretos únicos para
   el control y la publicación. Podés generar cada secreto con
   `openssl rand -hex 32`. Restringí el acceso al archivo.
3. Ejecutá `docker compose config --quiet` y `docker compose up -d --build`.
   El relay arranca en pausa, incluso después de un reinicio del controlador.
4. Probá desde el servidor con VLC o FFmpeg usando
   `rtsp://nvr_salus:CONTRASEÑA@127.0.0.1:18554/salus` sobre TCP.
   Debe verse el cartel y una conexión sin credenciales debe ser rechazada.

## Control desde Cockpit

El controlador no publica un puerto del host. Primero iniciá este Compose
para crear la red privada `salus-nvr-control`. En el despliegue de Cockpit,
agregá `compose.nvr.yaml` después del Compose de identidad y configurá en
el servicio de autenticación:

- `COCKPIT_NVR_CONTROL_URL=http://nvr-control:8090/transmission`
- `COCKPIT_NVR_CONTROL_TOKEN` con el mismo valor que `NVR_CONTROL_TOKEN`.

Los usuarios con sesión iniciada, incluidos los operadores, pueden activar o
pausar el video en **Cámara → Transmisión al NVR**. Al activar se abren las
tres fuentes. Al pausar se cierran todas antes de confirmar el cambio. Los
clientes RTSP siguen recibiendo el cartel local, y la vista normal de cámaras
de Cockpit conserva su conexión independiente.

Si ya hay una instalación en Server-CIT, respaldá su Compose, configuración y
`.env`, conservá las contraseñas, el puerto y la IP de escucha, y reaplicá
las cuentas adicionales de lectura al nuevo `mediamtx.yml` sin alterar el
orden de sus dos primeras cuentas. Revisá el montaje y el firewall antes
de reemplazar el contenedor en producción.

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

Comprobá que el NVR conserva el canal al alternar cartel, video en vivo y
cartel, y que graba y reproduce lo grabado. Comprobá también qué registra
durante la pausa según su programación de grabación.

## Migración

Cloná este repositorio en el destino, trasladá `.env` por un canal seguro y
probá el acceso privado al rover y la salida local. Luego ajustá la dirección
de escucha y el acceso desde el NVR. El relay no tiene volúmenes de datos
que migrar.
