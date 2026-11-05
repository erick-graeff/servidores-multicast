# =============================================================================
#  TP REDES II 2026 - Servidor tolerante a falhas com grupo multicast
#  Dupla .................: Eduardo Camargo Neves e Erick Graeff Petzold
#  Funcionalidade ........: Processo servidor do grupo replicado. Implementa
#                           heartbeat por multicast, deteccao de falhas por
#                           parada total, eleicao do lider (menor ID sem
#                           falha), servico de conta bancaria (consulta e
#                           alteracao) e replicacao das escritas com ACK.
#  Ultima modificacao ....: 02/11/2026
# =============================================================================
#
#  Uso:
#     python3 servidor.py --id 1 [--config config.json] [--log logs/s1.log]
#
#  Visao geral das mensagens (todas em JSON, via UDP):
#
#   multicast (endereco do grupo, recebidas por todos os servidores):
#     HEARTBEAT  {id, sinc}                "estou sem falha" (+ se ja tenho estado)
#     REQ        {req_id, op, valor}       requisicao do cliente
#     REPLICA    {req_id, op, valor, lider, versao, saldo_lider} lider pede que as replicas executem
#     SYNC_REQ   {id}                      servidor que (re)iniciou pede o estado
#
#   unicast (IP:porta de cada processo, conhecidos por todos via config.json):
#     ACK        {req_id, id}              replica confirma ao lider
#     STATE      {saldo, cache, versao, versoes, id} lider envia o estado a quem reiniciou
#     RESPOSTA   {...}                     lider responde ao cliente
# =============================================================================

import argparse
import json
import logging
import os
import sys
import threading
import time

from comunicacao import abrir_canal_multicast
from comunicacao import abrir_canal_unicast
from conta import Conta
from membros import Membros

# -----------------------------------------------------------------------------
#  Servico oferecido pelo grupo: conta bancaria
#    SALDO            -> consulta (leitura)
#    DEPOSITO <valor> -> alteracao (escrita)
#    SAQUE <valor>    -> alteracao (escrita); recusada se o saldo for insuficiente
#  A operacao e deterministica: todas as replicas que executam a mesma
#  sequencia de escritas chegam ao mesmo saldo.
# -----------------------------------------------------------------------------
OPS_LEITURA = {"SALDO"}
OPS_ESCRITA = {"DEPOSITO", "SAQUE"}


# -----------------------------------------------------------------------------
#  Processo servidor
# -----------------------------------------------------------------------------
class Servidor:
    def __init__(self, meu_id, cfg, canal_grupo, canal_uni, falha_injetada=None):
        self.id = meu_id
        self.cfg = cfg
        self.membros = {s["id"]: s for s in cfg["servidores"]}  # todos conhecem todos
        self.eu = self.membros[meu_id]
        self.grupo = (cfg["grupo"], cfg["porta_grupo"])
        self.hb_intervalo = cfg["intervalo_heartbeat"]
        self.timeout = cfg["timeout_falha"]
        self.timeout_escrita = cfg.get("timeout_escrita", 8.0)
        self.estado_membros = Membros(meu_id, set(self.membros), self.timeout)
        self.falha_injetada = falha_injetada  # usado so nos testes (ver main)

        self.conta = Conta()
        self.inicio = time.time()
        self.sincronizado = False  # ja tem o estado atual da conta?

        self.vivos_anteriores = set()
        self.lider_anterior = None

        # controle de ACKs das escritas em andamento
        self.acks = {}  # req_id -> conjunto de ids que confirmaram
        self.cond_ack = threading.Condition()
        self.lock_escrita = threading.Lock()  # o lider executa uma escrita por vez
        self.lock_estado = threading.RLock()  # serializa REPLICA, STATE e snapshots

        # Os canais sao montados no main e injetados aqui. O canal do grupo
        # recebe multicast; o unicast envia ao grupo e recebe ACK / STATE.
        self.canal_grupo = canal_grupo
        self.canal_uni = canal_uni

        self.log = logging.getLogger("servidor")

    # ---------------------------------------------------------------- membros
    def vivos(self):
        """Conjunto de membros considerados sem falha pelo monitor do grupo."""
        return self.estado_membros.vivos()

    def lider(self):
        """Lider = membro sem falha de MENOR identificador."""
        return self.estado_membros.lider()

    def sou_lider(self):
        return self.lider() == self.id

    def em_inicializacao(self):
        """
        Durante o primeiro 'timeout' apos iniciar, o servidor ainda nao sabe

        quem esta vivo; por isso nao atende clientes nesse periodo (senao
        poderia se achar lider por engano). Depois disso:
          - se algum membro vivo ja tem estado (flag 'sinc' do heartbeat),
            espera receber o estado dele (servidor voltando de uma falha);
          - se nenhum tem, todos estao comecando juntos e o estado inicial
            (saldo 0) ja e o estado correto.
        """
        if time.time() - self.inicio < self.timeout:
            return True
        if not self.sincronizado:
            outros = self.vivos() - {self.id}
            com_estado = self.estado_membros.sincronizados(outros)
            if com_estado:
                return True
            self.sincronizado = True
            self.log.info("nenhum membro vivo tem estado anterior: comeca com saldo 0")
        return False

    # --------------------------------------------------------------- threads
    def thread_heartbeat(self):
        """Periodicamente envia HEARTBEAT ao grupo."""
        while True:
            self.envia_grupo({"tipo": "HEARTBEAT", "id": self.id, "sinc": self.sincronizado})
            time.sleep(self.hb_intervalo)

    def thread_monitor(self):
        """Verifica a lista de vivos e registra no log as mudancas:
        membro detectado, membro falho e troca de lider."""
        while True:
            time.sleep(0.2)
            v = self.vivos()
            for i in sorted(v - self.vivos_anteriores):
                if i != self.id:
                    self.log.info(f"MEMBRO S{i} detectado sem falha (heartbeat recebido)")
            for i in sorted(self.vivos_anteriores - v):
                self.log.warning(f"FALHA detectada: S{i} sem heartbeat ha mais de {self.timeout:.1f}s")
            if v != self.vivos_anteriores:
                self.log.info(f"VIVOS = {sorted(v)}")
            self.vivos_anteriores = v
            if not self.em_inicializacao():
                l = min(v)
                if l != self.lider_anterior:
                    papel = "EU SOU O LIDER" if l == self.id else "sou replica"
                    self.log.info(f"LIDER eleito = S{l} (menor ID sem falha) -> {papel}")
                    self.lider_anterior = l

    def thread_grupo(self):
        """Recebe tudo que chega ao grupo multicast."""
        while True:
            try:
                msg, origem = self.canal_grupo.receber()
            except ValueError:
                continue
            tipo = msg.get("tipo")
            if tipo == "HEARTBEAT":
                self.estado_membros.registrar_heartbeat(msg["id"], msg.get("sinc", False))
            elif tipo == "REQ":
                threading.Thread(target=self.trata_requisicao, args=(msg, origem), daemon=True).start()
            elif tipo == "REPLICA":
                if msg["lider"] != self.id:
                    self.trata_replica(msg)
            elif tipo == "SYNC_REQ":
                if msg["id"] != self.id:
                    threading.Thread(target=self.trata_sync, args=(msg,), daemon=True).start()

    def thread_unicast(self):
        """Recebe mensagens unicast: ACK das replicas e STATE (sincronizacao)."""
        while True:
            try:
                msg, origem = self.canal_uni.receber()
            except ValueError:
                continue
            if msg.get("tipo") == "ACK":
                with self.cond_ack:
                    if msg["req_id"] in self.acks:
                        self.acks[msg["req_id"]].add(msg["id"])
                        self.log.info(f"ACK recebido de S{msg['id']} para {msg['req_id']}")
                    self.cond_ack.notify_all()
            elif msg.get("tipo") == "STATE":
                self.recebe_estado(msg)

    def recebe_estado(self, msg):
        """Restaura um estado somente se ele nao for anterior ao estado local."""
        with self.lock_estado:
            if self.sincronizado:
                return
            if not self.conta.restaurar(msg):
                self.log.warning(f"ESTADO antigo de S{msg['id']} ignorado: versao={msg['versao']} atual={self.conta.versao}")
                return
            self.sincronizado = True
            self.log.info(
                f"ESTADO recebido de S{msg['id']}: saldo={msg['saldo']} "
                f"versao={msg['versao']} ({len(msg['cache'])} escritas ja aplicadas)"
            )

    # ------------------------------------------------------------ envio
    def envia_grupo(self, msg):
        self.canal_uni.enviar(msg, self.grupo)

    def envia_para(self, msg, ip, porta):
        self.canal_uni.enviar(msg, (ip, porta))

    def resposta_para_cliente(self, req_id, res, origem, replicado_em=None, erro=None):
        """Toda resposta leva o resultado + identificador, IP e porta do servidor."""
        resp = {
            "tipo": "RESPOSTA",
            "req_id": req_id,
            "ok": res["ok"],
            "resultado": res["msg"],
            "saldo": res["saldo"],
            "servidor": {"id": self.id, "ip": self.eu["ip"], "porta": self.eu["porta"]},
        }
        if replicado_em is not None:
            resp["replicado_em"] = sorted(replicado_em)
        if erro is not None:
            resp["erro"] = erro
        self.canal_uni.enviar(resp, origem)

    # ------------------------------------------------------- requisicoes
    def trata_requisicao(self, msg, origem):
        req_id, op, valor = msg["req_id"], msg["op"].upper(), msg.get("valor", 0)
        cli = f"{origem[0]}:{origem[1]}"
        if self.em_inicializacao():
            self.log.info(f"REQ {req_id} {op} de {cli} ignorada: ainda em inicializacao")
            return
        v = self.vivos()
        lider = min(v)
        if lider != self.id:
            self.log.info(f"REQ {req_id} {op} {valor if op in OPS_ESCRITA else ''} de {cli}: lider e S{lider}, nao respondo")
            return

        self.log.info(f"REQ {req_id} {op} {valor if op in OPS_ESCRITA else ''} de {cli}: SOU O LIDER (vivos={sorted(v)})")

        if op in OPS_LEITURA:
            res = self.conta.consulta()
            self.resposta_para_cliente(req_id, res, origem)
            self.log.info(f"RESPOSTA {req_id} -> {cli}: saldo={res['saldo']}")
            return

        if op not in OPS_ESCRITA:
            res = {"ok": False, "msg": f"operacao desconhecida {op}", "saldo": self.conta.saldo}
            self.resposta_para_cliente(req_id, res, origem)
            return

        # ---------------------------- escrita: executa, replica, espera ACKs
        with self.lock_escrita:
            with self.lock_estado:
                res, nova = self.conta.aplica(req_id, op, valor)
                versao = self.conta.versao_requisicao(req_id)
            if nova:
                self.log.info(f"ESCRITA {req_id} executada localmente: {res['msg']}, saldo={res['saldo']}")
            else:
                self.log.info(
                    f"ESCRITA {req_id} ja executada antes (reenvio do cliente); nao executa de novo, saldo={res['saldo']}"
                )

            with self.cond_ack:
                self.acks[req_id] = set()
            replica = {
                "tipo": "REPLICA",
                "req_id": req_id,
                "op": op,
                "valor": valor,
                "lider": self.id,
                "versao": versao,
                "saldo_lider": res["saldo"],
            }
            esperando = self.vivos() - {self.id}
            self.log.info(f"REPLICA {req_id} enviada ao grupo; aguardando ACK de {fmt(esperando)}")
            self.envia_grupo(replica)

            if self.falha_injetada == "lider-antes-de-responder":
                time.sleep(0.5)  # da tempo das replicas executarem e confirmarem
                self.log.critical("FALHA INJETADA: lider para (parada total) antes de responder ao cliente")
                logging.shutdown()
                os._exit(1)

            ultimo_envio = time.time()
            limite = time.time() + self.timeout_escrita
            falha_replicacao = False
            while True:
                with self.cond_ack:
                    confirmados = set(self.acks[req_id])
                    # so espera quem continua vivo: um membro que falhou durante a
                    # escrita sai da lista de vivos pelo heartbeat e deixa de ser esperado
                    faltam = (self.vivos() - {self.id}) & esperando - confirmados
                    descartados = esperando - self.vivos()
                    if not faltam:
                        break
                    self.cond_ack.wait(0.3)
                if time.time() - ultimo_envio > 1.0:  # UDP pode perder pacotes: reenvia
                    self.envia_grupo(replica)
                    ultimo_envio = time.time()
                    self.log.info(f"REPLICA {req_id} reenviada; ainda faltam ACK de {fmt(faltam)}")
                if time.time() > limite:
                    self.log.warning(f"tempo esgotado esperando ACK de {fmt(faltam)}")
                    falha_replicacao = True
                    break
            for i in sorted(descartados):
                self.log.warning(f"S{i} falhou durante a escrita {req_id}; nao espero mais seu ACK")
            with self.cond_ack:
                confirmados = self.acks.pop(req_id)

        if falha_replicacao:
            res_falha = {
                "ok": False,
                "msg": "replicacao nao confirmada por todos os membros sem-falha; resultado desconhecido",
                "saldo": res["saldo"],
            }
            self.resposta_para_cliente(
                req_id,
                res_falha,
                origem,
                replicado_em=confirmados | {self.id},
                erro="REPLICACAO_NAO_CONFIRMADA",
            )
            self.log.warning(
                f"RESPOSTA {req_id} -> {cli}: REPLICACAO_NAO_CONFIRMADA (confirmada em {fmt(confirmados | {self.id})})"
            )
            return

        self.resposta_para_cliente(req_id, res, origem, replicado_em=confirmados | {self.id})
        self.log.info(
            f"RESPOSTA {req_id} -> {cli}: {res['msg']}, saldo={res['saldo']} (replicado em {fmt(confirmados | {self.id})})"
        )

    def trata_replica(self, msg):
        """Aplica somente a proxima versao e confirma duplicados sem regredir."""
        if not self.sincronizado:
            self.log.info(f"REPLICA {msg['req_id']} ignorada: estado ainda nao sincronizado")
            return
        if self.falha_injetada == "replica-durante-escrita":
            self.log.critical(
                f"FALHA INJETADA: REPLICA {msg['req_id']} recebida, replica para (parada total) antes de executar e confirmar"
            )
            logging.shutdown()
            os._exit(1)

        versao = msg["versao"]
        nova = False
        with self.lock_estado:
            if not self.sincronizado:
                return
            if versao <= self.conta.versao:
                self.log.info(
                    f"REPLICA {msg['req_id']} versao {versao} ja aplicada ou superada "
                    f"(atual={self.conta.versao}); ACK sem alterar o estado"
                )
            elif versao > self.conta.versao + 1:
                self.log.warning(
                    f"LACUNA de versoes: REPLICA {msg['req_id']} versao={versao}, "
                    f"esperada={self.conta.versao + 1}; nao aplica nem confirma"
                )
                return
            else:
                res, nova = self.conta.aplica(msg["req_id"], msg["op"], msg["valor"], versao)
                if nova:
                    self.log.info(
                        f"REPLICA {msg['req_id']} de S{msg['lider']}: {res['msg']}, saldo={res['saldo']}, versao={versao}"
                    )
                # A correcao so e permitida na aplicacao da proxima versao;
                # mensagens antigas nunca alteram o saldo atual.
                if self.conta.saldo != msg["saldo_lider"]:
                    self.log.warning(
                        f"INCONSISTENCIA: saldo local {self.conta.saldo} != saldo do lider "
                        f"{msg['saldo_lider']}; adotando o do lider na mesma versao"
                    )
                    with self.conta.lock:
                        self.conta.saldo = msg["saldo_lider"]
        lider = self.membros[msg["lider"]]
        self.envia_para({"tipo": "ACK", "req_id": msg["req_id"], "id": self.id}, lider["ip"], lider["porta"])
        if nova:
            self.log.info(f"ACK enviado a S{msg['lider']} para {msg['req_id']}")

    def trata_sync(self, msg):
        """Um servidor (re)iniciou e pediu o estado. Responde o membro de menor
        ID entre os vivos QUE JA TEM ESTADO, sem contar quem pediu (o novo
        membro pode ter ID menor, mas ainda nao tem estado). Feito sob o lock
        de escrita para nao mandar um estado no meio de uma escrita."""
        # O pedido de estado tambem prova que o processo esta executando.
        # Marca-lo como vivo faz o lider aguardar seu ACK se uma escrita
        # ocorrer depois do snapshot, fechando a corrida de reintegracao.
        self.estado_membros.registrar_heartbeat(msg["id"], False)
        if not self.sincronizado:
            return
        outros = self.vivos() - {msg["id"]}
        candidatos = self.estado_membros.sincronizados(outros) | {self.id}
        if min(candidatos) != self.id:
            return
        with self.lock_escrita, self.lock_estado:
            estado = {"tipo": "STATE", "id": self.id, **self.conta.snapshot()}
            m = self.membros.get(msg["id"])
            if m:
                self.envia_para(estado, m["ip"], m["porta"])
                self.log.info(f"ESTADO enviado a S{msg['id']} (saldo={self.conta.saldo})")

    # ----------------------------------------------------------------- main
    def executa(self):
        self.log.info(
            f"INICIANDO servidor S{self.id} em {self.eu['ip']}:{self.eu['porta']}, "
            f"grupo {self.grupo[0]}:{self.grupo[1]}, heartbeat a cada {self.hb_intervalo}s, "
            f"falha apos {self.timeout}s sem heartbeat"
        )
        for alvo in (self.thread_grupo, self.thread_unicast, self.thread_heartbeat, self.thread_monitor):
            threading.Thread(target=alvo, daemon=True).start()
        # pede o estado atual ao grupo (caso esteja voltando de uma falha)
        while not self.sincronizado:
            self.envia_grupo({"tipo": "SYNC_REQ", "id": self.id})
            time.sleep(0.5)
            self.em_inicializacao()  # marca 'sincronizado' se estiver sozinho no grupo
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass


def fmt(ids):
    return "{" + ", ".join(f"S{i}" for i in sorted(ids)) + "}" if ids else "{}"


def configura_log(meu_id, ip, porta, arquivo):
    fmt_ = logging.Formatter(f"%(asctime)s.%(msecs)03d [S{meu_id} {ip}:{porta}] %(levelname)-7s %(message)s", "%Y-%m-%d %H:%M:%S")
    log = logging.getLogger("servidor")
    log.setLevel(logging.INFO)
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(fmt_)
    log.addHandler(h)
    if arquivo:
        os.makedirs(os.path.dirname(arquivo) or ".", exist_ok=True)
        fh = logging.FileHandler(arquivo, mode="w", encoding="utf-8")
        fh.setFormatter(fmt_)
        log.addHandler(fh)


def main():
    ap = argparse.ArgumentParser(description="Servidor do grupo replicado (TP Redes II)")
    ap.add_argument("--id", type=int, required=True, help="identificador deste servidor")
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--log", default=None, help="arquivo de log (alem da tela)")
    # Injecao de falha usada apenas em dois cenarios de teste, para parar o
    # processo exatamente num ponto do protocolo (dificil de acertar com kill manual).
    ap.add_argument("--falha", choices=["replica-durante-escrita", "lider-antes-de-responder"])
    a = ap.parse_args()
    with open(a.config) as f:
        cfg = json.load(f)
    eu = next(s for s in cfg["servidores"] if s["id"] == a.id)
    configura_log(a.id, eu["ip"], eu["porta"], a.log)
    canal_grupo = abrir_canal_multicast(cfg["grupo"], cfg["porta_grupo"], eu["ip"])
    canal_uni = abrir_canal_unicast(eu["ip"], eu["porta"], eu["ip"])
    Servidor(a.id, cfg, canal_grupo, canal_uni, a.falha).executa()


if __name__ == "__main__":
    main()
