FROM coredns/coredns:1.12.0 AS coredns

FROM alpine:3.21

RUN apk add --update --no-cache yq ca-certificates curl

COPY --from=coredns /coredns /coredns

ENTRYPOINT ["/entrypoint.sh"]

HEALTHCHECK CMD [ "curl" -sSf "http://127.0.0.1:8080/health" ]

EXPOSE 53/UDP

COPY entrypoint.sh /entrypoint.sh
