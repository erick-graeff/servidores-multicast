import unittest
from unittest.mock import patch

from cliente import Cliente
from servidor import Servidor
from tests.doubles import CanalFake


def configuracao():
    return {
        "grupo": "224.1.1.1",
        "porta_grupo": 5007,
        "intervalo_heartbeat": 1.0,
        "timeout_falha": 3.0,
        "servidores": [{"id": 1, "ip": "127.0.0.1", "porta": 6001}],
    }


class InjecaoCanaisTest(unittest.TestCase):
    def test_servidor_envia_ao_grupo_pelo_canal_injetado(self):
        canal_grupo = CanalFake(("127.0.0.1", 5007))
        canal_uni = CanalFake(("127.0.0.1", 6001))
        servidor = Servidor(1, configuracao(), canal_grupo, canal_uni)
        mensagem = {"tipo": "HEARTBEAT", "id": 1}

        servidor.envia_grupo(mensagem)

        self.assertEqual([(mensagem, ("224.1.1.1", 5007))], canal_uni.enviadas)
        self.assertEqual([], canal_grupo.enviadas)

    def test_cliente_faz_requisicao_pelo_canal_injetado(self):
        canal = CanalFake(("127.0.0.1", 12345))
        resposta = {
            "tipo": "RESPOSTA",
            "req_id": "C1-abcdef",
            "ok": True,
            "resultado": "consulta de saldo",
            "saldo": 0,
            "servidor": {"id": 1, "ip": "127.0.0.1", "porta": 6001},
        }
        canal.adicionar_recebida(resposta, ("127.0.0.1", 6001))
        cliente = Cliente(configuracao(), "C1", None, 1, 0.1, canal)

        with patch("cliente.uuid.uuid4") as uuid_fake:
            uuid_fake.return_value.hex = "abcdef123456"
            resultado = cliente.requisita("SALDO")

        self.assertEqual(resposta, resultado)
        self.assertEqual("C1-abcdef", canal.enviadas[0][0]["req_id"])
        self.assertEqual(("224.1.1.1", 5007), canal.enviadas[0][1])


if __name__ == "__main__":
    unittest.main()
