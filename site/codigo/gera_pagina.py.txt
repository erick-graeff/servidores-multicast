#!/usr/bin/env python3
# =============================================================================
#  TP REDES II 2026 - Gerador da pagina de entrega
#  Dupla .................: Eduardo Camargo Neves e [NOME DO(A) COLEGA]
#  Funcionalidade ........: Monta a pasta site/ (index.html, relatorio.html,
#                           codigo/*.txt e logs/*.txt) a partir do codigo e
#                           dos logs gerados por cenarios.py.
#  Ultima modificacao ....: 02/11/2026
# =============================================================================
import html
import json
import os
import re
import shutil

AQUI = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(AQUI, "site")
DUPLA = "Eduardo Camargo Neves e [NOME DO(A) COLEGA]"
DATA = "02/11/2026"

CODIGOS = [
    ("servidor.py", "Processo servidor: heartbeat, detecção de falhas, eleição, serviço e replicação"),
    ("cliente.py", "Cliente: envia ao grupo multicast, reenvia com o mesmo req_id se não houver resposta"),
    ("config.json", "Configuração usada nos testes locais (3 servidores)"),
    ("config_lab.json", "Modelo de configuração para 3 hosts diferentes no laboratório"),
    ("cenarios.py", "Roteiro automático dos 12 cenários de teste (sobe, mata e confere)"),
    ("gera_pagina.py", "Gerador desta página"),
]

RUIDO = ("detectado sem falha", "VIVOS =", "INICIANDO", "nenhum membro vivo", "] cliente em ",
         "ignorada: ainda em inicializacao")

CSS = """
:root{--fg:#1d2433;--muted:#5b6475;--line:#d9dde5;--bg:#fff;--soft:#f4f6f9;--acc:#1f5fbf;--ok:#1d7a3e;--bad:#b42318}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.6 "Source Sans 3",system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:920px;margin:0 auto;padding:40px 20px 80px}
h1{font-size:2rem;line-height:1.2;margin:0 0 6px}
h2{font-size:1.4rem;margin:48px 0 12px;padding-top:12px;border-top:1px solid var(--line)}
h3{font-size:1.1rem;margin:28px 0 8px}
.sub{color:var(--muted);margin:0 0 24px}
a{color:var(--acc)}
code{font-family:"JetBrains Mono",ui-monospace,Consolas,monospace;font-size:.88em;background:var(--soft);padding:1px 5px;border-radius:4px}
pre{font-family:"JetBrains Mono",ui-monospace,Consolas,monospace;font-size:12.5px;line-height:1.5;background:var(--soft);border:1px solid var(--line);border-radius:8px;padding:12px 14px;overflow-x:auto;white-space:pre}
table{border-collapse:collapse;width:100%;margin:12px 0;font-size:.95rem}
th,td{border-bottom:1px solid var(--line);padding:7px 10px;text-align:left;vertical-align:top}
th{background:var(--soft);font-weight:600}
.ok{color:var(--ok);font-weight:600}.bad{color:var(--bad);font-weight:600}
figure{margin:20px 0}figcaption{color:var(--muted);font-size:.92rem;margin-top:6px}
svg{max-width:100%;height:auto;display:block}
.nota{background:#fff8e6;border:1px solid #f0d58a;border-radius:8px;padding:12px 16px;margin:16px 0}
.card{border:1px solid var(--line);border-radius:10px;padding:18px 20px;margin:14px 0}
.card h3{margin-top:0}
nav.toc{background:var(--soft);border-radius:10px;padding:14px 20px;margin:20px 0}
nav.toc ol{margin:0;padding-left:20px}
details summary{cursor:pointer;color:var(--acc);margin:6px 0}
.links{font-size:.92rem;color:var(--muted)}
@media (max-width:640px){table{display:block;overflow-x:auto}main{padding:24px 16px 60px}h1{font-size:1.6rem}}
"""


def pagina(titulo, corpo):
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titulo}</title>
<!-- Dupla: {DUPLA} | Funcionalidade: {titulo} | Ultima modificacao: {DATA} -->
<style>{CSS}</style></head><body><main>
{corpo}
<p class="links" style="margin-top:60px">Dupla: {DUPLA} · Última modificação: {DATA}</p>
</main></body></html>
"""


# ----------------------------------------------------------------- diagramas
SVG_ARQ = """<svg viewBox="0 0 860 330" role="img" aria-label="Arquitetura" font-family="system-ui,sans-serif" font-size="14">
<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#5b6475"/></marker>
<marker id="b" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#1f5fbf"/></marker></defs>
<rect x="20" y="120" width="170" height="80" rx="8" fill="none" stroke="#5b6475"/>
<text x="105" y="152" text-anchor="middle" font-weight="600">Cliente</text>
<text x="105" y="172" text-anchor="middle" font-size="12" fill="#5b6475">envia ao endereço</text>
<text x="105" y="188" text-anchor="middle" font-size="12" fill="#5b6475">do grupo</text>
<rect x="250" y="20" width="590" height="290" rx="10" fill="none" stroke="#5b6475" stroke-dasharray="5 4"/>
<text x="268" y="46" font-weight="600">Grupo multicast 224.1.1.1:5007</text>
<rect x="270" y="90" width="170" height="110" rx="8" fill="#1f5fbf" fill-opacity=".10" stroke="#1f5fbf" stroke-width="2"/>
<text x="355" y="120" text-anchor="middle" font-weight="600">S1 · líder</text>
<text x="355" y="142" text-anchor="middle" font-size="12">menor ID sem falha</text>
<text x="355" y="160" text-anchor="middle" font-size="12">responde ao cliente</text>
<text x="355" y="178" text-anchor="middle" font-size="12">coordena as escritas</text>
<rect x="465" y="90" width="170" height="110" rx="8" fill="none" stroke="#5b6475"/>
<text x="550" y="120" text-anchor="middle" font-weight="600">S2 · réplica</text>
<text x="550" y="142" text-anchor="middle" font-size="12" fill="#5b6475">recebe a requisição</text>
<text x="550" y="160" text-anchor="middle" font-size="12" fill="#5b6475">e não responde;</text>
<text x="550" y="178" text-anchor="middle" font-size="12" fill="#5b6475">executa REPLICA + ACK</text>
<rect x="660" y="90" width="170" height="110" rx="8" fill="none" stroke="#5b6475"/>
<text x="745" y="120" text-anchor="middle" font-weight="600">S3 · réplica</text>
<text x="745" y="142" text-anchor="middle" font-size="12" fill="#5b6475">recebe a requisição</text>
<text x="745" y="160" text-anchor="middle" font-size="12" fill="#5b6475">e não responde;</text>
<text x="745" y="178" text-anchor="middle" font-size="12" fill="#5b6475">executa REPLICA + ACK</text>
<rect x="270" y="235" width="560" height="54" rx="8" fill="#eef1f6" stroke="#5b6475"/>
<text x="550" y="258" text-anchor="middle" font-size="13">HEARTBEAT por multicast a cada 1 s, de todos para todos</text>
<text x="550" y="277" text-anchor="middle" font-size="12" fill="#5b6475">3 s sem heartbeat de um membro = falha (parada total)</text>
<path d="M190 140H268" stroke="#5b6475" stroke-width="1.5" fill="none" marker-end="url(#a)"/>
<text x="229" y="130" text-anchor="middle" font-size="12" fill="#5b6475">REQ</text>
<path d="M270 185H192" stroke="#1f5fbf" stroke-width="1.5" fill="none" marker-end="url(#b)"/>
<text x="229" y="205" text-anchor="middle" font-size="12" fill="#1f5fbf">RESPOSTA</text>
<text x="229" y="221" text-anchor="middle" font-size="11" fill="#1f5fbf">(unicast)</text>
</svg>"""

SVG_SEQ = """<svg viewBox="0 0 860 470" role="img" aria-label="Sequência de uma escrita" font-family="system-ui,sans-serif" font-size="13">
<defs><marker id="s" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#1d2433"/></marker></defs>
<g font-weight="600" text-anchor="middle">
<rect x="40" y="16" width="120" height="34" rx="6" fill="#eef1f6" stroke="#5b6475"/><text x="100" y="38">Cliente</text>
<rect x="260" y="16" width="120" height="34" rx="6" fill="#1f5fbf" fill-opacity=".12" stroke="#1f5fbf"/><text x="320" y="38">S1 (líder)</text>
<rect x="480" y="16" width="120" height="34" rx="6" fill="#eef1f6" stroke="#5b6475"/><text x="540" y="38">S2</text>
<rect x="680" y="16" width="120" height="34" rx="6" fill="#eef1f6" stroke="#5b6475"/><text x="740" y="38">S3</text></g>
<g stroke="#b8bfcc" stroke-dasharray="4 4"><path d="M100 50V450"/><path d="M320 50V450"/><path d="M540 50V450"/><path d="M740 50V450"/></g>
<g stroke="#1d2433" stroke-width="1.4" fill="none">
<path d="M100 90H318" marker-end="url(#s)"/><path d="M100 90H538" marker-end="url(#s)" stroke-dasharray="2 3"/><path d="M100 90H738" marker-end="url(#s)" stroke-dasharray="2 3"/>
<path d="M320 190H538" marker-end="url(#s)"/><path d="M320 190H738" marker-end="url(#s)"/>
<path d="M540 270H322" marker-end="url(#s)"/><path d="M740 300H322" marker-end="url(#s)"/>
<path d="M320 400H102" marker-end="url(#s)" stroke="#1f5fbf"/></g>
<text x="108" y="76">1. REQ {req_id, DEPOSITO, 100} → grupo multicast</text>
<text x="560" y="120" fill="#5b6475">S2 e S3 também recebem:</text>
<text x="560" y="136" fill="#5b6475">"líder é S1, não respondo"</text>
<rect x="250" y="130" width="140" height="34" rx="5" fill="#fff" stroke="#1f5fbf"/>
<text x="320" y="152" text-anchor="middle">2. executa: saldo 100</text>
<text x="335" y="176">3. REPLICA {req_id, op, valor, saldo_lider} → grupo</text>
<rect x="470" y="212" width="140" height="30" rx="5" fill="#fff" stroke="#5b6475"/><text x="540" y="232" text-anchor="middle">executa: saldo 100</text>
<rect x="670" y="212" width="140" height="30" rx="5" fill="#fff" stroke="#5b6475"/><text x="740" y="232" text-anchor="middle">executa: saldo 100</text>
<text x="430" y="259" text-anchor="middle">4. ACK (unicast)</text>
<text x="640" y="289" text-anchor="middle">4. ACK (unicast)</text>
<rect x="225" y="330" width="190" height="44" rx="5" fill="#fff" stroke="#1f5fbf"/>
<text x="320" y="349" text-anchor="middle">5. tem ACK de todos os</text><text x="320" y="366" text-anchor="middle">membros sem falha?</text>
<text x="108" y="388" fill="#1f5fbf">6. RESPOSTA {saldo 100, S1, IP, porta, replicado em [S1,S2,S3]}</text>
<rect x="0" y="424" width="860" height="40" fill="#fff"/><text x="430" y="446" text-anchor="middle" font-size="12" fill="#5b6475">Se uma réplica falha no meio, ela sai da lista de vivos (heartbeat) e o líder deixa de esperar o ACK dela.</text>
</svg>"""

SVG_FAILOVER = """<svg viewBox="0 0 860 230" role="img" aria-label="Linha do tempo da troca de líder" font-family="system-ui,sans-serif" font-size="13">
<defs><marker id="f" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#5b6475"/></marker></defs>
<g stroke="#e3e6ec"><path d="M80 40V180"/><path d="M230 40V180"/><path d="M380 40V180"/><path d="M530 40V180"/><path d="M680 40V180"/></g>
<path d="M60 180H830" stroke="#5b6475" stroke-width="1.4" marker-end="url(#f)"/>
<g font-size="12" fill="#5b6475" text-anchor="middle"><text x="80" y="200">t = 0</text><text x="230" y="200">1 s</text><text x="380" y="200">2 s</text><text x="530" y="200">3 s</text><text x="680" y="200">4 s</text></g>
<text x="20" y="74" font-weight="600">S1</text><text x="20" y="144" font-weight="600">S2</text>
<circle cx="80" cy="70" r="6" fill="#1d7a3e"/>
<text x="80" y="52" text-anchor="middle" font-size="12" fill="#1d7a3e">último heartbeat</text>
<path d="M110 58V82" stroke="#b42318" stroke-width="2.5"/>
<text x="120" y="96" font-size="12" fill="#b42318" font-weight="600">kill -9 (parada total)</text>
<path d="M86 118H526" stroke="#5b6475" stroke-dasharray="5 4" marker-end="url(#f)"/>
<text x="305" y="110" text-anchor="middle" font-size="12" fill="#5b6475">3 s sem heartbeat de S1: requisições ficam sem resposta, o cliente reenvia</text>
<rect x="530" y="126" width="290" height="34" rx="6" fill="#1f5fbf" fill-opacity=".12" stroke="#1f5fbf"/>
<text x="675" y="148" text-anchor="middle">S2 detecta a falha e assume como líder</text>
</svg>"""


def trecho(caminho, max_linhas=60):
    with open(caminho, encoding="utf-8") as f:
        linhas = [l.rstrip("\n")[11:] for l in f if not any(r in l for r in RUIDO)]
    if len(linhas) > max_linhas:
        linhas = linhas[:max_linhas] + [f"... ({len(linhas) - max_linhas} linhas a mais no log completo)"]
    return html.escape("\n".join(linhas))


def gera():
    if os.path.isdir(SITE):
        shutil.rmtree(SITE)
    os.makedirs(os.path.join(SITE, "codigo"))
    os.makedirs(os.path.join(SITE, "logs"))

    for nome, _ in CODIGOS:
        shutil.copy(os.path.join(AQUI, nome), os.path.join(SITE, "codigo", nome + ".txt"))

    with open(os.path.join(AQUI, "logs", "resumo.json"), encoding="utf-8") as f:
        resumo = json.load(f)
    for r in resumo:
        r["titulo"] = TITULOS.get(r["num"], r["titulo"])
        for c in r["checks"]:
            c["req"] = c["req"].replace("estado da replica", "estado da réplica")

    cards = []
    linhas_tab = []
    for r in resumo:
        pasta = f"cenario{r['num']:02d}"
        orig = os.path.join(AQUI, "logs", pasta)
        dest = os.path.join(SITE, "logs", pasta)
        os.makedirs(dest)
        arquivos = []
        for nome in sorted(os.listdir(orig)):
            shutil.copy(os.path.join(orig, nome), os.path.join(dest, nome + ".txt"))
            arquivos.append(nome)
        ordem = ["linha_do_tempo.log", "roteiro.log", "cliente.log"]
        arquivos.sort(key=lambda n: (ordem.index(n) if n in ordem else 9, n))
        links = " · ".join(f'<a href="logs/{pasta}/{n}.txt">{n}</a>' for n in arquivos)
        checks = "".join(
            f"<tr><td>{html.escape(c['req'])}</td><td>{html.escape(c['esperado'])}</td>"
            f"<td>{html.escape(c['obtido'])}</td>"
            f"<td class=\"{'ok' if c['ok'] else 'bad'}\">{'OK' if c['ok'] else 'ERRO'}</td></tr>"
            for c in r["checks"])
        n_ok = sum(c["ok"] for c in r["checks"])
        linhas_tab.append(f"<tr><td>{r['num']}</td><td><a href=\"#c{r['num']}\">{html.escape(r['titulo'])}</a></td>"
                          f"<td>{n_ok}/{len(r['checks'])}</td>"
                          f"<td class=\"{'ok' if r['ok'] else 'bad'}\">{'passou' if r['ok'] else 'falhou'}</td></tr>")
        cards.append(f"""<div class="card" id="c{r['num']}">
<h3>Cenário {r['num']} · {html.escape(r['titulo'])}</h3>
<p>{DESCR.get(r['num'], '')}</p>
<table><tr><th>Requisição / verificação</th><th>Esperado</th><th>Obtido</th><th></th></tr>{checks}</table>
<details><summary>Ver trecho da linha do tempo (todos os processos)</summary>
<pre>{trecho(os.path.join(orig, 'linha_do_tempo.log'))}</pre></details>
<p class="links">Logs completos: {links}</p></div>""")

    total = sum(len(r["checks"]) for r in resumo)
    total_ok = sum(c["ok"] for r in resumo for c in r["checks"])

    codigos_html = "".join(f'<tr><td><a href="codigo/{n}.txt"><code>{n}.txt</code></a></td><td>{d}</td></tr>'
                           for n, d in CODIGOS)

    rel = f"""
<h1>Servidor tolerante a falhas com grupo multicast</h1>
<p class="sub">TP Redes II 2026 · Dupla: {DUPLA} · {DATA}</p>

<nav class="toc"><ol>
<li><a href="#visao">Visão geral</a></li><li><a href="#servico">Serviço oferecido</a></li>
<li><a href="#arq">Arquitetura</a></li><li><a href="#proto">Protocolo</a></li>
<li><a href="#decisoes">Decisões de projeto</a></li><li><a href="#exec">Como executar</a></li>
<li><a href="#testes">Testes e resultados</a></li><li><a href="#lab">Execução em 3 hosts</a></li>
<li><a href="#limites">Limitações</a></li></ol></nav>

<h2 id="visao">1. Visão geral</h2>
<p>O "servidor" é um grupo de N processos servidores (S1, S2, …, SN) que participam do mesmo grupo
multicast IP. Todos conhecem o identificador, o IP e a porta de todos os outros (arquivo
<code>config.json</code>). O cliente envia a requisição para o <b>endereço do grupo</b>; todos os servidores a
recebem, mas apenas o <b>líder</b>, o servidor sem falha de <b>menor identificador</b>, responde. A resposta
contém o resultado do serviço e o identificador, o IP e a porta do servidor que atendeu.</p>
<p>Cada servidor envia periodicamente um <b>heartbeat</b> por multicast. Quem fica 3 s sem enviar é
considerado falho. As falhas consideradas são de parada total: nos testes os processos são mortos com
<code>kill -9</code>. Implementação em Python 3, só com a biblioteca padrão (<code>socket</code>,
<code>threading</code>, <code>json</code>).</p>
<p>Resultado: <b>{len(resumo)} cenários</b> de teste, <b>{total_ok} de {total}</b> verificações corretas.</p>

<h2 id="servico">2. Serviço oferecido: conta bancária</h2>
<table><tr><th>Operação</th><th>Tipo</th><th>Efeito</th></tr>
<tr><td><code>SALDO</code></td><td>consulta (leitura)</td><td>o líder responde imediatamente com o saldo</td></tr>
<tr><td><code>DEPOSITO v</code></td><td>alteração (escrita)</td><td>soma v ao saldo, replicado em todos</td></tr>
<tr><td><code>SAQUE v</code></td><td>alteração (escrita)</td><td>subtrai v; recusado se o saldo for insuficiente</td></tr></table>
<p>Escolhemos uma conta porque nela uma escrita duplicada causa um erro visível (um depósito contado duas
vezes), o que torna fácil demonstrar a correção da estratégia nos testes.</p>

<h2 id="arq">3. Arquitetura</h2>
<figure>{SVG_ARQ}<figcaption>Figura 1 · Todos recebem a requisição pelo grupo; só o líder responde, por unicast, ao IP:porta de origem do cliente.</figcaption></figure>
<p>Cada servidor tem quatro <i>threads</i>:</p>
<table><tr><th>Thread</th><th>Função</th></tr>
<tr><td>heartbeat</td><td>envia <code>HEARTBEAT</code> ao grupo a cada 1 s</td></tr>
<tr><td>monitor</td><td>a cada 0,2 s recalcula a lista de vivos e o líder e registra no log falhas, novos membros e troca de líder</td></tr>
<tr><td>grupo</td><td>recebe o tráfego multicast: <code>HEARTBEAT</code>, <code>REQ</code>, <code>REPLICA</code>, <code>SYNC_REQ</code></td></tr>
<tr><td>unicast</td><td>recebe na porta do servidor: <code>ACK</code> das réplicas e <code>STATE</code> (sincronização)</td></tr></table>
<p>A eleição não precisa de troca de mensagens extra: como todos veem os mesmos heartbeats, cada servidor
calcula sozinho <code>lider = min(vivos)</code>. Quando chega uma requisição, cada um verifica se ele mesmo é o líder.</p>

<h2 id="proto">4. Protocolo</h2>
<table><tr><th>Mensagem</th><th>Via</th><th>Campos</th><th>Uso</th></tr>
<tr><td>HEARTBEAT</td><td>multicast</td><td>id, sinc</td><td>"estou sem falha" e se já tenho o estado da conta</td></tr>
<tr><td>REQ</td><td>multicast</td><td>req_id, op, valor</td><td>requisição do cliente ao grupo</td></tr>
<tr><td>REPLICA</td><td>multicast</td><td>req_id, op, valor, lider, saldo_lider</td><td>líder pede às réplicas que executem a escrita</td></tr>
<tr><td>ACK</td><td>unicast → líder</td><td>req_id, id</td><td>réplica confirma que executou</td></tr>
<tr><td>RESPOSTA</td><td>unicast → cliente</td><td>req_id, ok, resultado, saldo, servidor{{id, ip, porta}}, replicado_em</td><td>resposta do líder</td></tr>
<tr><td>SYNC_REQ</td><td>multicast</td><td>id</td><td>servidor que (re)iniciou pede o estado</td></tr>
<tr><td>STATE</td><td>unicast</td><td>saldo, cache</td><td>estado atual enviado a quem pediu</td></tr></table>

<h3>Escrita</h3>
<figure>{SVG_SEQ}<figcaption>Figura 2 · O líder executa, replica, espera o ACK de todos os membros sem falha e só então responde.</figcaption></figure>
<ol><li>O cliente envia <code>REQ</code> ao grupo com um <code>req_id</code> único.</li>
<li>O líder executa a operação localmente.</li>
<li>O líder envia <code>REPLICA</code> ao grupo.</li>
<li>Cada réplica executa e responde <code>ACK</code> ao líder (unicast, IP:porta do <code>config.json</code>).</li>
<li>O líder espera o ACK de todos os membros que continuam sem falha, reenviando a REPLICA a cada 1 s (o UDP pode perder pacotes). Um membro que falha no meio sai da lista de vivos e deixa de ser esperado.</li>
<li>O líder responde ao cliente, informando em quais servidores a escrita foi replicada.</li></ol>
<p>Uma leitura é respondida diretamente pelo líder. As escritas são executadas uma de cada vez pelo líder (um <i>lock</i>), o que garante que todas as réplicas recebam as alterações na mesma ordem.</p>

<h3>Detecção de falha e troca de líder</h3>
<figure>{SVG_FAILOVER}<figcaption>Figura 3 · Com heartbeat de 1 s e limite de 3 s, a troca de líder acontece cerca de 3 s após a parada.</figcaption></figure>

<h2 id="decisoes">5. Decisões de projeto</h2>
<ul>
<li><b>Reenvio pelo cliente com o mesmo <code>req_id</code>.</b> Se nenhuma resposta chega em 2 s, o cliente reenvia a mesma requisição (até 6 vezes). Isso cobre o intervalo em que o líder já morreu mas a falha ainda não foi detectada.</li>
<li><b>Sem execução dupla.</b> Todo servidor guarda um <i>cache</i> <code>req_id → resultado</code>. Se o líder morre depois de replicar e antes de responder, o novo líder já executou aquela escrita como réplica e, ao receber o reenvio, devolve o resultado guardado, sem executar de novo (cenário 9).</li>
<li><b>Período de inicialização.</b> Um servidor recém-iniciado não sabe quem está vivo. Por isso, nos primeiros 3 s ele não atende clientes, para não se considerar líder por engano.</li>
<li><b>Sincronização ao voltar de uma falha.</b> O heartbeat informa se o servidor já tem estado (<code>sinc</code>). Um servidor que reinicia envia <code>SYNC_REQ</code>; o membro sem falha de menor ID que tem estado responde com <code>STATE</code>. Só depois disso o servidor que voltou pode assumir como líder (cenário 10). Se todos estão começando juntos, ninguém tem estado e todos começam com saldo 0.</li>
<li><b>Verificação de consistência.</b> A REPLICA leva o saldo do líder. Se a réplica chegar a um saldo diferente, ela registra <code>INCONSISTENCIA</code> no log e adota o do líder. Em todos os testes essa situação não ocorreu.</li>
<li><b>Bug encontrado nos testes.</b> Na primeira versão, um servidor que voltava de uma falha assumia a liderança com saldo 0 e respondia errado. O cenário 10 detectou o problema, e a correção foi a sincronização descrita acima.</li>
</ul>

<h2 id="exec">6. Como executar</h2>
<pre># em cada host (um servidor por host), com o IP de cada máquina no config
python3 servidor.py --id 1 --config config.json --log logs/s1.log
python3 servidor.py --id 2 --config config.json --log logs/s2.log
python3 servidor.py --id 3 --config config.json --log logs/s3.log

# cliente (em qualquer host da mesma rede); --iface = IP da máquina do cliente
python3 cliente.py SALDO --iface 192.168.0.10
python3 cliente.py DEPOSITO 100 --iface 192.168.0.10
python3 cliente.py --iface 192.168.0.10        # modo interativo

# simular falha (parada total) de um servidor
kill -9 &lt;pid do servidor&gt;

# todos os cenários automaticamente, numa máquina só
python3 cenarios.py</pre>
<p>Código-fonte comentado:</p>
<table><tr><th>Arquivo</th><th>Conteúdo</th></tr>{codigos_html}</table>

<h2 id="testes">7. Testes e resultados</h2>
<p>Cada cenário sobe os servidores do zero, executa requisições, mata processos com <code>SIGKILL</code>
(<code>kill -9</code>) e confere duas coisas: qual servidor respondeu e o saldo. No fim, confere no log de cada
réplica sem falha se o saldo é igual em todas. Para cada cenário há o log de cada processo, o roteiro e uma
<b>linha do tempo</b> que junta todos os logs em ordem de horário.</p>
<p>Nos cenários 8 e 9 a parada é feita pelo próprio processo (<code>os._exit</code>, opção <code>--falha</code>)
num ponto exato do protocolo, que seria difícil de acertar com <code>kill</code> manual. O efeito é o mesmo:
o processo para completamente.</p>
<table><tr><th>#</th><th>Cenário</th><th>Verificações</th><th>Resultado</th></tr>{''.join(linhas_tab)}</table>
{''.join(cards)}

<h2 id="lab">8. Execução em 3 hosts diferentes</h2>
<div class="nota"><b>[A COMPLETAR PELA DUPLA]</b> Os logs da seção 7 foram gerados numa única máquina
(3 processos em portas diferentes, multicast pela interface local). O enunciado exige logs com 3 servidores
em hosts diferentes. Rodem os cenários principais no laboratório com o <code>config_lab.json</code>
(preenchido com os IPs das máquinas), coloquem os logs em <code>logs/lab/</code> e substituam este aviso
por uma tabela com os resultados e os links.</div>

<h2 id="limites">9. Limitações</h2>
<ul>
<li>O modelo considera só falhas de parada total, como pede o enunciado; partição de rede não é tratada. Se a rede se dividir, cada parte elegeria seu próprio líder.</li>
<li>Com perda de heartbeats, dois servidores podem se considerar líder por um instante. O cliente usa a primeira resposta e descarta a outra pelo <code>req_id</code>.</li>
<li>O estado fica em memória: se todos os servidores param, o saldo se perde (cenário 12).</li>
<li>O multicast usa TTL 1, então todos os hosts precisam estar na mesma rede local.</li>
</ul>
"""
    with open(os.path.join(SITE, "relatorio.html"), "w", encoding="utf-8") as f:
        f.write(pagina("Relatório · TP Redes II 2026", rel))

    idx = f"""
<h1>TP Redes II 2026</h1>
<p class="sub">Servidor tolerante a falhas com grupo multicast · Dupla: {DUPLA}</p>
<div class="card"><h3><a href="relatorio.html">Relatório</a></h3>
<p>Como o trabalho foi feito, diagramas da arquitetura e do protocolo, e os resultados dos {len(resumo)} cenários de teste.</p></div>
<div class="card"><h3>Código-fonte comentado</h3><table>{codigos_html}</table></div>
<div class="card"><h3>Logs de execução</h3><ul>
{''.join(f'<li><a href="relatorio.html#c{r["num"]}">Cenário {r["num"]}</a> · {html.escape(r["titulo"])} · <a href="logs/cenario{r["num"]:02d}/linha_do_tempo.log.txt">linha do tempo</a></li>' for r in resumo)}
</ul></div>
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
}

DESCR = {
    1: "Os três servidores estão sem falha. S1, de menor ID, responde a tudo. As escritas são replicadas em S1, S2 e S3. O saque maior que o saldo é recusado, e o saldo não muda.",
    2: "Depois de um depósito, S1 é morto. S2 e S3 detectam a falha pelo heartbeat, S2 passa a ser o líder, mantém o saldo de 100 e atende às novas requisições.",
    3: "O cliente envia a requisição logo após a morte de S1, antes de a falha ser detectada. Ninguém responde à primeira tentativa (S2 e S3 ainda acham que S1 é o líder). Após a detecção, S2 assume e responde ao reenvio.",
    4: "Uma réplica (S2) é morta. S1 continua líder e, nas escritas, espera apenas o ACK de S3.",
    5: "S1 e S2 são mortos. S3 é o único sem falha, vira líder e atende sozinho com o saldo correto.",
    6: "S1 e S3 são mortos. S2 atende sozinho.",
    7: "S2 e S3 são mortos. S1 continua líder e completa as escritas sem esperar ACK.",
    8: "S3 para no instante em que recebe a REPLICA, sem executar nem confirmar. S1 detecta a falha pelo heartbeat, deixa de esperar o ACK de S3 e responde ao cliente.",
    9: "S1 executa e replica um depósito de 100 e para antes de responder. O cliente reenvia o mesmo req_id, S2 assume e reconhece a escrita já executada. O saldo fica em 100, e não 200.",
    10: "S1 é morto e S2 assume. Depois S1 é reiniciado, pede o estado ao grupo, recebe o saldo de S2 e volta a ser o líder por ter o menor ID, com o saldo correto.",
    11: "Um cliente faz 6 depósitos, um por segundo, e S1 é morto durante a sequência. O depósito que estava em andamento é reenviado e atendido por S2, e nenhum é perdido ou duplicado: o saldo final é 60.",
    12: "Todos os servidores são mortos. O cliente tenta 6 vezes e informa que nenhum servidor respondeu.",
}

if __name__ == "__main__":
    gera()
