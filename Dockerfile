FROM alpine:3.23 AS slate
RUN apk add --no-cache ffmpeg font-dejavu
RUN mkdir /slates && \
    for spec in 'salus:Panorámica' 'salus-ptz:Cámara PTZ' 'salus-trasera:Cámara trasera'; do \
      name="${spec%%:*}"; label="${spec#*:}"; \
      ffmpeg -nostdin -v error -f lavfi -i color=c=0x101c29:s=640x360:r=15 \
        -vf "drawtext=fontfile=/usr/share/fonts/dejavu/DejaVuSans.ttf:text='Rover detenido':fontsize=36:fontcolor=white:x=(w-tw)/2:y=133,drawtext=fontfile=/usr/share/fonts/dejavu/DejaVuSans.ttf:text='$label':fontsize=20:fontcolor=0x97b0c8:x=(w-tw)/2:y=195" \
        -t 2 -c:v libx264 -profile:v main -bf 0 -pix_fmt yuv420p -g 30 -movflags +faststart "/slates/$name.mp4" || exit 1; \
    done

FROM bluenviron/mediamtx:1.21.4 AS media
COPY --from=slate /slates /slates

FROM python:3.13-alpine3.23 AS control
RUN apk add --no-cache ffmpeg
COPY controller.py /app/controller.py
USER 65534:65534
CMD ["python", "/app/controller.py"]
