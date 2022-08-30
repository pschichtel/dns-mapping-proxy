#!/usr/bin/env python3
import json
import os
import socket
import asyncio
import signal
from aiodnsresolver import Resolver, get_nameservers_default, get_logger_adapter_default
from dnsrewriteproxy import DnsProxy


async def nameservers_from_env(_, __):
    host = os.environ['DNS_UPSTREAM']
    port = 53
    if 'DNS_UPSTREAM_PORT' in os.environ:
        port = int(os.environ['DNS_UPSTREAM_PORT'])
    
    for _ in range(5):
        yield 0.5, (host, port)


def get_resolver_from_env():
    return Resolver(get_nameservers=nameservers_from_env)


async def noop_fqdn_transformer(fqdn):
    return bytes(fqdn)


def cache_clearing_as_is_resolver(nameserver_provider):
    resolve, clear_cache = Resolver(
        get_nameservers=nameserver_provider,
        transform_fqdn=noop_fqdn_transformer,
    )

    async def resolve_and_clear(fqdn_str, qtype, get_logger_adapter=get_logger_adapter_default):
        await clear_cache()
        return await resolve(fqdn_str, qtype, get_logger_adapter)

    return resolve_and_clear, clear_cache


def get_socket_default():
    if 'SERVER_ADDRESS' in os.environ:
        server_address = os.environ['SERVER_ADDRESS']
    else:
        server_address = '0.0.0.0'

    if 'SERVER_PORT' in os.environ:
        server_port = int(os.environ['SERVER_PORT'])
    else:
        server_port = 53
    sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    sock.setblocking(False)
    sock.bind((server_address, server_port))
    return sock


def load_rules() -> list[(str, str)]:
    def to_rule(tuple_like: list[str]) -> (str, str):
        return r'^' + tuple_like[0] + r'$', tuple_like[1]

    if 'RULES_FILE' in os.environ:
        with open("a") as f:
            return [to_rule(rule) for rule in json.load(f)]
    if 'RULES' in os.environ:
        return [to_rule(rule) for rule in json.loads(os.environ['RULES'])]
    return []


async def main():
    print("Loading rules...")
    rules = load_rules()

    if len(rules) == 0:
        print("No rules have been defined! Use RULES or RULES_FILE env vars.")
        exit(1)

    for f, t in rules:
        print("Rule: {} -> {}".format(f, t))

    nameserver_provider = get_nameservers_default
    if 'DNS_UPSTREAM' in os.environ:
        nameserver_provider = nameservers_from_env

    print("Setting up resolver...")
    resolver = cache_clearing_as_is_resolver(nameserver_provider)

    print("Starting up proxy")
    start = DnsProxy(
        rules=rules,
        get_socket=get_socket_default,
        get_resolver=lambda: resolver,
    )
    proxy_task = await start()

    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGINT, proxy_task.cancel)
    loop.add_signal_handler(signal.SIGTERM, proxy_task.cancel)

    try:
        await proxy_task
    except asyncio.CancelledError:
        print("Shutting down!")


print("Starting up...")
asyncio.run(main())
