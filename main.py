#!/usr/bin/env python3
import os
import socket
import asyncio
import signal
from aiodnsresolver import Resolver
from dnsrewriteproxy import DnsProxy, get_resolver_default

async def nameservers_from_env(_, __):
    host = os.environ['DNS_UPSTREAM']
    port = 53
    if 'DNS_UPSTREAM_PORT' in os.environ:
        port = int(os.environ['DNS_UPSTREAM_PORT'])
    
    print("Providing {}:{} as namespace!".format(host, port))
    for _ in range(5):
        yield (0.5, (host, port))

def get_resolver_from_env():
    return Resolver(get_nameservers=nameservers_from_env)

if 'SERVER_ADDRESS' in os.environ:
    server_address = os.environ['SERVER_ADDRESS']
else:
    server_address = '0.0.0.0'

if 'SERVER_PORT' in os.environ:
    server_port = int(os.environ['SERVER_PORT'])
else:
    server_port = 53

if 'DNS_SOURCE_SUFFIX' not in os.environ:
    print("DNS_SOURCE_SUFFIX missing!")
    exit(1)

if 'DNS_TARGET_SUFFIX' not in os.environ:
    print("DNS_TARGET_SUFFIX missing!")
    exit(1)

rules = [
    (r'^(.*)' + os.environ['DNS_SOURCE_SUFFIX'] + '$', r'\1' + os.environ['DNS_TARGET_SUFFIX']),
    (r'(^.*$)', r'\1'),
]


def get_socket_default():
    sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    sock.setblocking(False)
    sock.bind((server_address, server_port))
    return sock


async def main():
    resolver_factory = get_resolver_default
    if 'DNS_UPSTREAM' in os.environ:
        resolver_factory = get_resolver_from_env

    start = DnsProxy(
        rules=rules,
        get_socket=get_socket_default,
        get_resolver=resolver_factory,
    )
    proxy_task = await start()

    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGINT, proxy_task.cancel)
    loop.add_signal_handler(signal.SIGTERM, proxy_task.cancel)

    try:
        await proxy_task
    except asyncio.CancelledError:
        print("Shutting down!")


asyncio.run(main())
