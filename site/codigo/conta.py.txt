"""Estado e operacoes do servico de conta bancaria replicada."""

import threading
from copy import deepcopy


class Conta:
    def __init__(self):
        self.saldo = 0
        # cache: req_id -> resultado. Garante que uma escrita reenviada pelo
        # cliente (mesmo req_id) NAO seja executada duas vezes.
        self.cache = {}
        self.versao = 0
        self.versoes = {}
        self.lock = threading.Lock()

    def aplica(self, req_id, op, valor, versao=None):
        """Executa uma escrita uma unica vez, na proxima versao do estado."""
        with self.lock:
            if req_id in self.cache:
                return self.cache[req_id], False
            if versao is None:
                versao = self.versao + 1
            if versao != self.versao + 1:
                raise ValueError(f"versao {versao} fora de ordem; estado atual {self.versao}")
            if op == "DEPOSITO":
                self.saldo += valor
                res = {"ok": True, "msg": f"deposito de {valor} realizado", "saldo": self.saldo}
            elif op == "SAQUE":
                if valor > self.saldo:
                    res = {"ok": False, "msg": f"saldo insuficiente para saque de {valor}", "saldo": self.saldo}
                else:
                    self.saldo -= valor
                    res = {"ok": True, "msg": f"saque de {valor} realizado", "saldo": self.saldo}
            else:
                res = {"ok": False, "msg": f"operacao desconhecida {op}", "saldo": self.saldo}
            self.cache[req_id] = res
            self.versao = versao
            self.versoes[req_id] = versao
            return res, True

    def consulta(self):
        with self.lock:
            return {"ok": True, "msg": "consulta de saldo", "saldo": self.saldo}

    def versao_requisicao(self, req_id):
        with self.lock:
            return self.versoes[req_id]

    def snapshot(self):
        """Retorna uma copia consistente e versionada do estado."""
        with self.lock:
            return {
                "saldo": self.saldo,
                "cache": deepcopy(self.cache),
                "versao": self.versao,
                "versoes": dict(self.versoes),
            }

    def restaurar(self, estado):
        """Restaura um snapshot, recusando versoes anteriores ao estado atual."""
        with self.lock:
            if estado["versao"] < self.versao:
                return False
            self.saldo = estado["saldo"]
            self.cache = deepcopy(estado["cache"])
            self.versao = estado["versao"]
            self.versoes = dict(estado["versoes"])
            return True
