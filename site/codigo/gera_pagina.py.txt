#!/usr/bin/env python3
# =============================================================================
#  TP REDES II 2026 - Gerador da pagina de entrega
#  Dupla .................: Eduardo Camargo Neves e Erick Graeff Petzold
#  Funcionalidade ........: Monta a pasta site/ (index.html, relatorio.html,
#                           codigo/*.txt e logs/*.txt) a partir do codigo e
#                           dos logs gerados por cenarios.py e, no
#                           laboratorio, por cenarios_lab.py.
#  Ultima modificacao ....: 07/11/2026
# =============================================================================
import argparse
import html
import json
import os
import re
import shutil

AQUI = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(AQUI, "site")
DUPLA = "Eduardo Camargo Neves e Erick Graeff Petzold"
DATA = "07/11/2026"

CODIGOS = [
    ("servidor.py", "Processo servidor: heartbeat, detecção de falhas, eleição, serviço e replicação"),
    ("cliente.py", "Cliente: envia ao grupo multicast, reenvia com o mesmo req_id se não houver resposta"),
    ("comunicacao.py", "Transporte UDP/JSON e canais multicast e unicast injetáveis"),
    ("conta.py", "Conta bancária: operações, idempotência, versões e snapshots"),
    ("membros.py", "Monitoramento de membros vivos e eleição do menor ID"),
    ("config.json", "Configuração usada nos testes locais (3 servidores)"),
    ("config_lab.json", "Configuração dos 3 hosts do DInf (orval, cpu1 e cpu2)"),
    ("cenarios.py", "Roteiro automático dos 15 cenários de teste (sobe, mata e confere)"),
    ("cenarios_lab.py", "Os mesmos 15 cenários com cada servidor num host diferente, via ssh"),
    ("gera_pagina.py", "Gerador desta página"),
]

RUIDO = ("detectado sem falha", "VIVOS =", "INICIANDO", "nenhum membro vivo", "] cliente em ", "ignorada: ainda em inicializacao")

CSS = """
body{font-family:Georgia,"Times New Roman",serif;font-size:17px;line-height:1.5;color:#111;background:#fff;margin:0}
main{max-width:860px;margin:0 auto;padding:20px 16px 60px}
h1{font-size:26px;margin-bottom:4px}
h2{font-size:21px;margin-top:36px}
h3{font-size:18px;margin-top:24px}
code,pre{font-family:"Courier New",monospace;font-size:14px}
pre{background:#f3f3f3;border:1px solid #ccc;padding:8px;overflow-x:auto}
table{border-collapse:collapse;margin:10px 0}
th,td{border:1px solid #999;padding:4px 8px;text-align:left;vertical-align:top}
th{background:#eee}
.ok{color:green}.bad{color:#b00}
figure{margin:16px 0}figcaption{font-size:15px;font-style:italic}
svg{max-width:100%;height:auto}
.nota{border:1px solid #c90;background:#fff6dd;padding:8px}
.links{font-size:15px}
@media (max-width:640px){table{display:block;overflow-x:auto}}
"""


def pagina(titulo, corpo):
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titulo}</title>
<!-- Dupla: {DUPLA} | Funcionalidade: {titulo} | Ultima modificacao: {DATA} -->
<style>{CSS}</style></head><body><main>
{corpo}
<hr><p class="links">{DUPLA} - {DATA}</p>
</main></body></html>
"""


# ----------------------------------------------------------------- diagramas
SVG_ARQ = """<svg viewBox="0 0 860 330" role="img" aria-label="Arquitetura" font-family="system-ui,sans-serif" font-size="14">
<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#5b6475"/></marker>
<marker id="b" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#000"/></marker></defs>
<rect x="20" y="120" width="170" height="80" rx="8" fill="none" stroke="#5b6475"/>
<text x="105" y="152" text-anchor="middle" font-weight="600">Cliente</text>
<text x="105" y="172" text-anchor="middle" font-size="12" fill="#5b6475">envia ao endereço</text>
<text x="105" y="188" text-anchor="middle" font-size="12" fill="#5b6475">do grupo</text>
<rect x="250" y="20" width="590" height="290" rx="10" fill="none" stroke="#5b6475" stroke-dasharray="5 4"/>
<text x="268" y="46" font-weight="600">Grupo multicast 224.1.1.1:5007</text>
<rect x="270" y="90" width="170" height="110" rx="8" fill="none" stroke="#000" stroke-width="2"/>
<text x="355" y="120" text-anchor="middle" font-weight="600">S1 (líder)</text>
<text x="355" y="142" text-anchor="middle" font-size="12">menor ID sem falha</text>
<text x="355" y="160" text-anchor="middle" font-size="12">responde ao cliente</text>
<text x="355" y="178" text-anchor="middle" font-size="12">coordena as escritas</text>
<rect x="465" y="90" width="170" height="110" rx="8" fill="none" stroke="#5b6475"/>
<text x="550" y="120" text-anchor="middle" font-weight="600">S2 (réplica)</text>
<text x="550" y="142" text-anchor="middle" font-size="12" fill="#5b6475">recebe a requisição</text>
<text x="550" y="160" text-anchor="middle" font-size="12" fill="#5b6475">e não responde;</text>
<text x="550" y="178" text-anchor="middle" font-size="12" fill="#5b6475">executa REPLICA + ACK</text>
<rect x="660" y="90" width="170" height="110" rx="8" fill="none" stroke="#5b6475"/>
<text x="745" y="120" text-anchor="middle" font-weight="600">S3 (réplica)</text>
<text x="745" y="142" text-anchor="middle" font-size="12" fill="#5b6475">recebe a requisição</text>
<text x="745" y="160" text-anchor="middle" font-size="12" fill="#5b6475">e não responde;</text>
<text x="745" y="178" text-anchor="middle" font-size="12" fill="#5b6475">executa REPLICA + ACK</text>
<rect x="270" y="235" width="560" height="54" rx="8" fill="#fff" stroke="#5b6475"/>
<text x="550" y="258" text-anchor="middle" font-size="13">HEARTBEAT por multicast a cada 0,5 s, de todos para todos</text>
<text x="550" y="277" text-anchor="middle" font-size="12" fill="#5b6475">1,5 s sem heartbeat de um membro = falha (parada total)</text>
<path d="M190 140H268" stroke="#5b6475" stroke-width="1.5" fill="none" marker-end="url(#a)"/>
<text x="229" y="130" text-anchor="middle" font-size="12" fill="#5b6475">REQ</text>
<path d="M270 185H192" stroke="#000" stroke-width="1.5" fill="none" marker-end="url(#b)"/>
<text x="229" y="205" text-anchor="middle" font-size="12" fill="#000">RESPOSTA</text>
<text x="229" y="221" text-anchor="middle" font-size="11" fill="#000">(unicast)</text>
</svg>"""

SVG_SEQ = """<svg viewBox="0 0 860 470" role="img" aria-label="Sequência de uma escrita" font-family="system-ui,sans-serif" font-size="13">
<defs><marker id="s" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#1d2433"/></marker></defs>
<g font-weight="600" text-anchor="middle">
<rect x="40" y="16" width="120" height="34" rx="6" fill="#fff" stroke="#5b6475"/><text x="100" y="38">Cliente</text>
<rect x="260" y="16" width="120" height="34" rx="6" fill="none" stroke="#000"/><text x="320" y="38">S1 (líder)</text>
<rect x="480" y="16" width="120" height="34" rx="6" fill="#fff" stroke="#5b6475"/><text x="540" y="38">S2</text>
<rect x="680" y="16" width="120" height="34" rx="6" fill="#fff" stroke="#5b6475"/><text x="740" y="38">S3</text></g>
<g stroke="#b8bfcc" stroke-dasharray="4 4"><path d="M100 50V450"/><path d="M320 50V450"/><path d="M540 50V450"/><path d="M740 50V450"/></g>
<g stroke="#1d2433" stroke-width="1.4" fill="none">
<path d="M100 90H318" marker-end="url(#s)"/><path d="M100 90H538" marker-end="url(#s)" stroke-dasharray="2 3"/><path d="M100 90H738" marker-end="url(#s)" stroke-dasharray="2 3"/>
<path d="M320 190H538" marker-end="url(#s)"/><path d="M320 190H738" marker-end="url(#s)"/>
<path d="M540 270H322" marker-end="url(#s)"/><path d="M740 300H322" marker-end="url(#s)"/>
<path d="M320 400H102" marker-end="url(#s)" stroke="#000"/></g>
<text x="108" y="76">1. REQ {req_id, DEPOSITO, 100} → grupo multicast</text>
<text x="560" y="120" fill="#5b6475">S2 e S3 também recebem:</text>
<text x="560" y="136" fill="#5b6475">"líder é S1, não respondo"</text>
<rect x="250" y="130" width="140" height="34" rx="5" fill="#fff" stroke="#000"/>
<text x="320" y="152" text-anchor="middle">2. executa: saldo 100</text>
<text x="335" y="176">3. REPLICA {req_id, op, valor, saldo_lider} → grupo</text>
<rect x="470" y="212" width="140" height="30" rx="5" fill="#fff" stroke="#5b6475"/><text x="540" y="232" text-anchor="middle">executa: saldo 100</text>
<rect x="670" y="212" width="140" height="30" rx="5" fill="#fff" stroke="#5b6475"/><text x="740" y="232" text-anchor="middle">executa: saldo 100</text>
<text x="430" y="259" text-anchor="middle">4. ACK (unicast)</text>
<text x="640" y="289" text-anchor="middle">4. ACK (unicast)</text>
<rect x="225" y="330" width="190" height="44" rx="5" fill="#fff" stroke="#000"/>
<text x="320" y="349" text-anchor="middle">5. tem ACK de todos os</text><text x="320" y="366" text-anchor="middle">membros sem falha?</text>
<text x="108" y="388" fill="#000">6. RESPOSTA {saldo 100, S1, IP, porta, replicado em [S1,S2,S3]}</text>
<rect x="0" y="424" width="860" height="40" fill="#fff"/><text x="430" y="446" text-anchor="middle" font-size="12" fill="#5b6475">Se uma réplica falha no meio, ela sai da lista de vivos (heartbeat) e o líder deixa de esperar o ACK dela.</text>
</svg>"""

SVG_FAILOVER = """<svg viewBox="0 0 860 230" role="img" aria-label="Linha do tempo da troca de líder" font-family="system-ui,sans-serif" font-size="13">
<defs><marker id="f" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#5b6475"/></marker></defs>
<g stroke="#e3e6ec"><path d="M80 40V180"/><path d="M260 40V180"/><path d="M440 40V180"/><path d="M620 40V180"/><path d="M800 40V180"/></g>
<path d="M60 180H830" stroke="#5b6475" stroke-width="1.4" marker-end="url(#f)"/>
<g font-size="12" fill="#5b6475" text-anchor="middle"><text x="80" y="200">t = 0</text><text x="260" y="200">0,5 s</text><text x="440" y="200">1,0 s</text><text x="620" y="200">1,5 s</text><text x="800" y="200">2,0 s</text></g>
<text x="20" y="74" font-weight="600">S1</text><text x="20" y="144" font-weight="600">S2</text>
<circle cx="80" cy="70" r="6" fill="#000"/>
<text x="80" y="52" text-anchor="middle" font-size="12" fill="#000">último heartbeat</text>
<path d="M110 58V82" stroke="#000" stroke-width="2.5"/>
<text x="120" y="96" font-size="12" fill="#000" font-weight="600">kill -9 (parada total)</text>
<path d="M86 118H616" stroke="#5b6475" stroke-dasharray="5 4" marker-end="url(#f)"/>
<text x="350" y="110" text-anchor="middle" font-size="12" fill="#5b6475">1,5 s sem heartbeat de S1; o cliente reenvia a mesma REQ a cada 0,5 s</text>
<rect x="620" y="126" width="236" height="40" rx="6" fill="none" stroke="#000"/>
<text x="738" y="143" text-anchor="middle" font-size="12">S2 detecta a falha e assume;</text>
<text x="738" y="159" text-anchor="middle" font-size="11.5">a REQ guardada é atendida em seguida</text>
</svg>"""


def trecho(caminho, max_linhas=60):
    with open(caminho, encoding="utf-8") as f:
        linhas = [l.rstrip("\n")[11:] for l in f if not any(r in l for r in RUIDO)]
    if len(linhas) > max_linhas:
        linhas = linhas[:max_linhas] + [f"... ({len(linhas) - max_linhas} linhas a mais no log completo)"]
    return html.escape("\n".join(linhas))


def secao_lab(diretorio_lab):
    """Copia os logs dos 3 hosts para site/logs_lab e monta a secao 8."""
    with open(os.path.join(diretorio_lab, "resumo.json"), encoding="utf-8") as f:
        resumo = json.load(f)
    with open(os.path.join(AQUI, "config_lab.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    linhas = []
    for r in resumo:
        pasta = f"cenario{r['num']:02d}"
        dest = os.path.join(SITE, "logs_lab", pasta)
        os.makedirs(dest)
        arquivos = sorted(os.listdir(os.path.join(diretorio_lab, pasta)))
        for nome in arquivos:
            shutil.copy(os.path.join(diretorio_lab, pasta, nome), os.path.join(dest, nome + ".txt"))
        ordem = ["linha_do_tempo.log", "roteiro.log", "cliente.log"]
        arquivos.sort(key=lambda n: (ordem.index(n) if n in ordem else 9, n))
        links = ", ".join(f'<a href="logs_lab/{pasta}/{n}.txt">{n}</a>' for n in arquivos)
        n_ok = sum(c["ok"] for c in r["checks"])
        linhas.append(
            f"<tr><td>{r['num']}</td><td>{html.escape(TITULOS.get(r['num'], r['titulo']))}</td>"
            f"<td>{n_ok}/{len(r['checks'])}</td>"
            f'<td class="{"ok" if r["ok"] else "bad"}">{"passou" if r["ok"] else "falhou"}</td>'
            f'<td class="links">{links}</td></tr>'
        )
    total = sum(len(r["checks"]) for r in resumo)
    total_ok = sum(c["ok"] for r in resumo for c in r["checks"])
    hosts = {1: "orval", 2: "cpu1", 3: "cpu2"}
    tab_hosts = "".join(
        f"<tr><td>S{s['id']}</td><td>{hosts.get(s['id'], '')}</td><td><code>{s['ip']}:{s['porta']}</code></td></tr>"
        for s in cfg["servidores"]
    )
    return f"""<p>Rodamos os mesmos {len(resumo)} cenários da seção 7 com cada servidor numa máquina diferente do
DInf. As três máquinas estão na mesma rede (10.17.110.0/24). O cliente e o script de testes rodaram numa
quarta máquina, o macalan. O <code>cenarios_lab.py</code> sobe cada servidor na sua máquina por ssh e,
nos cenários de falha, dá <code>kill -9</code> no processo lá mesmo. Usamos o grupo
<code>{cfg['grupo']}:{cfg['porta_grupo']}</code> em vez do padrão, porque as máquinas são usadas por outros
alunos e poderia ter outra dupla usando o mesmo grupo.</p>
<table><tr><th>Servidor</th><th>Máquina</th><th>IP:porta</th></tr>{tab_hosts}
<tr><td>clientes</td><td>macalan</td><td><code>10.17.110.6</code></td></tr></table>
<p>Resultado: {len(resumo)} cenários, {total_ok} de {total} verificações certas. Os relógios das máquinas
estavam sincronizados (NTP), então dá para juntar os logs das três máquinas numa linha do tempo só.</p>
<p>Um problema que tivemos: os logs ficam na home, que é compartilhada por NFS, e o macalan às vezes lia uma
versão desatualizada do log de um servidor que ainda estava rodando em outra máquina. Por isso, no lab, o
script lê o log pelo próprio host do servidor (com ssh) na hora de conferir o saldo.</p>
<table><tr><th>#</th><th>Cenário</th><th>Verificações</th><th>Resultado</th><th>Logs</th></tr>{"".join(linhas)}</table>
<details><summary>Trecho da linha do tempo do cenário 10 (S1 cai, S2 assume, S1 volta e vira líder de novo)</summary>
<pre>{trecho(os.path.join(diretorio_lab, "cenario10", "linha_do_tempo.log"))}</pre></details>"""


AVISO_LAB = """<div class="nota"><b>[A COMPLETAR PELA DUPLA]</b> Os logs da seção 7 foram gerados numa única máquina
(3 processos em portas diferentes, multicast pela interface local). O enunciado exige logs com 3 servidores
em hosts diferentes. Rodem os cenários principais no laboratório com o <code>config_lab.json</code>
(preenchido com os IPs das máquinas), coloquem os logs em <code>logs/lab/</code> e substituam este aviso
por uma tabela com os resultados e os links.</div>"""


def gera(diretorio_logs=None, diretorio_lab=None):
    logs = os.path.abspath(diretorio_logs or os.path.join(AQUI, "logs"))
    if os.path.isdir(SITE):
        shutil.rmtree(SITE)
    os.makedirs(os.path.join(SITE, "codigo"))
    os.makedirs(os.path.join(SITE, "logs"))

    for nome, _ in CODIGOS:
        destino = os.path.join(SITE, "codigo", nome + ".txt")
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        shutil.copy(os.path.join(AQUI, nome), destino)

    with open(os.path.join(logs, "resumo.json"), encoding="utf-8") as f:
        resumo = json.load(f)
    for r in resumo:
        r["titulo"] = TITULOS.get(r["num"], r["titulo"])
        for c in r["checks"]:
            c["req"] = c["req"].replace("estado da replica", "estado da réplica")

    cards = []
    linhas_tab = []
    for r in resumo:
        pasta = f"cenario{r['num']:02d}"
        orig = os.path.join(logs, pasta)
        dest = os.path.join(SITE, "logs", pasta)
        os.makedirs(dest)
        arquivos = []
        for nome in sorted(os.listdir(orig)):
            shutil.copy(os.path.join(orig, nome), os.path.join(dest, nome + ".txt"))
            arquivos.append(nome)
        ordem = ["linha_do_tempo.log", "roteiro.log", "cliente.log"]
        arquivos.sort(key=lambda n: (ordem.index(n) if n in ordem else 9, n))
        links = ", ".join(f'<a href="logs/{pasta}/{n}.txt">{n}</a>' for n in arquivos)
        checks = "".join(
            f"<tr><td>{html.escape(c['req'])}</td><td>{html.escape(c['esperado'])}</td>"
            f"<td>{html.escape(c['obtido'])}</td>"
            f'<td class="{"ok" if c["ok"] else "bad"}">{"OK" if c["ok"] else "ERRO"}</td></tr>'
            for c in r["checks"]
        )
        n_ok = sum(c["ok"] for c in r["checks"])
        linhas_tab.append(
            f'<tr><td>{r["num"]}</td><td><a href="#c{r["num"]}">{html.escape(r["titulo"])}</a></td>'
            f"<td>{n_ok}/{len(r['checks'])}</td>"
            f'<td class="{"ok" if r["ok"] else "bad"}">{"passou" if r["ok"] else "falhou"}</td></tr>'
        )
        cards.append(f"""<h3 id="c{r["num"]}">Cenário {r["num"]}: {html.escape(r["titulo"])}</h3>
<p>{DESCR.get(r["num"], "")}</p>
<table><tr><th>Requisição / verificação</th><th>Esperado</th><th>Obtido</th><th></th></tr>{checks}</table>
<details><summary>Trecho da linha do tempo</summary>
<pre>{trecho(os.path.join(orig, "linha_do_tempo.log"))}</pre></details>
<p class="links">Logs: {links}</p>""")

    total = sum(len(r["checks"]) for r in resumo)
    total_ok = sum(c["ok"] for r in resumo for c in r["checks"])

    codigos_html = "".join(f'<tr><td><a href="codigo/{n}.txt"><code>{n}.txt</code></a></td><td>{d}</td></tr>' for n, d in CODIGOS)

    rel = f"""
<h1>Servidor tolerante a falhas com grupo multicast</h1>
<p>Trabalho Prático de Redes II, 2026<br>Dupla: {DUPLA}</p>

<p>Seções: <a href="#visao">1. Visão geral</a> | <a href="#servico">2. Serviço</a> |
<a href="#arq">3. Arquitetura</a> | <a href="#proto">4. Protocolo</a> | <a href="#decisoes">5. Decisões</a> |
<a href="#exec">6. Como executar</a> | <a href="#testes">7. Testes</a> | <a href="#lab">8. Execução em 3 hosts</a> |
<a href="#limites">9. Limitações</a></p>

<h2 id="visao">1. Visão geral</h2>
<p>O servidor do trabalho é na verdade um grupo de N processos (S1, S2, ..., SN) que entram no mesmo grupo
multicast. Cada um conhece o id, o IP e a porta dos outros, que ficam no <code>config.json</code>.
O cliente manda a requisição para o endereço do grupo, então todos os servidores recebem, mas só quem é o líder
responde. O líder é o servidor sem falha com o menor id. Na resposta vai o resultado e também o id, o IP e a
porta de quem atendeu.</p>
<p>Para saber quem está vivo, cada servidor manda um heartbeat no grupo a cada 0,5 s. Se um servidor fica 1,5 s
sem mandar heartbeat, os outros consideram que ele falhou. Só tratamos falha por parada total; nos testes
matamos os processos com <code>kill -9</code>. Como a troca de líder leva por volta de 1,5 s, ela termina
antes do cliente desistir de esperar (ver cenários 3 e 11).</p>
<p>Fizemos em Python 3 usando só a biblioteca padrão (<code>socket</code>, <code>threading</code> e <code>json</code>).
Rodamos {len(resumo)} cenários de teste e as {total} verificações deram certo ({total_ok} de {total}).</p>

<h2 id="servico">2. Serviço: conta bancária</h2>
<table><tr><th>Operação</th><th>Tipo</th><th>O que faz</th></tr>
<tr><td><code>SALDO</code></td><td>consulta</td><td>o líder devolve o saldo</td></tr>
<tr><td><code>DEPOSITO v</code></td><td>alteração</td><td>soma v ao saldo e replica nos outros</td></tr>
<tr><td><code>SAQUE v</code></td><td>alteração</td><td>tira v do saldo; se não tiver saldo suficiente, é recusado</td></tr></table>
<p>Escolhemos conta bancária porque se uma escrita for executada duas vezes dá para ver na hora
(o depósito aparece em dobro), o que ajuda a mostrar nos testes que isso não acontece.</p>

<h2 id="arq">3. Arquitetura</h2>
<figure>{SVG_ARQ}<figcaption>Figura 1: todos recebem a requisição pelo grupo, mas só o líder responde (por unicast, para o IP e porta do cliente).</figcaption></figure>
<p>Dividimos o código assim:</p>
<ul>
<li><code>comunicacao.py</code>: sockets UDP, envio/recebimento em JSON e entrada no grupo multicast;</li>
<li><code>conta.py</code>: saldo, cache de requisições já feitas, versões e cópia do estado;</li>
<li><code>membros.py</code>: guarda os heartbeats recebidos e calcula quem está vivo e quem é o líder;</li>
<li><code>servidor.py</code>: o protocolo em si (requisições, replicação, sincronização);</li>
<li><code>cliente.py</code>: manda as requisições e reenvia se não vier resposta.</li>
</ul>
<p>Cada servidor roda quatro threads:</p>
<table><tr><th>Thread</th><th>Função</th></tr>
<tr><td>heartbeat</td><td>manda <code>HEARTBEAT</code> no grupo a cada 0,5 s</td></tr>
<tr><td>monitor</td><td>a cada 0,2 s recalcula os vivos e o líder e escreve no log quando algo muda</td></tr>
<tr><td>grupo</td><td>recebe o que chega pelo multicast: <code>HEARTBEAT</code>, <code>REQ</code>, <code>REPLICA</code> e <code>SYNC_REQ</code></td></tr>
<tr><td>unicast</td><td>recebe na porta do servidor os <code>ACK</code> e o <code>STATE</code></td></tr></table>
<p>A eleição não usa mensagens próprias. Como todos recebem os mesmos heartbeats, cada servidor calcula
<code>lider = min(vivos)</code> e, quando chega uma requisição, vê se ele é o líder ou não.</p>

<h2 id="proto">4. Protocolo</h2>
<table><tr><th>Mensagem</th><th>Como vai</th><th>Campos</th><th>Para que serve</th></tr>
<tr><td>HEARTBEAT</td><td>multicast</td><td>id, sinc</td><td>avisa que está vivo e se já tem o estado da conta</td></tr>
<tr><td>REQ</td><td>multicast</td><td>req_id, op, valor</td><td>requisição do cliente</td></tr>
<tr><td>REPLICA</td><td>multicast</td><td>req_id, op, valor, lider, versao, saldo_lider</td><td>líder manda as réplicas executarem a escrita</td></tr>
<tr><td>ACK</td><td>unicast para o líder</td><td>req_id, id</td><td>réplica avisa que executou</td></tr>
<tr><td>RESPOSTA</td><td>unicast para o cliente</td><td>req_id, ok, resultado, saldo, servidor{{id, ip, porta}}, replicado_em</td><td>resposta do líder</td></tr>
<tr><td>SYNC_REQ</td><td>multicast</td><td>id</td><td>servidor que voltou pede o estado</td></tr>
<tr><td>STATE</td><td>unicast</td><td>saldo, cache, versao, versoes</td><td>estado atual mandado para quem pediu</td></tr></table>

<h3>4.1 Escrita</h3>
<figure>{SVG_SEQ}<figcaption>Figura 2: o líder executa, manda a REPLICA, espera os ACKs e só depois responde.</figcaption></figure>
<ol><li>O cliente manda <code>REQ</code> para o grupo, com um <code>req_id</code> único.</li>
<li>O líder executa a operação.</li>
<li>O líder manda <code>REPLICA</code> para o grupo.</li>
<li>Cada réplica executa e manda <code>ACK</code> para o líder.</li>
<li>O líder espera o ACK de todos que ainda estão vivos. Como UDP pode perder pacote, ele reenvia a REPLICA a cada 1 s.
Se uma réplica morre no meio, ela sai da lista de vivos e o líder para de esperar por ela.</li>
<li>O líder responde ao cliente dizendo em quais servidores a escrita ficou.</li></ol>
<p>Consultas o líder responde direto. As escritas passam por um lock no líder, uma de cada vez, e por isso todas
as réplicas aplicam na mesma ordem.</p>

<h3>4.2 Falha do líder</h3>
<figure>{SVG_FAILOVER}<figcaption>Figura 3: com heartbeat de 0,5 s e limite de 1,5 s, S2 assume cerca de 1,5 s depois da queda de S1.</figcaption></figure>
<p>Entre a morte do líder e a detecção, ninguém responde: o líder está morto e os outros ainda acham que são
réplicas. Para não perder as requisições que chegam nesse intervalo, as réplicas guardam a requisição por
um tempo (timeout + 1 s). Se uma delas virar líder, atende na hora o que guardou. Além disso o cliente reenvia a
mesma requisição (mesmo <code>req_id</code>) a cada 0,5 s. Nos testes a resposta chegou uns 2 s depois da queda
do líder.</p>

<h2 id="decisoes">5. Decisões que tomamos</h2>
<ul>
<li>O cliente reenvia sempre com o mesmo <code>req_id</code>. Ele espera no total 12 s (6 tentativas de 2 s) e
reenvia a cada 0,5 s. Isso cobre o tempo da troca de líder e também perda de pacote.</li>
<li>As réplicas guardam a requisição durante a troca de líder (explicado na seção 4.2). Quando o líder está
normal, essa cópia só expira.</li>
<li>Para não executar a mesma escrita duas vezes, cada servidor guarda um cache <code>req_id → resultado</code>.
Se o líder morre depois de replicar e antes de responder, o novo líder já tem aquela escrita no cache e
só devolve o resultado (cenário 9).</li>
<li>Quando um servidor acabou de subir ele ainda não sabe quem está vivo, então nos primeiros 1,5 s ele não
atende cliente. Senão ele poderia achar que é o líder.</li>
<li>Quando um servidor volta de uma falha, ele manda <code>SYNC_REQ</code> e o servidor vivo de menor id que já tem
estado responde com <code>STATE</code>. Só depois disso ele pode virar líder (cenário 10). O campo <code>sinc</code>
do heartbeat diz quem já tem estado; se ninguém tem, todos começam com saldo 0.</li>
<li>Cada escrita tem um número de versão. A réplica só aplica a próxima versão; se receber uma versão velha ela
manda ACK sem mudar nada. Assim uma REPLICA atrasada não volta o saldo para trás.</li>
<li>Se alguma réplica viva não confirmar em 8 s, o líder responde com <code>ok=false</code> e
<code>REPLICACAO_NAO_CONFIRMADA</code>. Não respondemos sucesso sem ter os ACKs.</li>
<li>Réplica que ainda não recebeu o estado não aplica escritas, e um <code>STATE</code> mais velho que o estado
atual é ignorado. Os cenários 13 e 14 testam escrita enquanto S2 ou S3 estão voltando.</li>
<li>Na primeira versão tinha um erro: o servidor que voltava de uma falha virava líder com saldo 0. Achamos pelo
cenário 10 e corrigimos com a sincronização acima.</li>
</ul>

<h2 id="exec">6. Como executar</h2>
<pre># um servidor em cada host (os IPs ficam no arquivo de config)
python3 servidor.py --id 1 --config config_lab.json --log logs/s1.log
python3 servidor.py --id 2 --config config_lab.json --log logs/s2.log
python3 servidor.py --id 3 --config config_lab.json --log logs/s3.log

# cliente, em qualquer máquina da mesma rede (--iface = IP dessa máquina)
python3 cliente.py SALDO --config config_lab.json --iface 10.17.110.6
python3 cliente.py DEPOSITO 100 --config config_lab.json --iface 10.17.110.6
python3 cliente.py --config config_lab.json --iface 10.17.110.6    # modo interativo

# derrubar um servidor (parada total)
kill -9 PID

# cenários numa máquina só (3 processos em 127.0.0.1)
python3 cenarios.py --saida logs/pos_correcoes

# cenários nos 3 hosts (rodado no macalan, com ssh para orval, cpu1 e cpu2)
python3 cenarios_lab.py --iface 10.17.110.6 --saida logs/lab

# gerar esta página
python3 gera_pagina.py --logs logs/pos_correcoes --lab logs/lab</pre>
<p>Código fonte:</p>
<table><tr><th>Arquivo</th><th>Conteúdo</th></tr>{codigos_html}</table>

<h2 id="testes">7. Testes</h2>
<p>Para testar fizemos o <code>cenarios.py</code>, que usa UDP e multicast de verdade. Em cada cenário ele sobe os
servidores, manda requisições com o cliente, mata processos com <code>kill -9</code> e confere qual servidor
respondeu e qual o saldo. No final confere se o saldo é o mesmo em todas as réplicas vivas. Para cada cenário
ficam os logs de cada processo, o roteiro do que foi feito e uma linha do tempo com todos os logs juntos em ordem
de horário.</p>
<p>Nos cenários 8 e 9 quem faz o processo parar é ele mesmo (<code>os._exit</code>, com a opção <code>--falha</code>),
porque precisávamos que ele parasse num ponto exato do protocolo e com <code>kill</code> na mão não dá para
acertar o momento. Para os outros processos é igual a uma parada total.</p>
<p>Esta seção mostra a execução numa máquina só. A execução nos 3 hosts está na <a href="#lab">seção 8</a>.</p>
<table><tr><th>#</th><th>Cenário</th><th>Verificações</th><th>Resultado</th></tr>{"".join(linhas_tab)}</table>
{"".join(cards)}

<h2 id="lab">8. Execução em 3 hosts diferentes</h2>
{secao_lab(diretorio_lab) if diretorio_lab else AVISO_LAB}

<h2 id="limites">9. Limitações</h2>
<ul>
<li>Só tratamos parada total, como pede o enunciado. Se a rede se dividir, cada lado vai eleger um líder.</li>
<li>Se heartbeats se perderem, por um instante dois servidores podem achar que são líder. O cliente usa a
primeira resposta e descarta a outra pelo <code>req_id</code>.</li>
<li>O saldo fica só na memória. Se todos os servidores caírem, o estado se perde (cenário 12).</li>
<li>Se der o timeout de 8 s da replicação, o cliente recebe erro, mas a escrita pode ter sido aplicada no líder e
em parte das réplicas.</li>
<li>Se uma réplica perder várias REPLICA seguidas e ficar com um buraco nas versões, ela para de confirmar.
Não fizemos ressincronização automática para isso; é preciso reiniciar o processo.</li>
<li>O multicast tem TTL 1, então todas as máquinas precisam estar na mesma rede local.</li>
</ul>
"""
    with open(os.path.join(SITE, "relatorio.html"), "w", encoding="utf-8") as f:
        f.write(pagina("Relatório - TP Redes II 2026", rel))

    idx = f"""
<h1>TP Redes II 2026</h1>
<p>Servidor tolerante a falhas com grupo multicast<br>Dupla: {DUPLA}</p>
<ul>
<li><a href="relatorio.html">Relatório</a></li>
{'<li><a href="relatorio.html#lab">Execução em 3 hosts diferentes (orval, cpu1 e cpu2)</a></li>' if diretorio_lab else ''}
</ul>
<h2>Código fonte</h2>
<table>{codigos_html}</table>
<h2>Logs</h2>
<ul>
{"".join(f'<li><a href="relatorio.html#c{r["num"]}">Cenário {r["num"]}</a>: {html.escape(r["titulo"])} (<a href="logs/cenario{r["num"]:02d}/linha_do_tempo.log.txt">linha do tempo</a>)</li>' for r in resumo)}
</ul>
"""
    with open(os.path.join(SITE, "index.html"), "w", encoding="utf-8") as f:
        f.write(pagina("TP Redes II 2026", idx))
    print("pagina gerada em", SITE)


TITULOS = {
    1: "Todos sem falha: consultas e alterações atendidas por S1",
    2: "Falha do líder S1: S2 assume e mantém o estado",
    3: "Requisição enviada logo após a falha do líder (antes da detecção)",
    4: "Falha de uma réplica (S2): S1 continua líder e não espera S2",
    5: "Falhas de S1 e S2: S3 atende sozinho",
    6: "Falhas de S1 e S3: S2 atende sozinho",
    7: "Falhas de S2 e S3: S1 atende sozinho",
    8: "Réplica S3 para no meio de uma escrita",
    9: "Líder para depois de replicar e antes de responder (sem execução dupla)",
    10: "S1 falha, S2 assume, S1 volta, recebe o estado e reassume",
    11: "Cliente enviando escritas enquanto o líder é morto",
    12: "Todos os servidores falhos: cliente fica sem resposta",
    13: "S2 volta e recebe escrita durante a sincronização",
    14: "S3 volta e recebe escrita durante a sincronização",
    15: "Três clientes concorrentes mantêm as réplicas consistentes",
}

DESCR = {
    1: "Os três servidores estão sem falha. S1, de menor ID, responde a tudo. As escritas são replicadas em S1, S2 e S3. O saque maior que o saldo é recusado, e o saldo não muda.",
    2: "Depois de um depósito, S1 é morto. S2 e S3 detectam a falha pelo heartbeat, S2 passa a ser o líder, mantém o saldo de 100 e atende às novas requisições.",
    3: "O cliente envia a requisição logo após a morte de S1, antes de a falha ser detectada. Na hora ninguém atende, mas S2 e S3 guardam a requisição. Em até 1,5 s a falha é detectada, S2 vira líder e atende o que guardou. A resposta chega ao cliente em uns 2 s.",
    4: "Uma réplica (S2) é morta. S1 continua líder e, nas escritas, espera apenas o ACK de S3.",
    5: "S1 e S2 são mortos. S3 é o único sem falha, vira líder e atende sozinho com o saldo correto.",
    6: "S1 e S3 são mortos. S2 atende sozinho.",
    7: "S2 e S3 são mortos. S1 continua líder e completa as escritas sem esperar ACK.",
    8: "S3 para no instante em que recebe a REPLICA, sem executar nem confirmar. S1 detecta a falha pelo heartbeat, deixa de esperar o ACK de S3 e responde ao cliente.",
    9: "S1 executa e replica um depósito de 100 e para antes de responder. O cliente reenvia o mesmo req_id, S2 assume e reconhece a escrita já executada. O saldo fica em 100, e não 200.",
    10: "S1 é morto e S2 assume. Depois S1 é reiniciado, pede o estado ao grupo, recebe o saldo de S2 e volta a ser o líder por ter o menor ID, com o saldo correto.",
    11: "Um cliente faz 6 depósitos, um por segundo, e S1 é morto durante a sequência. O depósito que estava em andamento acaba sendo atendido por S2. Nenhum se perde nem é contado duas vezes, e o saldo final é 60.",
    12: "Todos os servidores são mortos. O cliente fica reenviando por 12 s e no fim avisa que nenhum servidor respondeu.",
    13: "Depois de duas escritas sem S2, ele é reiniciado e uma terceira escrita ocorre durante sua sincronização. O saldo final é 175 em S1, S2 e S3.",
    14: "Igual ao 13, mas com S3. Todas as réplicas terminam com saldo 175.",
    15: "Três clientes fazem 5 depósitos de 10 ao mesmo tempo. S1 faz uma escrita por vez e o saldo final é 150 em todos os servidores.",
}

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Gera a página HTML do TP")
    ap.add_argument("--logs", default=os.path.join(AQUI, "logs"), help="diretório que contém resumo.json e os cenários")
    ap.add_argument("--lab", default=None, help="diretório com os logs dos 3 hosts (resumo.json e cenários)")
    args = ap.parse_args()
    gera(args.logs, args.lab)
