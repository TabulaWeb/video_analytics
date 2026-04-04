FROM bluenviron/mediamtx:latest AS src
FROM alpine:3.20
RUN apk add --no-cache curl
COPY --from=src /mediamtx /mediamtx
ENTRYPOINT ["/mediamtx"]
