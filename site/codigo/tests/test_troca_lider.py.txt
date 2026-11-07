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


def configuracao(timeout=3.0):
    return {
        "grupo": "224.1.1.1",
        "porta_grupo": 5007,
        "intervalo_heartbeat": 1.0,
        "timeout_falha": timeout,
        "servidores": [
            {"id": 1, "ip": "127.0.0.1", "porta": 6001},
            {"id": 2, "ip": "127.0.0.1", "porta": 6002},
        ],
    }


class TrocaDeLiderTest(unittest.TestCase):
    """Cenario: S1 e o lider e acaba de falhar (parada total) sem que S2
    ainda tenha percebido. A requisicao do cliente chega nessa janela e NAO
    pode ser descartada: quando S2 assume, ele deve atende-la."""

    def cria_s2(self, timeout=3.0):
        relogio = RelogioControlado()
        canal_uni = CanalFake(("127.0.0.1", 6002))
        servidor = Servidor(2, configuracao(timeout), CanalFake(), canal_uni)
        servidor.sincronizado = True
        servidor.inicio = 0
        servidor.estado_membros._relogio = relogio  # relogio controlado
        servidor.estado_membros.registrar_heartbeat(1, True)  # S1 visto vivo
        return servidor, canal_uni, relogio

    def requisita(self, servidor, relogio, req_id="C1-1", op="DEPOSITO", valor=10):
        with patch("servidor.time.time", new=relogio):
            servidor.trata_requisicao(
                {"tipo": "REQ", "req_id": req_id, "op": op, "valor": valor},
                ("127.0.0.1", 12345),
            )

    def respostas(self, canal):
        return [m for m, _ in canal.enviadas if m["tipo"] == "RESPOSTA"]

    def test_replica_guarda_a_requisicao_em_vez_de_descartar(self):
        servidor, canal, relogio = self.cria_s2()

        self.requisita(servidor, relogio)

        self.assertEqual(1, len(servidor.pendentes))
        self.assertEqual([], [m for m, _ in canal.enviadas if m["tipo"] in ("RESPOSTA", "REPLICA")])

    def test_reenvio_do_cliente_nao_duplica_a_requisicao_guardada(self):
        servidor, canal, relogio = self.cria_s2()

        self.requisita(servidor, relogio)
        self.requisita(servidor, relogio, req_id="C1-1")

        self.assertEqual(1, len(servidor.pendentes))

    def test_ao_assumir_a_lideranca_a_requisicao_guardada_e_atendida(self):
        servidor, canal, relogio = self.cria_s2()
        self.requisita(servidor, relogio)  # chegou durante a troca

        relogio.avancar(3.1)  # o heartbeat de S1 esgota o timeout: S2 assume
        with patch("servidor.time.time", new=relogio):
            servidor.atende_pendentes()

        respostas = self.respostas(canal)
        self.assertEqual(1, len(respostas))
        self.assertEqual(10, servidor.conta.consulta()["saldo"])
        self.assertEqual([], servidor.pendentes)

    def test_requisicao_guardada_expira_sem_ser_atendida(self):
        servidor, canal, relogio = self.cria_s2()
        self.requisita(servidor, relogio)

        relogio.avancar(9.9)  # prazo (timeout + 1) ja venceu
        with patch("servidor.time.time", new=relogio):
            servidor.atende_pendentes()

        self.assertEqual([], servidor.pendentes)
        self.assertEqual([], self.respostas(canal))
        self.assertEqual(0, servidor.conta.consulta()["saldo"])


if __name__ == "__main__":
    unittest.main()
