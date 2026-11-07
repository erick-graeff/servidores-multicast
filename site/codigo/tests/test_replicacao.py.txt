import unittest
from unittest.mock import patch

from servidor import Servidor
from tests.doubles import CanalFake


class RelogioControlado:
    def __init__(self, agora=1000.0):
        self.agora = agora

    def __call__(self):
        return self.agora

    def avancar(self, segundos):
        self.agora += segundos


class CondicaoAckControlada:
    def __init__(self, relogio, ao_esperar=None):
        self.relogio = relogio
        self.ao_esperar = ao_esperar

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def wait(self, segundos):
        self.relogio.avancar(segundos)
        if self.ao_esperar:
            self.ao_esperar()


def configuracao(ids):
    return {
        "grupo": "224.1.1.1",
        "porta_grupo": 5007,
        "intervalo_heartbeat": 1.0,
        "timeout_falha": 3.0,
        "servidores": [{"id": sid, "ip": "127.0.0.1", "porta": 6000 + sid} for sid in ids],
    }


class ReplicacaoTest(unittest.TestCase):
    def cria_servidor(self, ids=(1, 2), ao_esperar=None):
        canal = CanalFake(("127.0.0.1", 6001))
        servidor = Servidor(1, configuracao(ids), CanalFake(), canal)
        servidor.sincronizado = True
        servidor.inicio = 0
        for sid in ids:
            if sid != 1:
                servidor.estado_membros.registrar_heartbeat(sid, True)
        relogio = RelogioControlado()
        servidor.cond_ack = CondicaoAckControlada(relogio, ao_esperar)
        return servidor, canal, relogio

    def executa_deposito(self, servidor, relogio, req_id="C1-1"):
        with patch("servidor.time.time", new=relogio):
            servidor.trata_requisicao(
                {"tipo": "REQ", "req_id": req_id, "op": "DEPOSITO", "valor": 10},
                ("127.0.0.1", 12345),
            )

    def respostas(self, canal):
        return [m for m, _ in canal.enviadas if m["tipo"] == "RESPOSTA"]

    def test_confirma_sucesso_depois_dos_acks(self):
        servidor, canal, relogio = self.cria_servidor(ao_esperar=lambda: servidor.acks["C1-1"].add(2))

        self.executa_deposito(servidor, relogio)

        resposta = self.respostas(canal)[0]
        self.assertTrue(resposta["ok"])
        self.assertEqual([1, 2], resposta["replicado_em"])
        replica = next(m for m, _ in canal.enviadas if m["tipo"] == "REPLICA")
        self.assertEqual(10, replica["saldo_lider"])
        self.assertEqual(1, replica["versao"])
        self.assertEqual(10, servidor.conta.consulta()["saldo"])

    def test_timeout_com_replica_viva_nao_confirma_sucesso(self):
        servidor, canal, relogio = self.cria_servidor()

        self.executa_deposito(servidor, relogio)

        respostas = self.respostas(canal)
        self.assertEqual(1, len(respostas))
        self.assertFalse(respostas[0]["ok"])
        self.assertEqual("REPLICACAO_NAO_CONFIRMADA", respostas[0].get("erro"))
        replicas = [m for m, _ in canal.enviadas if m["tipo"] == "REPLICA"]
        self.assertGreaterEqual(len(replicas), 2)

    def test_ack_duplicado_nao_substitui_ack_de_outra_replica(self):
        servidor, canal, relogio = self.cria_servidor(
            ids=(1, 2, 3),
            ao_esperar=lambda: servidor.acks["C1-1"].add(2),
        )

        self.executa_deposito(servidor, relogio)

        resposta = self.respostas(canal)[0]
        self.assertFalse(resposta["ok"])
        self.assertEqual([1, 2], resposta["replicado_em"])

    def test_reenvio_da_mesma_requisicao_nao_duplica_o_deposito(self):
        servidor, canal, relogio = self.cria_servidor(ids=(1,))

        self.executa_deposito(servidor, relogio)
        self.executa_deposito(servidor, relogio)

        self.assertEqual(10, servidor.conta.consulta()["saldo"])
        self.assertEqual(2, len(self.respostas(canal)))
        self.assertTrue(all(r["ok"] for r in self.respostas(canal)))


if __name__ == "__main__":
    unittest.main()
