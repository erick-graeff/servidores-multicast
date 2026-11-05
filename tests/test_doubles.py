import socket
import unittest

from tests.doubles import CanalFake


class CanalFakeTest(unittest.TestCase):
    def test_enviar_registra_mensagem_e_destino(self):
        canal = CanalFake()
        mensagem = {"tipo": "REQ", "req_id": "C1-1"}
        destino = ("224.1.1.1", 5007)

        canal.enviar(mensagem, destino)

        self.assertEqual([(mensagem, destino)], canal.enviadas)

    def test_receber_entrega_mensagens_na_ordem_programada(self):
        canal = CanalFake()
        primeira = ({"tipo": "ACK", "id": 2}, ("127.0.0.1", 6002))
        segunda = ({"tipo": "ACK", "id": 3}, ("127.0.0.1", 6003))
        canal.adicionar_recebida(*primeira)
        canal.adicionar_recebida(*segunda)

        self.assertEqual(primeira, canal.receber())
        self.assertEqual(segunda, canal.receber())

    def test_receber_sem_mensagem_indica_timeout(self):
        canal = CanalFake()

        with self.assertRaises(socket.timeout):
            canal.receber(timeout=0.01)

    def test_mensagem_enviada_e_copiada(self):
        canal = CanalFake()
        mensagem = {"tipo": "REQ", "dados": {"valor": 10}}
        canal.enviar(mensagem, ("224.1.1.1", 5007))

        mensagem["dados"]["valor"] = 99

        self.assertEqual(10, canal.enviadas[0][0]["dados"]["valor"])


if __name__ == "__main__":
    unittest.main()
