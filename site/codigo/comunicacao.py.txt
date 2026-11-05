"""Transporte UDP/JSON compartilhado pelo cliente e pelos servidores."""

import json
import socket
import struct


Endereco = tuple[str, int]


class CanalUDP:
    """Encapsula um socket UDP e a codificacao JSON das mensagens."""

    def __init__(self, sock):
        self._sock = sock
        self.endereco = sock.getsockname()

    def enviar(self, mensagem: dict, destino: Endereco) -> None:
        dados = json.dumps(mensagem).encode("utf-8")
        self._sock.sendto(dados, destino)

    def receber(self, timeout: float | None = None) -> tuple[dict, Endereco]:
        self._sock.settimeout(timeout)
        dados, origem = self._sock.recvfrom(65535)
        return json.loads(dados.decode("utf-8")), origem

    def fechar(self) -> None:
        self._sock.close()


def _configura_envio_multicast(sock, iface: str) -> None:
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(iface))
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)


def abrir_canal_cliente(iface: str) -> CanalUDP:
    """Abre um canal com porta efemera para enviar ao grupo e receber resposta."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((iface, 0))
    _configura_envio_multicast(sock, iface)
    return CanalUDP(sock)


def abrir_canal_unicast(ip: str, porta: int, iface: str) -> CanalUDP:
    """Abre o canal unicast de um servidor, tambem usado para enviar ao grupo."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((ip, porta))
    _configura_envio_multicast(sock, iface)
    return CanalUDP(sock)


def abrir_canal_multicast(grupo: str, porta: int, iface: str) -> CanalUDP:
    """Abre um canal receptor e entra no grupo multicast na interface indicada."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if hasattr(socket, "SO_REUSEPORT"):
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except OSError:
            pass
    sock.bind(("", porta))
    mreq = struct.pack("4s4s", socket.inet_aton(grupo), socket.inet_aton(iface))
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    return CanalUDP(sock)
