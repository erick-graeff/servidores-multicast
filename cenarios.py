#!/usr/bin/env python3
# =============================================================================
#  TP REDES II 2026 - Roteiro automatico dos cenarios de teste
#  Dupla .................: Eduardo Camargo Neves e Erick Graeff Petzold
#  Funcionalidade ........: Sobe os servidores, executa requisicoes de
#                           clientes, mata processos com SIGKILL (kill -9,
#                           parada total) em varias combinacoes, confere o
#                           servidor que respondeu e o saldo, e grava os logs
#                           de cada processo + uma linha do tempo unificada.
#                           Uso para testes numa unica maquina; no laboratorio
#                           os mesmos cenarios sao feitos a mao em 3 hosts.
#  Ultima modificacao ....: 02/11/2026
# =============================================================================
#
#  Uso: python3 cenarios.py [--iface 127.0.0.1] [--saida logs]
# =============================================================================

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime

AQUI = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable


class Cenario:
    def __init__(self, num, titulo, pasta, iface):
        self.num, self.titulo, self.iface = num, titulo, iface
        self.pasta = pasta
        os.makedirs(pasta, exist_ok=True)
        self.procs = {}
        self.checks = []
        self.roteiro = open(os.path.join(pasta, "roteiro.log"), "w", encoding="utf-8")
        self.n_cli = 0

    def nota(self, texto):
        agora = datetime.now()
        linha = f"{agora:%Y-%m-%d %H:%M:%S}.{agora.microsecond // 1000:03d} [ROTEIRO] {texto}"
        print(linha, flush=True)
        self.roteiro.write(linha + "\n")
        self.roteiro.flush()

    def sobe(self, sid, falha=None):
        args = [
            PY,
            os.path.join(AQUI, "servidor.py"),
            "--id",
            str(sid),
            "--config",
            os.path.join(AQUI, "config.json"),
            "--log",
            os.path.join(self.pasta, f"servidor_S{sid}.log"),
        ]
        if falha:
            args += ["--falha", falha]
        if os.path.exists(os.path.join(self.pasta, f"servidor_S{sid}.log")):
            # servidor reiniciado: guarda o log da execucao anterior
            os.replace(os.path.join(self.pasta, f"servidor_S{sid}.log"), os.path.join(self.pasta, f"servidor_S{sid}_execucao1.log"))
        p = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.procs[sid] = p
        self.nota(f"inicia S{sid} (pid {p.pid})" + (f" com falha injetada '{falha}'" if falha else ""))

    def mata(self, sid):
        p = self.procs[sid]
        self.nota(f"kill -9 {p.pid}  -> S{sid} sofre PARADA TOTAL")
        os.kill(p.pid, signal.SIGKILL)
        p.wait()

    def espera(self, s, motivo=""):
        self.nota(f"aguarda {s}s {motivo}".rstrip())
        time.sleep(s)

    def cliente(self, op, valor=0, esperado_srv=None, esperado_saldo=None, nome=None):
        self.n_cli += 1
        nome = nome or "C1"
        args = (
            [PY, os.path.join(AQUI, "cliente.py"), op]
            + ([str(valor)] if op != "SALDO" else [])
            + [
                "--config",
                os.path.join(AQUI, "config.json"),
                "--iface",
                self.iface,
                "--nome",
                nome,
                "--log",
                os.path.join(self.pasta, "cliente.log"),
            ]
        )
        desc = op if op == "SALDO" else f"{op} {valor}"
        self.nota(f"cliente {nome}: {desc}")
        out = subprocess.run(args, capture_output=True, text=True).stdout
        m = re.search(r"RESPOSTA \S+ do servidor S(\d+) .*saldo=(-?\d+)", out)
        srv = int(m.group(1)) if m else None
        saldo = int(m.group(2)) if m else None
        ok = (srv == esperado_srv) and (esperado_saldo is None or saldo == esperado_saldo)
        exp = f"S{esperado_srv}" if esperado_srv else "nenhuma resposta"
        obt = f"S{srv}" if srv else "nenhuma resposta"
        if esperado_saldo is not None:
            exp += f", saldo={esperado_saldo}"
        if saldo is not None:
            obt += f", saldo={saldo}"
        self.checks.append({"req": desc, "esperado": exp, "obtido": obt, "ok": ok})
        self.nota(f"  -> esperado: {exp} | obtido: {obt} | {'OK' if ok else 'ERRO'}")
        return srv, saldo

    def confere_replicas(self, saldo_esperado):
        """Confere no log de cada servidor vivo o ultimo saldo registrado:
        todas as replicas sem falha devem ter o mesmo estado."""
        time.sleep(0.5)
        for sid, p in sorted(self.procs.items()):
            if p.poll() is not None:
                continue
            with open(os.path.join(self.pasta, f"servidor_S{sid}.log"), encoding="utf-8") as f:
                saldos = re.findall(r"saldo=(-?\d+)", f.read())
            s = int(saldos[-1]) if saldos else 0
            ok = s == saldo_esperado
            self.checks.append(
                {"req": f"estado da replica S{sid}", "esperado": f"saldo={saldo_esperado}", "obtido": f"saldo={s}", "ok": ok}
            )
            self.nota(f"estado de S{sid}: saldo={s} (esperado {saldo_esperado}) {'OK' if ok else 'ERRO'}")

    def encerra(self):
        for sid, p in self.procs.items():
            if p.poll() is None:
                p.send_signal(signal.SIGKILL)
                p.wait()
        self.nota("fim do cenario")
        self.roteiro.close()
        # linha do tempo unificada: junta e ordena por horario todas as linhas
        linhas = []
        for nome in sorted(os.listdir(self.pasta)):
            if nome.endswith(".log") and nome != "linha_do_tempo.log":
                with open(os.path.join(self.pasta, nome), encoding="utf-8") as f:
                    linhas += [l.rstrip("\n") for l in f if l.strip()]
        linhas.sort(key=lambda l: l[:23])
        with open(os.path.join(self.pasta, "linha_do_tempo.log"), "w", encoding="utf-8") as f:
            f.write("\n".join(linhas) + "\n")


def sobe_tres(c):
    for i in (1, 2, 3):
        c.sobe(i)
    c.espera(4, "(heartbeats e eleicao inicial)")


DETECCAO = 4  # timeout de 3 s + folga


def c01(c):
    sobe_tres(c)
    c.cliente("SALDO", esperado_srv=1, esperado_saldo=0)
    c.cliente("DEPOSITO", 100, esperado_srv=1, esperado_saldo=100)
    c.cliente("SAQUE", 30, esperado_srv=1, esperado_saldo=70)
    c.cliente("SAQUE", 500, esperado_srv=1, esperado_saldo=70)  # recusado: saldo insuficiente
    c.cliente("SALDO", esperado_srv=1, esperado_saldo=70)
    c.confere_replicas(70)


def c02(c):
    sobe_tres(c)
    c.cliente("DEPOSITO", 100, esperado_srv=1, esperado_saldo=100)
    c.mata(1)
    c.espera(DETECCAO, "(S2 e S3 detectam a falha de S1)")
    c.cliente("SALDO", esperado_srv=2, esperado_saldo=100)
    c.cliente("DEPOSITO", 50, esperado_srv=2, esperado_saldo=150)
    c.cliente("SALDO", esperado_srv=2, esperado_saldo=150)
    c.confere_replicas(150)


def c03(c):
    sobe_tres(c)
    c.mata(1)
    c.nota("cliente envia IMEDIATAMENTE, antes de a falha ser detectada")
    c.cliente("DEPOSITO", 40, esperado_srv=2, esperado_saldo=40)
    c.confere_replicas(40)


def c04(c):
    sobe_tres(c)
    c.cliente("DEPOSITO", 200, esperado_srv=1, esperado_saldo=200)
    c.mata(2)
    c.espera(DETECCAO, "(S1 e S3 detectam a falha de S2)")
    c.cliente("SAQUE", 20, esperado_srv=1, esperado_saldo=180)
    c.cliente("SALDO", esperado_srv=1, esperado_saldo=180)
    c.confere_replicas(180)


def c05(c):
    sobe_tres(c)
    c.cliente("DEPOSITO", 10, esperado_srv=1, esperado_saldo=10)
    c.mata(1)
    c.mata(2)
    c.espera(DETECCAO, "(S3 detecta as falhas de S1 e S2)")
    c.cliente("DEPOSITO", 5, esperado_srv=3, esperado_saldo=15)
    c.cliente("SALDO", esperado_srv=3, esperado_saldo=15)
    c.confere_replicas(15)


def c06(c):
    sobe_tres(c)
    c.cliente("DEPOSITO", 10, esperado_srv=1, esperado_saldo=10)
    c.mata(1)
    c.mata(3)
    c.espera(DETECCAO, "(S2 detecta as falhas de S1 e S3)")
    c.cliente("DEPOSITO", 7, esperado_srv=2, esperado_saldo=17)
    c.cliente("SALDO", esperado_srv=2, esperado_saldo=17)
    c.confere_replicas(17)


def c07(c):
    sobe_tres(c)
    c.mata(2)
    c.mata(3)
    c.espera(DETECCAO, "(S1 detecta as falhas de S2 e S3)")
    c.cliente("DEPOSITO", 60, esperado_srv=1, esperado_saldo=60)
    c.cliente("SALDO", esperado_srv=1, esperado_saldo=60)
    c.confere_replicas(60)


def c08(c):
    for i in (1, 2):
        c.sobe(i)
    c.sobe(3, falha="replica-durante-escrita")
    c.espera(4, "(heartbeats e eleicao inicial)")
    c.nota("S3 vai parar no instante em que receber a REPLICA, sem confirmar")
    c.cliente("DEPOSITO", 80, esperado_srv=1, esperado_saldo=80)
    c.cliente("SALDO", esperado_srv=1, esperado_saldo=80)
    c.confere_replicas(80)


def c09(c):
    c.sobe(1, falha="lider-antes-de-responder")
    for i in (2, 3):
        c.sobe(i)
    c.espera(4, "(heartbeats e eleicao inicial)")
    c.nota("S1 vai executar e replicar a escrita e parar ANTES de responder ao cliente")
    c.cliente("DEPOSITO", 100, esperado_srv=2, esperado_saldo=100)
    c.nota("o deposito NAO pode ter sido aplicado duas vezes: saldo deve ser 100, nao 200")
    c.cliente("SALDO", esperado_srv=2, esperado_saldo=100)
    c.confere_replicas(100)


def c10(c):
    sobe_tres(c)
    c.cliente("DEPOSITO", 100, esperado_srv=1, esperado_saldo=100)
    c.mata(1)
    c.espera(DETECCAO, "(S1 morto, S2 assume)")
    c.cliente("DEPOSITO", 50, esperado_srv=2, esperado_saldo=150)
    c.sobe(1)
    c.espera(5, "(S1 volta, pede o estado ao lider e reassume por ter o menor ID)")
    c.cliente("SALDO", esperado_srv=1, esperado_saldo=150)
    c.cliente("SAQUE", 25, esperado_srv=1, esperado_saldo=125)
    c.confere_replicas(125)


def c11(c):
    sobe_tres(c)
    resultados = []

    def rajada():
        for k in range(6):
            resultados.append(c.cliente("DEPOSITO", 10, esperado_srv=(1 if k == 0 else 2), esperado_saldo=10 * (k + 1), nome="C2"))
            time.sleep(1)

    t = threading.Thread(target=rajada)
    t.start()
    time.sleep(0.6)
    c.mata(1)
    t.join()
    c.cliente("SALDO", esperado_srv=2, esperado_saldo=60)
    c.confere_replicas(60)


def c12(c):
    sobe_tres(c)
    c.cliente("DEPOSITO", 30, esperado_srv=1, esperado_saldo=30)
    for i in (1, 2, 3):
        c.mata(i)
    c.cliente("SALDO", esperado_srv=None)


def reintegra_replica_durante_escrita(c, sid):
    sobe_tres(c)
    c.cliente("DEPOSITO", 100, esperado_srv=1, esperado_saldo=100)
    c.mata(sid)
    c.espera(DETECCAO, f"(S{sid} morto; os demais detectam a falha)")
    c.cliente("DEPOSITO", 50, esperado_srv=1, esperado_saldo=150)
    c.sobe(sid)
    c.nota(f"S{sid} reinicia e o cliente escreve durante sua sincronizacao")
    c.cliente("DEPOSITO", 25, esperado_srv=1, esperado_saldo=175)
    c.espera(5, f"(S{sid} recebe o estado e processa retransmissoes)")
    c.cliente("SALDO", esperado_srv=1, esperado_saldo=175)
    c.confere_replicas(175)


def c13(c):
    reintegra_replica_durante_escrita(c, 2)


def c14(c):
    reintegra_replica_durante_escrita(c, 3)


def c15(c):
    sobe_tres(c)
    erros = []

    def rajada(nome):
        try:
            for _ in range(5):
                c.cliente("DEPOSITO", 10, esperado_srv=1, nome=nome)
        except Exception as exc:
            erros.append(exc)

    threads = [threading.Thread(target=rajada, args=(f"C{i}",)) for i in (2, 3, 4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    if erros:
        raise erros[0]

    c.cliente("SALDO", esperado_srv=1, esperado_saldo=150)
    c.confere_replicas(150)


CENARIOS = [
    (1, "Todos sem falha: consultas e alteracoes atendidas por S1", c01),
    (2, "Falha do lider S1: S2 assume e mantem o estado", c02),
    (3, "Requisicao enviada logo apos a falha do lider (antes da deteccao)", c03),
    (4, "Falha de uma replica (S2): S1 continua lider e nao espera S2", c04),
    (5, "Falhas de S1 e S2: S3 atende sozinho", c05),
    (6, "Falhas de S1 e S3: S2 atende sozinho", c06),
    (7, "Falhas de S2 e S3: S1 atende sozinho", c07),
    (8, "Replica S3 para no meio de uma escrita", c08),
    (9, "Lider para depois de replicar e antes de responder (sem execucao dupla)", c09),
    (10, "S1 falha, S2 assume, S1 volta, recebe o estado e reassume", c10),
    (11, "Cliente enviando escritas enquanto o lider e morto", c11),
    (12, "Todos os servidores falhos: cliente fica sem resposta", c12),
    (13, "S2 volta e recebe escrita durante a sincronizacao", c13),
    (14, "S3 volta e recebe escrita durante a sincronizacao", c14),
    (15, "Tres clientes concorrentes mantêm as replicas consistentes", c15),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iface", default="127.0.0.1")
    ap.add_argument("--saida", default=os.path.join(AQUI, "logs"))
    ap.add_argument("--so", type=int, nargs="*", help="rodar so estes cenarios")
    a = ap.parse_args()
    resumo = []
    for num, titulo, fn in CENARIOS:
        if a.so and num not in a.so:
            continue
        pasta = os.path.join(a.saida, f"cenario{num:02d}")
        for f in os.listdir(pasta) if os.path.isdir(pasta) else []:
            os.remove(os.path.join(pasta, f))
        c = Cenario(num, titulo, pasta, a.iface)
        c.nota(f"===== CENARIO {num}: {titulo} =====")
        try:
            fn(c)
        finally:
            c.encerra()
        resumo.append({"num": num, "titulo": titulo, "checks": c.checks, "ok": all(x["ok"] for x in c.checks)})
        time.sleep(1)
    with open(os.path.join(a.saida, "resumo.json"), "w", encoding="utf-8") as f:
        json.dump(resumo, f, indent=2, ensure_ascii=False)
    print()
    for r in resumo:
        print(f"Cenario {r['num']:2d}: {'PASSOU' if r['ok'] else 'FALHOU'} - {r['titulo']}")


if __name__ == "__main__":
    main()
