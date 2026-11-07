from html.parser import HTMLParser
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import gera_pagina


RAIZ = Path(__file__).resolve().parents[1]


class LinksHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)


class EntregaHTMLTest(unittest.TestCase):
    def setUp(self):
        self.temporario = tempfile.TemporaryDirectory()
        self.site = Path(self.temporario.name) / "site"
        with patch("gera_pagina.SITE", str(self.site)):
            gera_pagina.gera(str(RAIZ / "logs" / "pos_correcoes"))
        self.index = (self.site / "index.html").read_text(encoding="utf-8")
        self.relatorio = (self.site / "relatorio.html").read_text(encoding="utf-8")

    def tearDown(self):
        self.temporario.cleanup()

    def test_paginas_principais_sao_geradas(self):
        self.assertIn("TP Redes II 2026", self.index)
        self.assertIn("Servidor tolerante a falhas", self.relatorio)

    def test_codigos_publicados_sao_copias_exatas_em_txt(self):
        for nome, _ in gera_pagina.CODIGOS:
            with self.subTest(nome=nome):
                publicado = self.site / "codigo" / f"{nome}.txt"
                self.assertTrue(publicado.name.endswith(".txt"))
                self.assertTrue(publicado.is_file())
                self.assertEqual((RAIZ / nome).read_bytes(), publicado.read_bytes())

    def test_links_locais_das_paginas_resolvem(self):
        for nome in ("index.html", "relatorio.html"):
            caminho = self.site / nome
            parser = LinksHTML()
            parser.feed(caminho.read_text(encoding="utf-8"))
            for href in parser.links:
                if href.startswith(("#", "http://", "https://", "mailto:")):
                    continue
                destino = href.split("#", 1)[0]
                with self.subTest(pagina=nome, href=href):
                    self.assertTrue((caminho.parent / destino).is_file())

    def test_relatorio_usa_os_resultados_locais_finais(self):
        self.assertIn("15 cenários", self.relatorio)
        self.assertIn("92 de 92", self.relatorio)
        self.assertIn("52/52", self.relatorio)

    def test_autoria_nao_contem_placeholder(self):
        conteudo = self.index + self.relatorio
        self.assertNotIn("[NOME DO(A) COLEGA]", conteudo)
        self.assertIn("Eduardo Camargo Neves e Erick Graeff Petzold", conteudo)


if __name__ == "__main__":
    unittest.main()
