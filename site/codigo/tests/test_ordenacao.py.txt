import unittest

from servidor import Servidor
from tests.doubles import CanalFake


def configuracao():
    return {
        "grupo": "224.1.1.1",
        "porta_grupo": 5007,
        "intervalo_heartbeat": 1.0,
        "timeout_falha": 3.0,
        "servidores": [
            {"id": 1, "ip": "127.0.0.1", "porta": 6001},
            {"id": 2, "ip": "127.0.0.1", "porta": 6002},
        ],
    }


def replica(req_id, valor, versao, saldo_lider):
    return {
        "tipo": "REPLICA",
        "req_id": req_id,
        "op": "DEPOSITO",
        "valor": valor,
        "lider": 1,
        "versao": versao,
        "saldo_lider": saldo_lider,
    }


def estado(versao, saldo, cache, versoes):
    return {
        "tipo": "STATE",
        "id": 1,
        "versao": versao,
        "saldo": saldo,
        "cache": cache,
        "versoes": versoes,
    }


class OrdenacaoSincronizacaoTest(unittest.TestCase):
    def cria_replica(self, sincronizada=True):
        canal = CanalFake(("127.0.0.1", 6002))
        servidor = Servidor(2, configuracao(), CanalFake(), canal)
        servidor.sincronizado = sincronizada
        return servidor, canal

    def acks(self, canal):
        return [m for m, _ in canal.enviadas if m["tipo"] == "ACK"]

    def test_replica_antiga_nao_faz_o_saldo_regredir(self):
        servidor, canal = self.cria_replica()
        primeira = replica("A", 100, 1, 100)
        servidor.trata_replica(primeira)
        servidor.trata_replica(replica("B", 50, 2, 150))

        servidor.trata_replica(primeira)

        self.assertEqual(150, servidor.conta.consulta()["saldo"])
        self.assertEqual(3, len(self.acks(canal)))

    def test_replica_com_lacuna_nao_e_aplicada_nem_confirmada(self):
        servidor, canal = self.cria_replica()

        servidor.trata_replica(replica("B", 50, 2, 150))

        self.assertEqual(0, servidor.conta.consulta()["saldo"])
        self.assertEqual([], self.acks(canal))

    def test_replica_nao_sincronizada_nao_aplica_nem_confirma(self):
        servidor, canal = self.cria_replica(sincronizada=False)

        servidor.trata_replica(replica("A", 100, 1, 100))

        self.assertEqual(0, servidor.conta.consulta()["saldo"])
        self.assertEqual([], self.acks(canal))

    def test_state_antigo_nao_substitui_estado_mais_novo(self):
        servidor, _ = self.cria_replica(sincronizada=False)
        servidor.conta.aplica("A", "DEPOSITO", 100)
        servidor.conta.aplica("B", "DEPOSITO", 50)
        antigo = estado(
            1,
            100,
            {"A": {"ok": True, "msg": "deposito", "saldo": 100}},
            {"A": 1},
        )

        servidor.recebe_estado(antigo)

        self.assertEqual(150, servidor.conta.consulta()["saldo"])
        self.assertFalse(servidor.sincronizado)

    def test_replica_recebida_antes_do_state_pode_ser_repetida_depois(self):
        servidor, canal = self.cria_replica(sincronizada=False)
        mensagem = replica("B", 50, 2, 150)
        servidor.trata_replica(mensagem)
        atual = estado(
            2,
            150,
            {
                "A": {"ok": True, "msg": "deposito", "saldo": 100},
                "B": {"ok": True, "msg": "deposito", "saldo": 150},
            },
            {"A": 1, "B": 2},
        )

        servidor.recebe_estado(atual)
        servidor.trata_replica(mensagem)

        self.assertTrue(servidor.sincronizado)
        self.assertEqual(150, servidor.conta.consulta()["saldo"])
        self.assertEqual(1, len(self.acks(canal)))

    def test_sync_req_marca_o_reintegrante_como_vivo(self):
        canal = CanalFake(("127.0.0.1", 6001))
        servidor = Servidor(1, configuracao(), CanalFake(), canal)
        servidor.sincronizado = True

        servidor.trata_sync({"tipo": "SYNC_REQ", "id": 2})

        self.assertIn(2, servidor.vivos())
        estados = [m for m, _ in canal.enviadas if m["tipo"] == "STATE"]
        self.assertEqual(1, len(estados))
        self.assertEqual(0, estados[0]["versao"])


if __name__ == "__main__":
    unittest.main()
