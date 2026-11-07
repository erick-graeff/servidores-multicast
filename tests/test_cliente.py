import unittest
from unittest.mock import patch

from cliente import Cliente
from tests.doubles import CanalFake


def configuracao():
    return {"grupo": "224.1.1.1", "porta_grupo": 5007}


class RelogioCliente:
    def __init__(self, agora=0.0):
        self.agora = agora

    def __call__(self):
        return self.agora


class CanalComTempo(CanalFake):
    """CanalFake que avanca um relogio controlado a cada recebimento, como o
    recebimento real espera o timeout informado."""

    def __init__(self, relogio, endereco=("127.0.0.1", 0)):
        super().__init__(endereco)
        self.relogio = relogio

    def receber(self, timeout=None):
        if timeout:
            self.relogio.agora += timeout
        return super().receber(timeout)


def resposta(req_id):
    return {
        "tipo": "RESPOSTA",
        "req_id": req_id,
        "ok": True,
        "resultado": "consulta de saldo",
        "saldo": 0,
        "servidor": {"id": 1, "ip": "127.0.0.1", "porta": 6001},
    }


class ClienteTest(unittest.TestCase):
    def cria_cliente(self, canal, tentativas=3):
        return Cliente(configuracao(), "C1", None, tentativas, 2.0, canal)

    def test_retransmite_com_o_mesmo_req_id_ate_o_limite(self):
        relogio = RelogioCliente()
        canal = CanalComTempo(relogio)
        cliente = self.cria_cliente(canal, tentativas=3)

        # orcamento total = 3 tentativas x 2 s = 6 s; reenvio a cada 0,5 s
        with patch("cliente.uuid.uuid4") as uuid_fake, patch("cliente.time.time", new=relogio):
            uuid_fake.return_value.hex = "abcdef123456"
            resultado = cliente.requisita("SALDO")

        self.assertIsNone(resultado)
        self.assertEqual(12, len(canal.enviadas))  # envios em 0, 0.5, ..., 5.5 s
        self.assertEqual({"C1-abcdef"}, {m["req_id"] for m, _ in canal.enviadas})

    def test_orcamento_menor_gera_menos_envios(self):
        relogio = RelogioCliente()
        canal = CanalComTempo(relogio)
        cliente = self.cria_cliente(canal, tentativas=1)  # orcamento 2 s -> 4 envios

        with patch("cliente.uuid.uuid4") as uuid_fake, patch("cliente.time.time", new=relogio):
            uuid_fake.return_value.hex = "abcdef123456"
            resultado = cliente.requisita("SALDO")

        self.assertIsNone(resultado)
        self.assertEqual(4, len(canal.enviadas))

    def test_resposta_valida_interrompe_as_retransmissoes(self):
        canal = CanalFake()
        esperada = resposta("C1-abcdef")
        canal.adicionar_recebida(esperada, ("127.0.0.1", 6001))
        cliente = self.cria_cliente(canal, tentativas=6)

        with patch("cliente.uuid.uuid4") as uuid_fake:
            uuid_fake.return_value.hex = "abcdef123456"
            resultado = cliente.requisita("SALDO")

        self.assertEqual(esperada, resultado)
        self.assertEqual(1, len(canal.enviadas))

    def test_descarta_resposta_de_outro_req_id(self):
        canal = CanalFake()
        canal.adicionar_recebida(resposta("C1-antigo"), ("127.0.0.1", 6001))
        esperada = resposta("C1-abcdef")
        canal.adicionar_recebida(esperada, ("127.0.0.1", 6001))
        cliente = self.cria_cliente(canal)

        with patch("cliente.uuid.uuid4") as uuid_fake:
            uuid_fake.return_value.hex = "abcdef123456"
            resultado = cliente.requisita("SALDO")

        self.assertEqual(esperada, resultado)
        # a resposta de outro req_id nao conta como resposta; o cliente
        # retransmite e so entrega a requisicao quando a resposta correta chega
        self.assertEqual(2, len(canal.enviadas))


if __name__ == "__main__":
    unittest.main()
