import unittest

from membros import Membros


class MembrosTest(unittest.TestCase):
    def setUp(self):
        self.agora = 100.0
        self.membros = Membros(
            meu_id=2,
            ids={1, 2, 3},
            timeout=3.0,
            relogio=lambda: self.agora,
        )

    def avancar(self, segundos):
        self.agora += segundos

    def test_proprio_membro_sempre_esta_vivo(self):
        self.assertEqual({2}, self.membros.vivos())
        self.assertEqual(2, self.membros.lider())

    def test_heartbeats_tornam_outros_membros_vivos(self):
        self.membros.registrar_heartbeat(1, True)
        self.membros.registrar_heartbeat(3, True)

        self.assertEqual({1, 2, 3}, self.membros.vivos())
        self.assertEqual(1, self.membros.lider())

    def test_membro_sem_heartbeat_recente_deixa_o_conjunto_de_vivos(self):
        self.membros.registrar_heartbeat(1, True)
        self.membros.registrar_heartbeat(3, True)

        self.avancar(3.0)

        self.assertEqual({2}, self.membros.vivos())
        self.assertEqual(2, self.membros.lider())

    def test_heartbeat_renovado_mantem_membro_vivo(self):
        self.membros.registrar_heartbeat(1, True)
        self.avancar(2.0)
        self.membros.registrar_heartbeat(1, True)
        self.avancar(2.9)

        self.assertIn(1, self.membros.vivos())
        self.assertEqual(1, self.membros.lider())

    def test_idade_do_ultimo_heartbeat_e_informada(self):
        self.membros.registrar_heartbeat(1, True)

        self.avancar(1.3)
        self.assertAlmostEqual(1.3, self.membros.idade_heartbeat(1))
        self.assertIsNone(self.membros.idade_heartbeat(3))

    def test_membro_que_volta_a_enviar_heartbeat_reaparece(self):
        self.membros.registrar_heartbeat(1, True)
        self.avancar(3.1)
        self.assertNotIn(1, self.membros.vivos())

        self.membros.registrar_heartbeat(1, True)

        self.assertIn(1, self.membros.vivos())
        self.assertEqual(1, self.membros.lider())

    def test_estado_de_sincronizacao_acompanha_o_heartbeat(self):
        self.membros.registrar_heartbeat(1, True)
        self.membros.registrar_heartbeat(3, False)

        self.assertEqual({1}, self.membros.sincronizados({1, 3}))

        self.membros.registrar_heartbeat(1, False)
        self.membros.registrar_heartbeat(3, True)

        self.assertEqual({3}, self.membros.sincronizados({1, 3}))

    def test_heartbeat_proprio_ou_desconhecido_nao_altera_os_peers(self):
        self.membros.registrar_heartbeat(2, True)
        self.membros.registrar_heartbeat(99, True)

        self.assertEqual({2}, self.membros.vivos())
        self.assertEqual(set(), self.membros.sincronizados({2, 99}))


if __name__ == "__main__":
    unittest.main()
