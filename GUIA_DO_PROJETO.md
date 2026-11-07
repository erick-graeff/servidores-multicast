# Guia do Projeto — Servidor Tolerante a Falhas com Multicast

## 1. Objetivo

Este projeto implementa um serviço de conta bancária replicado em um grupo de servidores que se comunicam por UDP multicast. O grupo continua atendendo clientes quando servidores sofrem parada total, desde que pelo menos um membro com estado válido permaneça disponível.

O serviço oferece:

- `SALDO`: consulta o saldo atual;
- `DEPOSITO <valor>`: adiciona um valor ao saldo;
- `SAQUE <valor>`: retira um valor, se houver saldo suficiente.

O cliente envia requisições ao grupo, mas apenas o líder responde. A resposta contém o resultado, o saldo e o ID, IP e porta do servidor que atendeu.

### Situação atual

- 46/46 testes unitários aprovados;
- 15/15 cenários de integração local aprovados;
- 92/92 verificações locais aprovadas;
- página HTML gerada em `site/index.html`;
- execução em três hosts do laboratório ainda pendente.

Os testes locais não substituem a evidência exigida de três servidores em hosts diferentes.

---

## 2. Pré-requisitos

- Python 3.10 ou superior;
- sistema operacional com suporte a UDP multicast IPv4;
- somente biblioteca padrão do Python; não há pacotes externos para instalar;
- portas UDP 5007 e 6001–6003 livres para os testes locais;
- para o laboratório, hosts na mesma rede local, com multicast e as portas necessárias liberadas.

O grupo multicast usado é `224.1.1.1:5007`, com TTL 1. Por isso, o tráfego fica restrito à rede local.

---

## 3. Início rápido

Execute os comandos a partir da raiz do projeto.

### 3.1. Rodar os testes unitários

```bash
python3 -m unittest discover -s tests -v
```

Resultado atual: **46 testes aprovados**.

Os testes unitários usam dublês, como `CanalFake`, e não precisam abrir sockets reais.

### 3.2. Rodar todos os cenários locais

```bash
python3 cenarios.py --saida logs/pos_correcoes
```

O script inicia três processos servidores, executa clientes reais, mata servidores com `SIGKILL` nos cenários de falha e verifica o servidor que respondeu, o saldo e a consistência das réplicas.

Resultado atual: **15 cenários e 92 verificações aprovadas**.

Os resultados são gravados em:

```text
logs/pos_correcoes/
├── resumo.json
├── cenario01/
├── cenario02/
├── ...
└── cenario15/
```

Para executar somente alguns cenários:

```bash
python3 cenarios.py --saida logs/teste_parcial --so 1 8 9 10 13 14 15
```

Use diretórios de saída diferentes para preservar execuções anteriores. O script apaga os arquivos antigos das pastas de cenário que executar novamente dentro do diretório de saída escolhido.

### 3.3. Gerar a página HTML

```bash
python3 gera_pagina.py --logs logs/pos_correcoes
```

Depois, abra:

```text
site/index.html
```

O gerador recria `site/`, copia os códigos com terminação `.txt`, publica os logs e monta o relatório com diagramas e resultados.

---

## 4. Executar manualmente em uma máquina

Use quatro terminais, todos na raiz do projeto.

### Terminal 1 — servidor S1

```bash
python3 servidor.py --id 1 --config config.json --log logs/manual/servidor_S1.log
```

### Terminal 2 — servidor S2

```bash
python3 servidor.py --id 2 --config config.json --log logs/manual/servidor_S2.log
```

### Terminal 3 — servidor S3

```bash
python3 servidor.py --id 3 --config config.json --log logs/manual/servidor_S3.log
```

Aguarde aproximadamente 4 segundos para a sincronização e a eleição inicial.

### Terminal 4 — cliente

```bash
python3 cliente.py SALDO --config config.json --iface 127.0.0.1
python3 cliente.py DEPOSITO 100 --config config.json --iface 127.0.0.1
python3 cliente.py SAQUE 30 --config config.json --iface 127.0.0.1
python3 cliente.py SALDO --config config.json --iface 127.0.0.1
```

Resultado esperado dessa sequência: saldo 70, inicialmente atendido por S1.

Também existe modo interativo:

```bash
python3 cliente.py --config config.json --iface 127.0.0.1
```

Comandos aceitos:

```text
SALDO
DEPOSITO 100
SAQUE 30
SAIR
```

### Opções úteis do cliente

```text
--config ARQUIVO     Arquivo de configuração; padrão: config.json
--iface IP           IP da interface local usada para multicast
--nome NOME          Identificação do cliente nos logs e no req_id
--log ARQUIVO        Arquivo no qual o log será acrescentado
--tentativas N       Orçamento total = tentativas x espera; padrão: 6
--espera SEGUNDOS    Pedaco do orçamento por (re)envio; padrão: 2.0 (total 12 s)
--repetir SEGUNDOS   Cadência de reenvio da mesma requisição; padrão: 0.5
```

### Simular uma parada total

Descubra o PID do servidor desejado e execute:

```bash
kill -9 <pid>
```

Depois de aproximadamente 1,5 segundo sem heartbeat, os demais detectam a falha (a eleição termina antes do ciclo de espera do cliente). Se S1 parar, S2 assume; se S1 e S2 pararem, S3 assume.

O cliente reenvia a mesma requisição com o mesmo `req_id` a cada 0,5 s; e uma réplica guarda as requisições recebidas durante a troca de líder e o novo líder as atende ao assumir — a resposta chega em cerca de 2 s, sem esperar uma nova tentativa.

---

## 5. Executar em três hosts

Esta etapa ainda depende dos IPs e hosts reais do laboratório.

### 5.1. Preparar a configuração

Edite `config_lab.json` e substitua:

```json
{"id": 1, "ip": "IP_DA_MAQUINA_A", "porta": 6001}
{"id": 2, "ip": "IP_DA_MAQUINA_B", "porta": 6002}
{"id": 3, "ip": "IP_DA_MAQUINA_C", "porta": 6003}
```

pelos endereços IP reais das três máquinas. A mesma configuração deve estar disponível em todos os servidores e no cliente.

Verifique também:

- se os hosts estão na mesma rede local;
- se a rede permite multicast IPv4;
- se o grupo UDP 5007 está liberado;
- se as portas UDP 6001, 6002 e 6003 estão liberadas;
- se cada IP informado pertence à interface correta do host.

### 5.2. Iniciar os servidores

Na máquina A:

```bash
python3 servidor.py --id 1 --config config_lab.json --log logs/lab/servidor_S1.log
```

Na máquina B:

```bash
python3 servidor.py --id 2 --config config_lab.json --log logs/lab/servidor_S2.log
```

Na máquina C:

```bash
python3 servidor.py --id 3 --config config_lab.json --log logs/lab/servidor_S3.log
```

### 5.3. Executar o cliente

Em uma máquina da mesma rede:

```bash
python3 cliente.py SALDO --config config_lab.json --iface <IP_DESTA_MAQUINA>
python3 cliente.py DEPOSITO 100 --config config_lab.json --iface <IP_DESTA_MAQUINA>
```

Evite depender de `--iface 0.0.0.0` em máquinas com múltiplas interfaces: informar o IP real deixa a escolha da interface explícita.

### 5.4. Produzir as evidências

Execute os cenários principais de leitura, escrita, falha do líder, falha de réplica, múltiplas falhas e retorno de servidores. Use `kill -9` para simular parada total.

Reúna em `logs/lab/`:

- logs de cada servidor;
- logs dos clientes;
- roteiro das ações executadas;
- resultados esperados e obtidos;
- identificação dos três IPs distintos.

Só depois dessa evidência a seção de laboratório do relatório deve ser marcada como concluída.

---

## 6. Relação entre os arquivos

### 6.1. Dependências principais

```text
cliente.py ───────────────┐
                          │
servidor.py ──────────────┼──> comunicacao.py
                          │
                          ├──> conta.py
                          │
                          └──> membros.py

cenarios.py ────────────────> executa cliente.py e servidor.py como processos

gera_pagina.py ─────────────> lê códigos e logs e produz site/

tests/ ─────────────────────> testa os módulos usando dublês, incluindo CanalFake
```

As dependências seguem uma direção: cliente e servidor usam os módulos de infraestrutura e domínio; `comunicacao.py`, `conta.py` e `membros.py` não importam cliente nem servidor.

### 6.2. Responsabilidades

| Arquivo | Responsabilidade |
|---|---|
| `cliente.py` | Interpreta comandos, cria `req_id`, envia requisições, faz retransmissões e apresenta respostas |
| `servidor.py` | Coordena inicialização, threads, requisições, replicação, ACKs, respostas e sincronização |
| `comunicacao.py` | Encapsula sockets UDP, JSON, timeout e canais unicast/multicast |
| `conta.py` | Mantém saldo, cache de operações, versões e snapshots |
| `membros.py` | Controla heartbeats recebidos, membros vivos, flags de sincronização e eleição |
| `cenarios.py` | Orquestra os testes de integração locais |
| `gera_pagina.py` | Gera o site de entrega a partir dos códigos e logs |
| `config.json` | Configuração local: três processos em `127.0.0.1` |
| `config_lab.json` | Modelo de configuração para três hosts reais |
| `tests/` | Testes unitários e dublês |
| `logs/` | Baseline e resultados das execuções locais |
| `site/` | Página final, código `.txt` e logs publicados |
| `ANALISE_PROJETO.md` | Diagnóstico, decisões e to-do list com evidências de execução |
| `GUIA_DO_PROJETO.md` | Guia de arquitetura, execução, arquivos e testes |
| `base/` | Material de referência; não participa da implementação |

### 6.3. Criação e injeção dos canais

Os sockets são criados somente nos pontos de entrada (`main()`).

O cliente recebe um canal usado tanto para enviar ao grupo quanto para receber a resposta unicast.

Cada servidor recebe dois canais:

- `canal_grupo`: recebe `REQ`, `HEARTBEAT`, `REPLICA` e `SYNC_REQ` por multicast;
- `canal_uni`: envia mensagens ao grupo e ao cliente e recebe `ACK` e `STATE` por unicast.

Essa injeção permite substituir o canal real por `CanalFake` nos testes.

---

## 7. Como o protocolo funciona

### 7.1. Inicialização

Cada servidor começa com `sincronizado = False` e envia `SYNC_REQ` ao grupo. Durante o período inicial, ele não responde a clientes.

Se houver um membro com estado, o reintegrante recebe um snapshot. Se todos estiverem começando juntos, o estado inicial é saldo 0 e versão 0.

O `SYNC_REQ` também marca o reintegrante como vivo nos demais membros. Isso permite ao líder aguardar seu ACK caso uma nova escrita ocorra depois do snapshot.

### 7.2. Heartbeat e detecção de falha

Cada servidor envia por multicast:

```json
{"tipo": "HEARTBEAT", "id": 1, "sinc": true}
```

Configuração local:

- heartbeat a cada 0,5 segundo;
- falha considerada após 1,5 segundos sem heartbeat (eleição termina antes do ciclo de espera do cliente);
- requisições recebidas durante a troca de líder são guardadas e atendidas pelo novo líder ao assumir.

`membros.py` mantém os instantes dos últimos heartbeats e calcula o conjunto de vivos.

### 7.3. Eleição

Cada servidor calcula localmente:

```text
líder = menor ID entre os membros considerados vivos
```

Exemplos:

- S1, S2 e S3 vivos: líder S1;
- S1 falho: líder S2;
- S1 e S2 falhos: líder S3.

Não há uma rodada separada de votação.

### 7.4. Consulta

Uma consulta `SALDO` é enviada ao grupo. Todos recebem, mas somente o processo que se considera líder responde, desde que já esteja sincronizado.

A leitura não altera o estado nem exige replicação.

### 7.5. Escrita e confirmação

Para `DEPOSITO` e `SAQUE`:

1. o líder executa a operação localmente;
2. a conta recebe a próxima versão;
3. o líder envia `REPLICA` ao grupo;
4. cada réplica sincronizada aplica a próxima versão e envia ACK;
5. o líder espera os ACKs dos membros sem-falha esperados;
6. somente então envia uma confirmação de sucesso ao cliente.

Se uma réplica falhar e sair do conjunto de vivos, o líder deixa de esperar seu ACK.

Se uma réplica permanecer viva sem confirmar por 8 segundos, o líder responde:

```json
{
  "ok": false,
  "erro": "REPLICACAO_NAO_CONFIRMADA"
}
```

Nesse caso, o resultado da escrita é desconhecido: ela pode ter sido aplicada no líder e em parte das réplicas. O cliente não recebe confirmação de sucesso.

### 7.6. Idempotência

Cada requisição possui um `req_id`, por exemplo:

```text
C1-abcdef
```

O cliente reutiliza esse identificador nas retransmissões. A conta guarda um cache `req_id -> resultado`, impedindo que o mesmo depósito ou saque seja executado duas vezes.

### 7.7. Ordenação por versões

A conta mantém:

- `versao`: versão atual do estado;
- `versoes`: mapa de cada `req_id` para sua versão;
- `cache`: resultado de cada requisição.

Ao receber `REPLICA`, uma réplica aplica estas regras:

| Versão recebida | Comportamento |
|---|---|
| Menor ou igual à atual | Já foi aplicada ou superada; envia ACK sem alterar o estado |
| Exatamente a próxima | Aplica a operação e envia ACK |
| Maior que a próxima | Existe lacuna; não aplica nem confirma |

Isso impede que uma retransmissão antiga faça o saldo regredir.

### 7.8. Sincronização e snapshots

Um snapshot contém:

```json
{
  "saldo": 150,
  "cache": {},
  "versao": 2,
  "versoes": {}
}
```

Na implementação real, `cache` e `versoes` contêm as operações já conhecidas.

Réplicas não sincronizadas não aplicam `REPLICA`. Snapshots antigos são rejeitados, e `REPLICA`, `STATE` e snapshots são serializados por um lock de estado.

---

## 8. Mensagens do protocolo

| Mensagem | Via | Finalidade |
|---|---|---|
| `HEARTBEAT` | multicast | Informar que o membro continua ativo e se já possui estado |
| `REQ` | multicast | Requisição do cliente ao grupo |
| `REPLICA` | multicast | Ordem do líder para aplicar uma escrita versionada |
| `ACK` | unicast para o líder | Confirmar que a réplica já possui aquela versão |
| `SYNC_REQ` | multicast | Pedir o estado atual ao grupo |
| `STATE` | unicast | Enviar snapshot versionado ao reintegrante |
| `RESPOSTA` | unicast para o cliente | Retornar resultado, saldo, ID, IP e porta do servidor |

---

## 9. Threads do servidor

Cada servidor mantém quatro threads principais:

| Thread | Função |
|---|---|
| `thread_heartbeat` | Envia heartbeat periodicamente |
| `thread_monitor` | Recalcula vivos, registra falhas e mudanças de líder |
| `thread_grupo` | Recebe tráfego multicast |
| `thread_unicast` | Recebe ACKs e snapshots |

O líder também usa locks para serializar escritas e proteger o estado compartilhado.

---

## 10. Testes

### 10.1. Testes unitários

Comando:

```bash
python3 -m unittest discover -s tests -v
```

Organização:

| Arquivo | O que verifica |
|---|---|
| `tests/test_comunicacao.py` | JSON, timeout, origem/destino e configuração dos sockets |
| `tests/test_conta.py` | Operações, idempotência, versões e snapshots |
| `tests/test_membros.py` | Heartbeats, timeout, eleição e retorno de membros |
| `tests/test_cliente.py` | `req_id`, retransmissões e descarte de respostas antigas |
| `tests/test_replicacao.py` | ACKs, timeout, duplicação e escrita sem dupla execução |
| `tests/test_ordenacao.py` | Mensagens antigas, lacunas e sincronização |
| `tests/test_injecao.py` | Uso dos canais injetados por cliente e servidor |
| `tests/test_doubles.py` | Comportamento do `CanalFake` |
| `tests/test_entrega.py` | Geração do site, links e cópias `.txt` |
| `tests/doubles.py` | Implementações falsas usadas somente nos testes |

`CanalFake` permite perder, duplicar, reordenar ou programar mensagens sem depender da rede.

### 10.2. Cenários de integração

| Cenário | Objetivo |
|---|---|
| 1 | Operações normais com todos os servidores vivos |
| 2 | Falha do líder S1 e assunção de S2 |
| 3 | Requisição antes da detecção da falha |
| 4 | Falha de uma réplica |
| 5 | S3 como único servidor vivo |
| 6 | S2 como único servidor vivo |
| 7 | S1 como único servidor vivo |
| 8 | Réplica parando durante uma escrita |
| 9 | Líder parando antes de responder, sem duplicar escrita |
| 10 | Retorno e ressincronização de S1 |
| 11 | Escritas durante a morte do líder |
| 12 | Todos os servidores falhos |
| 13 | Retorno de S2 com escrita durante a sincronização |
| 14 | Retorno de S3 com escrita durante a sincronização |
| 15 | Três clientes concorrentes |

Os cenários usam sockets e processos reais, não dublês.

### 10.3. Estrutura dos logs

Cada cenário produz:

- `cliente.log`: requisições e respostas;
- `servidor_S1.log`, `servidor_S2.log`, `servidor_S3.log`: visão de cada processo;
- `roteiro.log`: ações do teste e verificações esperadas/obtidas;
- `linha_do_tempo.log`: eventos de todos os processos ordenados pelo horário.

O arquivo `resumo.json` reúne todos os resultados.

### 10.4. Resultados preservados

| Diretório | Conteúdo |
|---|---|
| `logs/baseline_pre_refatoracao/` | Baseline anterior às mudanças |
| `logs/pos_comunicacao/` | Regressão após extrair a comunicação |
| `logs/pos_separacao_responsabilidades/` | Regressão após separar conta e membros |
| `logs/pos_ack/` | Cenários críticos após corrigir ACKs |
| `logs/reintegracao/` | Retorno de S2 e S3 |
| `logs/reintegracao_S1/` | Retorno de S1 |
| `logs/pos_correcoes/` | Resultado local final: 15 cenários e 92 verificações |

---

## 11. Limitações e comportamento em falhas

- O modelo trata parada total, não falhas bizantinas.
- Partições de rede não são tratadas. Duas partes podem eleger líderes diferentes.
- Perdas de heartbeat podem produzir líderes temporariamente divergentes.
- Se todos os servidores pararem, o estado em memória é perdido.
- O timeout de replicação pode deixar uma escrita parcialmente aplicada; por isso o cliente recebe `ok=False`, nunca sucesso.
- Uma réplica com lacuna de versão deixa de confirmar escritas posteriores. Atualmente, ela deve ser reiniciada para obter um novo snapshot; não há ressincronização automática da lacuna.
- O multicast usa TTL 1 e depende de hosts na mesma rede local.

---

## 12. Problemas comuns

### `Address already in use`

Outro processo está usando uma das portas. Encerre servidores anteriores antes de iniciar novos cenários. O próprio `cenarios.py` encerra os processos que iniciou, inclusive quando um cenário falha.

### Cliente não recebe resposta

Verifique:

- se os servidores já passaram pela inicialização;
- se o IP de `--iface` está correto;
- se o grupo e as portas estão liberados;
- se a rede suporta multicast;
- se os logs indicam que algum membro continua vivo.

### `REPLICACAO_NAO_CONFIRMADA`

Uma réplica considerada viva não confirmou dentro de 8 segundos. Isso não é confirmação de sucesso. Consulte os logs para identificar quais membros confirmaram e investigue perda de `REPLICA` ou ACK.

### `LACUNA de versoes`

A réplica recebeu uma versão posterior à esperada e não a aplicou. Reinicie essa réplica para forçar uma nova sincronização.

### Página desatualizada

Depois de alterar código ou logs, execute novamente:

```bash
python3 gera_pagina.py --logs logs/pos_correcoes
python3 -m unittest discover -s tests -v
```

Se novos arquivos de código forem criados, inclua-os em `CODIGOS`, em `gera_pagina.py`, para que sejam publicados e testados na entrega.

---

## 13. Fluxo recomendado para modificações

1. Escreva ou ajuste primeiro o teste que descreve o comportamento.
2. Execute o teste e confirme que ele falha pelo motivo esperado.
3. Implemente a menor alteração necessária.
4. Execute a suíte unitária:

   ```bash
   python3 -m unittest discover -s tests -v
   ```

5. Execute os cenários locais:

   ```bash
   python3 cenarios.py --saida logs/pos_correcoes
   ```

6. Regenere e valide a página:

   ```bash
   python3 gera_pagina.py --logs logs/pos_correcoes
   ```

7. Registre o resultado e eventuais pendências em `ANALISE_PROJETO.md`.
8. Quando houver ambiente, execute os testes obrigatórios em três hosts.

Não altere `base/`: esse diretório contém apenas material de referência.

---

## 14. Referências

- Enunciado: <https://www.inf.ufpr.br/elias/redes/tpRedesII2026-2.html>
- Diagnóstico, arquitetura e to-do list: `ANALISE_PROJETO.md`
- Relatório HTML: `site/relatorio.html`
- Resultado local final: `logs/pos_correcoes/resumo.json`
