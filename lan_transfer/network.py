"""局域网 IPv4 探测（Windows / 通用）。"""

from __future__ import annotations

import socket
from typing import Iterable


def _is_private_ipv4(ip: str) -> bool:
    if ip.startswith("127."):
        return False
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    try:
        o = [int(p) for p in parts]
    except ValueError:
        return False
    if o[0] == 10:
        return True
    if o[0] == 172 and 16 <= o[1] <= 31:
        return True
    if o[0] == 192 and o[1] == 168:
        return True
    # 部分企业使用其它 RFC1918 片段外的局域网，仍可作为候选
    return False


def get_lan_ipv4_candidates() -> list[str]:
    """返回本机 IPv4 列表，私网地址优先。"""
    hostname = socket.gethostname()
    infos: list[str] = []
    try:
        infos.extend(socket.gethostbyname_ex(hostname)[2])
    except OSError:
        pass
    try:
        # getaddrinfo 每项为 (family, type, proto, canonname, sockaddr)，勿把 addr[0] 当成 IP
        for addr in socket.getaddrinfo(hostname, None):
            family, _socktype, _proto, _canon, sockaddr = addr
            if family != socket.AF_INET or not sockaddr:
                continue
            ip = sockaddr[0]
            if isinstance(ip, str):
                infos.append(ip)
    except OSError:
        pass
    uniq: list[str] = []
    for ip in infos:
        if "." not in ip or ip in uniq:
            continue
        uniq.append(ip)

    private = [ip for ip in uniq if _is_private_ipv4(ip)]
    if private:
        return private
    # 没有典型私网地址时退回第一个非 loopback IPv4
    return [ip for ip in uniq if not ip.startswith("127.")]


def pick_primary_lan_ip(candidates: Iterable[str]) -> str | None:
    """优先 192.168.x.x，其次 10.x，其次其它。"""
    c = list(candidates)
    if not c:
        return None
    for ip in c:
        if ip.startswith("192.168."):
            return ip
    for ip in c:
        if ip.startswith("10."):
            return ip
    return c[0]
