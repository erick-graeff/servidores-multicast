import unittest

from conta import Conta


class ContaTest(unittest.TestCase):
    def setUp(self):
        self.conta = Conta()

    def test_saldo_inicial_e_zero(self):
        resultado = self.conta.consulta()

        self.assertTrue(resultado["ok"])
        self.assertEqual(0, resultado["saldo"])

    def test_deposito_atualiza_o_saldo(self):
        resultado, nova = self.conta.aplica("C1-1", "DEPOSITO", 100)

        self.assertTrue(nova)
        self.assertTrue(resultado["ok"])
        self.assertEqual(100, resultado["saldo"])
        self.assertEqual(100, self.conta.consulta()["saldo"])

    def test_saque_atualiza_o_saldo(self):
        self.conta.aplica("C1-1", "DEPOSITO", 100)

        resultado, nova = self.conta.aplica("C1-2", "SAQUE", 30)

        self.assertTrue(nova)
        self.assertTrue(resultado["ok"])
        self.assertEqual(70, resultado["saldo"])

    def test_saque_sem_saldo_nao_altera_o_estado(self):
        self.conta.aplica("C1-1", "DEPOSITO", 100)

        resultado, nova = self.conta.aplica("C1-2", "SAQUE", 500)

        self.assertTrue(nova)
        self.assertFalse(resultado["ok"])
        self.assertEqual(100, resultado["saldo"])
        self.assertEqual(100, self.conta.consulta()["saldo"])

    def test_mesmo_req_id_nao_executa_a_escrita_duas_vezes(self):
        primeiro, nova_primeira = self.conta.aplica("C1-1", "DEPOSITO", 100)
        repetido, nova_repetida = self.conta.aplica("C1-1", "DEPOSITO", 100)

        self.assertTrue(nova_primeira)
        self.assertFalse(nova_repetida)
        self.assertEqual(primeiro, repetido)
        self.assertEqual(100, self.conta.consulta()["saldo"])

    def test_operacao_desconhecida_e_recusada_sem_alterar_o_saldo(self):
        resultado, _ = self.conta.aplica("C1-1", "TRANSFERENCIA", 100)

        self.assertFalse(resultado["ok"])
        self.assertEqual(0, resultado["saldo"])
        self.assertEqual(0, self.conta.consulta()["saldo"])

    def test_snapshot_preserva_saldo_versoes_e_idempotencia(self):
        self.conta.aplica("A", "DEPOSITO", 100)
        self.conta.aplica("B", "SAQUE", 30)

        snapshot = self.conta.snapshot()
        restaurada = self.conta.__class__()
        self.assertTrue(restaurada.restaurar(snapshot))
        _, nova = restaurada.aplica("A", "DEPOSITO", 100)

        self.assertFalse(nova)
        self.assertEqual(70, restaurada.consulta()["saldo"])
        self.assertEqual(2, snapshot["versao"])
        self.assertEqual({"A": 1, "B": 2}, snapshot["versoes"])

    def test_snapshot_antigo_nao_substitui_estado_mais_novo(self):
        self.conta.aplica("A", "DEPOSITO", 100)
        antigo = self.conta.snapshot()
        self.conta.aplica("B", "DEPOSITO", 50)

        self.assertFalse(self.conta.restaurar(antigo))
        self.assertEqual(150, self.conta.consulta()["saldo"])
        self.assertEqual(2, self.conta.snapshot()["versao"])


if __name__ == "__main__":
    unittest.main()
