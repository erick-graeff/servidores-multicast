"""Monitoramento dos membros do grupo e eleicao do menor ID sem-falha."""

import threading
import time


class Membros:
    def __init__(self, meu_id, ids, timeout, relogio=None):
        self.meu_id = meu_id
        self.ids = set(ids)
        self.timeout = timeout
        self._relogio = relogio or time.time
        self._ultimo_hb = {}
        self._sincronizados = set()
        self._lock = threading.Lock()

    def registrar_heartbeat(self, membro_id, sinc):
        if membro_id == self.meu_id or membro_id not in self.ids:
            return
        with self._lock:
            self._ultimo_hb[membro_id] = self._relogio()
            if sinc:
                self._sincronizados.add(membro_id)
            else:
                self._sincronizados.discard(membro_id)

    def vivos(self):
        """Retorna eu + membros cujo heartbeat esta dentro do timeout."""
        agora = self._relogio()
        with self._lock:
            vivos = {i for i, instante in self._ultimo_hb.items() if agora - instante < self.timeout}
        vivos.add(self.meu_id)
        return vivos

    def idade_heartbeat(self, membro_id):
        """Idade do ultimo heartbeat recebido do membro (None se nunca chegou)."""
        with self._lock:
            instante = self._ultimo_hb.get(membro_id)
        return None if instante is None else self._relogio() - instante

    def lider(self):
        return min(self.vivos())

    def sincronizados(self, entre):
        """Retorna quais dos IDs informados anunciaram ter estado."""
        with self._lock:
            return set(entre) & self._sincronizados
