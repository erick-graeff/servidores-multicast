#!/usr/bin/env python3
# =============================================================================
#  TP REDES II 2026 - Roteiro dos cenarios de teste em tres hosts
#  Dupla .................: Eduardo Camargo Neves e Erick Graeff Petzold
#  Funcionalidade ........: Executa os mesmos cenarios de cenarios.py, mas
#                           com cada servidor em um host diferente (iniciado
#                           e morto com kill -9 via ssh) e os clientes na
#                           maquina que roda o roteiro. Os logs vao para uma
#                           pasta da home compartilhada (NFS) do DInf.
#  Ultima modificacao ....: 07/11/2026
# =============================================================================
#
#  Uso (na maquina dos clientes, com acesso ssh sem senha aos hosts):
#     python3 cenarios_lab.py --iface <IP desta maquina> --saida logs/lab
# =============================================================================

import os
import signal
import subprocess

import cenarios
from cenarios import AQUI

HOSTS = {1: "orval", 2: "cpu1", 3: "cpu2"}


def ssh(host, comando, fundo=False, **kw):
    # fundo: o ssh vai para segundo plano (-f) e o comando segue rodando no host
    opcoes = ["-f", "-n"] if fundo else []
    return subprocess.run(["ssh", "-o", "BatchMode=yes", *opcoes, host, comando], **kw)


class ProcessoRemoto:
    """Imita o Popen usado em cenarios.py para um servidor em outro host."""

    def __init__(self, host, padrao):
        self.host, self.padrao = host, padrao
        self.pid = host

    def poll(self):
        r = ssh(self.host, f"pgrep -f '{self.padrao}'", stdout=subprocess.DEVNULL)
        return None if r.returncode == 0 else 1

    def send_signal(self, sinal):
        ssh(self.host, f"pkill -{int(sinal)} -f '{self.padrao}'")

    def wait(self):
        return 0


class CenarioLab(cenarios.Cenario):
    config = os.path.join(AQUI, "config_lab.json")

    def sobe(self, sid, falha=None):
        log = os.path.join(self.pasta, f"servidor_S{sid}.log")
        if os.path.exists(log):
            # servidor reiniciado: guarda o log da execucao anterior
            os.replace(log, os.path.join(self.pasta, f"servidor_S{sid}_execucao1.log"))
        padrao = f"servidor.py --id {sid} --config {self.config}"
        args = f"{padrao} --log {log}" + (f" --falha {falha}" if falha else "")
        # timeout de seguranca: nada fica rodando nos hosts compartilhados
        ssh(
            HOSTS[sid],
            f"cd {AQUI} && exec setsid timeout 600 python3 {args} >/dev/null 2>&1 </dev/null",
            fundo=True,
        )
        self.procs[sid] = ProcessoRemoto(HOSTS[sid], padrao)
        self.nota(f"inicia S{sid} em {HOSTS[sid]}" + (f" com falha injetada '{falha}'" if falha else ""))

    def le_log(self, sid):
        # le no proprio host: pelo NFS, o log ainda aberto por um servidor
        # em outra maquina pode aparecer desatualizado
        log = os.path.join(self.pasta, f"servidor_S{sid}.log")
        return ssh(HOSTS[sid], f"cat {log}", capture_output=True, text=True).stdout

    def mata(self, sid):
        self.nota(f"kill -9 em {HOSTS[sid]} -> S{sid} sofre PARADA TOTAL")
        self.procs[sid].send_signal(signal.SIGKILL)


if __name__ == "__main__":
    cenarios.Cenario = CenarioLab
    cenarios.main()
