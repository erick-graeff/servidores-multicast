#!/usr/bin/env python3
# =============================================================================
#  TP REDES II 2026 - Cliente do servidor tolerante a falhas
#  Dupla .................: Eduardo Camargo Neves e [NOME DO(A) COLEGA]
#  Funcionalidade ........: Cliente que envia requisicoes (consulta ou
#                           alteracao da conta) ao ENDERECO DO GRUPO multicast
#                           e mostra a resposta do lider: resultado,
#                           identificador, IP e porta do servidor que atendeu.
#                           Reenvia a mesma requisicao (mesmo req_id) se nao
#                           houver resposta, o que cobre a falha do lider.
#  Ultima modificacao ....: 02/11/2026
# =============================================================================
#
#  Uso:
#     python3 cliente.py SALDO
#     python3 cliente.py DEPOSITO 100
#     python3 cliente.py SAQUE 30
#     python3 cliente.py                 (modo interativo)
#  Opcoes: --config config.json --iface <IP desta maquina> --log arquivo
#          --nome C1 (identificacao do cliente nos logs)
# =============================================================================

import argparse
import json
import os
import socket
import sys
import time
import uuid
from datetime import datetime


class Cliente:
    def __init__(self, cfg, iface, nome, arquivo_log, tentativas, espera):
        self.grupo = (cfg["grupo"], cfg["porta_grupo"])
        self.nome = nome
        self.tentativas = tentativas
        self.espera = espera
        self.arq = None
        if arquivo_log:
            os.makedirs(os.path.dirname(arquivo_log) or ".", exist_ok=True)
            self.arq = open(arquivo_log, "a", encoding="utf-8")

        # Um unico socket UDP: envia ao grupo e recebe a resposta unicast do
        # lider (o lider responde para o IP:porta de origem da requisicao).
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((iface, 0))
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(iface))
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
        ip, porta = self.sock.getsockname()
        self.log(f"cliente em {ip}:{porta}, grupo {self.grupo[0]}:{self.grupo[1]}")

    def log(self, texto):
        agora = datetime.now()
        linha = f"{agora:%Y-%m-%d %H:%M:%S}.{agora.microsecond // 1000:03d} [{self.nome}] {texto}"
        print(linha, flush=True)
        if self.arq:
            self.arq.write(linha + "\n")
            self.arq.flush()

    def requisita(self, op, valor=0):
        """Envia a requisicao ao grupo e espera a resposta do lider.
        Se nao vier resposta, reenvia COM O MESMO req_id: assim, se o lider
        caiu depois de executar uma escrita, o novo lider reconhece o req_id
        e nao executa a escrita de novo."""
        req_id = f"{self.nome}-{uuid.uuid4().hex[:6]}"
        msg = {"tipo": "REQ", "req_id": req_id, "op": op.upper(), "valor": valor}
        desc = f"{op.upper()} {valor}" if op.upper() != "SALDO" else "SALDO"
        for t in range(1, self.tentativas + 1):
            self.log(f"ENVIA {req_id} '{desc}' ao grupo (tentativa {t}/{self.tentativas})")
            self.sock.sendto(json.dumps(msg).encode(), self.grupo)
            limite = time.time() + self.espera
            while time.time() < limite:
                self.sock.settimeout(max(0.01, limite - time.time()))
                try:
                    dados, origem = self.sock.recvfrom(65535)
                except socket.timeout:
                    break
                resp = json.loads(dados.decode())
                if resp.get("req_id") != req_id:
                    continue  # resposta atrasada de uma requisicao anterior
                s = resp["servidor"]
                extra = f", replicado em {['S%d' % i for i in resp['replicado_em']]}" if "replicado_em" in resp else ""
                self.log(f"RESPOSTA {req_id} do servidor S{s['id']} ({s['ip']}:{s['porta']}): "
                         f"{'OK' if resp['ok'] else 'RECUSADA'} - {resp['resultado']}, "
                         f"saldo={resp['saldo']}{extra}")
                return resp
            self.log(f"sem resposta em {self.espera:.1f}s para {req_id}")
        self.log(f"FALHA: nenhum servidor respondeu a {req_id} apos {self.tentativas} tentativas")
        return None


def main():
    ap = argparse.ArgumentParser(description="Cliente do grupo replicado (TP Redes II)")
    ap.add_argument("op", nargs="?", help="SALDO, DEPOSITO ou SAQUE")
    ap.add_argument("valor", nargs="?", type=int, default=0)
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--iface", default="0.0.0.0", help="IP desta maquina (interface multicast)")
    ap.add_argument("--nome", default="C1")
    ap.add_argument("--log", default=None)
    ap.add_argument("--tentativas", type=int, default=6)
    ap.add_argument("--espera", type=float, default=2.0, help="segundos de espera por tentativa")
    a = ap.parse_args()
    with open(a.config) as f:
        cfg = json.load(f)
    c = Cliente(cfg, a.iface, a.nome, a.log, a.tentativas, a.espera)

    if a.op:
        r = c.requisita(a.op, a.valor)
        sys.exit(0 if r else 1)

    print("Comandos: SALDO | DEPOSITO <valor> | SAQUE <valor> | SAIR")
    while True:
        try:
            partes = input("> ").split()
        except EOFError:
            break
        if not partes:
            continue
        if partes[0].upper() == "SAIR":
            break
        c.requisita(partes[0], int(partes[1]) if len(partes) > 1 else 0)


if __name__ == "__main__":
    main()
