"""Dublês usados somente pelos testes automatizados."""

from collections import deque
from copy import deepcopy
import socket


class CanalFake:
    """Canal em memória com a mesma interface usada pelo transporte UDP."""

    def __init__(self, endereco=("127.0.0.1", 0)):
        self.endereco = endereco
        self.enviadas = []
        self._recebidas = deque()
        self.fechado = False

    def enviar(self, mensagem, destino):
        self.enviadas.append((deepcopy(mensagem), destino))

    def receber(self, timeout=None):
        if not self._recebidas:
            raise socket.timeout()
        return deepcopy(self._recebidas.popleft())

    def adicionar_recebida(self, mensagem, origem):
        self._recebidas.append((deepcopy(mensagem), origem))

    def fechar(self):
        self.fechado = True
