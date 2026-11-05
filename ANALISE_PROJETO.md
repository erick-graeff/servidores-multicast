# Análise do TP de Redes II — Grupo de Servidores Multicast

## 1. Contexto e escopo

Este documento consolida a análise do enunciado, da implementação atual, da comunicação UDP, dos testes existentes e da arquitetura do projeto. Também registra a decisão de arquitetura para uma implementação futura.

- **Enunciado:** <https://www.inf.ufpr.br/elias/redes/tpRedesII2026-2.html>
- **Data da análise:** 04/11/2026
- **Método:** leitura estática do código, da página de entrega e dos logs já existentes.
- **Limitação da análise:** os testes não foram reexecutados durante a revisão.
- **Alterações de código:** nenhuma até o início da execução da to-do list; o andamento e as evidências passam a ser registrados na seção 11.
- **Decisão tomada:** seguir futuramente com a arquitetura sugerida neste documento, incluindo um módulo de comunicação reaproveitado por cliente e servidor.
- **Testes no escopo:** definir testes unitários para as funcionalidades sempre que possível, complementando os cenários de integração locais e os testes em três hosts.
- **Restrições da execução autorizada:** trabalhar diretamente na branch `main`, somente neste diretório, sem alterar `base/`, sem commits e sem push.

---

## 2. O que o enunciado exige

O trabalho consiste em construir um servidor tolerante a falhas formado, na realidade, por um grupo de processos servidores.

### 2.1. Funcionamento do grupo

- Cada servidor possui um identificador sequencial: S1, S2, ..., SN.
- Todos os membros conhecem identificador, endereço IP e porta dos demais.
- Deve existir monitoramento interno dos membros.
- Periodicamente, cada membro sem-falha envia um heartbeat por multicast.
- A ausência de heartbeats dentro do limite estabelecido indica falha.
- O modelo de falhas considerado é exclusivamente parada total.
- Ao receber uma requisição, o grupo elege como líder o membro sem-falha de menor identificador.

### 2.2. Comunicação e serviço

- Deve ser utilizado multicast IP/Ethernet.
- O cliente envia sua requisição ao endereço do grupo.
- A dupla define o serviço oferecido, desde que ele permita consulta e alteração.
- Uma consulta é uma leitura respondida diretamente pelo líder.
- Em uma alteração:
  1. o líder executa a operação localmente;
  2. o líder envia a operação aos demais membros;
  3. as réplicas executam a operação;
  4. as réplicas confirmam ao líder;
  5. somente depois disso o líder confirma ao cliente.
- A resposta deve conter o resultado e o identificador, endereço e porta do servidor que atendeu.

### 2.3. Testes e evidências

- A estratégia deve ser explicada e demonstrada claramente.
- Falhas devem ser simuladas matando processos.
- Devem ser executadas requisições com diferentes configurações de membros falhos e sem-falha.
- Os testes precisam ser suficientemente abrangentes para demonstrar a correção.
- **Os logs devem ser produzidos com, no mínimo, três servidores executando em hosts diferentes.**

### 2.4. Entrega

A entrega deve ser uma página Web contendo documentos HTML com:

- relatório da implementação e dos resultados;
- desenhos, diagramas ou figuras que ajudem a compreender a solução;
- código-fonte comentado;
- nomes dos arquivos de código terminados em `.txt`, como `cliente.py.txt` e `servidor.c.txt`;
- logs dos processos cliente e servidores.

Outras orientações do enunciado:

- trabalho em dupla;
- código, testes e relatório produzidos por ambos os integrantes;
- acesso aos trabalhos em 7 de novembro de 2026;
- envio da URL por e-mail com o subject exato `TP REDES II 2026`.

---

## 3. Visão geral da implementação atual

O projeto atual implementa uma conta bancária replicada com as operações:

- `SALDO`: consulta;
- `DEPOSITO <valor>`: escrita;
- `SAQUE <valor>`: escrita, recusada quando não há saldo suficiente.

Os principais arquivos são:

| Arquivo | Responsabilidade atual |
|---|---|
| `servidor.py` | Requisições, replicação, ACKs, sincronização, envio de heartbeats e threads |
| `cliente.py` | CLI, requisições, retransmissões, logs e apresentação das respostas |
| `comunicacao.py` | Canais UDP/JSON injetáveis e configuração de sockets multicast e unicast |
| `conta.py` | Estado da conta, operações e idempotência por `req_id` |
| `membros.py` | Heartbeats recebidos, membros vivos, flags de sincronização e eleição |
| `tests/` | Testes unitários e dublês de comunicação |
| `cenarios.py` | Orquestração dos testes locais, morte de processos e verificação dos resultados |
| `gera_pagina.py` | Geração da página HTML, diagramas, cópia do código e publicação dos logs |
| `config.json` | Configuração local com três processos em `127.0.0.1` |
| `config_lab.json` | Modelo para configuração em três hosts, ainda com IPs placeholder |
| `site/` | Página de entrega, código em `.txt` e logs publicados |
| `logs/` | Baseline e resultados dos 15 cenários locais e das etapas intermediárias |
| `GUIA_DO_PROJETO.md` | Guia de arquitetura, protocolo, execução, arquivos, testes e limitações |
| `base/t2-redes/` | Outro trabalho, baseado em UDP unicast em anel |

A implementação também possui recursos além do mínimo explícito do enunciado:

- retransmissão de requisições pelo cliente com o mesmo `req_id`;
- cache para evitar execução duplicada de escritas;
- retransmissão de `REPLICA` quando faltam ACKs;
- sincronização de estado quando um servidor reinicia;
- resposta informando em quais servidores uma escrita foi replicada.

---

## 4. Cobertura dos requisitos

| Requisito | Situação | Evidência |
|---|---|---|
| Grupo com IDs, IPs e portas conhecidos | Atendido | `servidor.py:127-161`, `config.json:6-10` |
| Heartbeat periódico por multicast | Atendido | `servidor.py:203-207` |
| Detecção de falha por ausência de heartbeat | Atendido | `servidor.py:166-173`, `209-227`, `239-246` |
| Líder é o menor ID sem-falha | Atendido | `servidor.py:175-180`, `299-318` |
| Cliente envia requisição ao grupo multicast | Atendido | `cliente.py:35-50`, `62-88` |
| Serviço permite consulta e alteração | Atendido | `servidor.py:80-121` |
| Resposta contém resultado, ID, IP e porta | Atendido | `servidor.py:287-296` |
| Escrita local, replicação, ACK e resposta | Atendido nos testes locais | Timeout sem ACK não confirma sucesso; versionamento e testes em `tests/test_replicacao.py` e `tests/test_ordenacao.py` |
| Reenvio sem duplicar escrita | Atendido no caminho testado | `servidor.py:95-117`; cenário 9 |
| Testes com parada total | Atendido localmente | `cenarios.py:64-68` usa `SIGKILL` |
| Diferentes configurações de falha | Atendido localmente | `cenarios.py:273-286` |
| Logs com três servidores em hosts diferentes | **Não atendido** | Todos os logs atuais usam `127.0.0.1`; não há `logs/lab/` |
| Relatório HTML com diagramas e resultados | Parcial | Existe, mas contém seção `[A COMPLETAR PELA DUPLA]` |
| Código `.txt` e logs na página | Parcial | Existem, mas há placeholders e uma cópia divergente |

### Conclusão da cobertura

A funcionalidade principal está implementada e demonstrada localmente. As não conformidades de ACK, ordenação e sincronização encontradas na análise inicial foram corrigidas e possuem testes de regressão. A entrega completa ainda depende dos testes e logs em três hosts e da atualização da seção correspondente do relatório.

---

## 5. Avaliação da comunicação UDP

### 5.1. Construção dos sockets no projeto atual

A construção básica dos sockets está adequada ao trabalho.

No servidor:

- `AF_INET + SOCK_DGRAM` implementa UDP: `servidor.py:50`;
- o socket entra no grupo com `IP_ADD_MEMBERSHIP`: `servidor.py:57-59`;
- a interface de envio é configurada com `IP_MULTICAST_IF`: `servidor.py:68`;
- o TTL 1 restringe o tráfego à rede local: `servidor.py:67`;
- `sendto()` e `recvfrom()` são utilizados para os datagramas;
- há dois sockets com finalidades distintas:
  - um para receber o tráfego multicast do grupo;
  - outro para unicast, ACKs, sincronização e respostas ao cliente.

No cliente:

- o socket UDP é vinculado a uma porta efêmera;
- a requisição é enviada ao grupo;
- a resposta unicast chega no mesmo socket, no endereço de origem da requisição.

Esse modelo é coerente com multicast IP sobre Ethernet. Não é necessário utilizar TCP nem sockets Ethernet crus.

Para os testes no laboratório, `config_lab.json` precisa conter os IPs reais e o cliente deve usar a interface correta. O padrão `--iface 0.0.0.0` pode ser ambíguo em hosts com múltiplas interfaces.

### 5.2. Comparação com `base/t2-redes`

O projeto de referência utiliza UDP unicast em anel:

- criação e bind do socket: `base/t2-redes/game_config.py:89-90`;
- envio ao próximo integrante: `game_config.py:120-121`;
- recepção e encaminhamento no anel: `game_config.py:123-137`.

Ele não contém:

- `IP_ADD_MEMBERSHIP`;
- configuração de interface multicast;
- heartbeats;
- eleição de líder;
- replicação com ACKs.

Portanto, o projeto atual utiliza o modelo de comunicação apropriado para este trabalho. O anel do projeto-base não deve substituir a arquitetura multicast. Do projeto-base, aproveitam-se apenas os conceitos básicos de `SOCK_DGRAM`, `sendto`, `recvfrom` e serialização JSON.

---

## 6. Problemas encontrados no protocolo

### 6.1. Resposta sem todos os ACKs — corrigido

A implementação original esperava no máximo 15 segundos e, ao atingir o limite, enviava `ok=True` mesmo com réplicas vivas sem ACK. Além da violação do enunciado, o cliente podia desistir após aproximadamente 12 segundos, antes da resposta do líder.

A espera do líder agora é configurável por `timeout_escrita` e vale 8 segundos nos arquivos de configuração, permanecendo menor que a janela total padrão do cliente, de aproximadamente 12 segundos. Se uma réplica sem-falha ainda não confirmou ao final da espera:

- o líder não envia confirmação de sucesso;
- envia `ok=False` e `erro="REPLICACAO_NAO_CONFIRMADA"`;
- informa em quais servidores houve confirmação;
- registra que o resultado é desconhecido, pois a operação pode ter sido aplicada localmente e em parte das réplicas.

Membros que falham e saem do conjunto de vivos continuam deixando de ser esperados, como no protocolo original. Perda de `REPLICA` e perda de ACK produzem a mesma ausência observável de confirmação no líder e são cobertas pelo teste de timeout com réplica viva.

Testes de regressão: `tests/test_replicacao.py` cobre sucesso após ACK, timeout sem sucesso, ACK duplicado insuficiente e reenvio sem dupla execução; `tests/test_cliente.py` cobre retransmissões e respostas válidas ou atrasadas.

### 6.2. `REPLICA` antigo fazia o saldo regredir — corrigido

A implementação original não possuía sequência e adotava `saldo_lider` mesmo para uma operação já presente no cache. Assim, uma retransmissão antiga podia fazer o saldo voltar de 150 para 100.

`Conta` agora mantém `versao` e o mapa `req_id -> versao`. O líder inclui a versão em cada `REPLICA` e preserva a mesma versão ao reenviar uma requisição já conhecida. Nas réplicas:

- versão menor ou igual à atual recebe ACK sem alterar o estado;
- exatamente a próxima versão é aplicada;
- uma versão com lacuna não é aplicada nem confirmada;
- a correção por `saldo_lider` só pode ocorrer durante a aplicação da próxima versão, nunca por uma mensagem antiga.

Snapshots incluem saldo, cache, versão atual e versões das requisições. `Conta.restaurar()` rejeita snapshots anteriores ao estado local. Testes em `tests/test_conta.py` e `tests/test_ordenacao.py` cobrem duplicação, lacuna, idempotência e restauração.

### 6.3. Corrida entre sincronização e replicação — corrigida

Originalmente, uma réplica podia aplicar `REPLICA` antes de receber `STATE`, confirmar a escrita e depois sofrer sobrescrita por um snapshot antigo.

Agora:

- réplicas não sincronizadas ignoram `REPLICA` e não enviam ACK;
- `REPLICA`, `STATE` e snapshots são serializados por `lock_estado`;
- `STATE` é versionado e não pode substituir um estado mais novo;
- uma retransmissão recebida depois da sincronização é confirmada sem regredir o estado;
- `SYNC_REQ` também marca o reintegrante como vivo, fazendo o líder aguardar seu ACK quando uma escrita ocorrer depois do snapshot.

Os cenários 13 e 14 foram adicionados para o retorno de S2 e S3 com escrita durante a sincronização. O cenário 10 continua cobrindo S1. Os três foram executados com saldo final consistente em todos os servidores.

### 6.4. Limitações já reconhecidas no relatório

O relatório também registra que:

- partições de rede não são tratadas;
- perdas de heartbeats podem produzir mais de um líder temporariamente;
- o estado fica em memória e é perdido quando todos os servidores param;
- o TTL 1 exige hosts na mesma rede local;
- após timeout de replicação, o resultado da escrita pode ficar desconhecido e parcialmente aplicado, embora o cliente receba `ok=False`;
- uma réplica sincronizada que fica com lacuna de versão deixa de confirmar escritas posteriores e, atualmente, precisa ser reiniciada para obter um novo snapshot; não há ressincronização automática da lacuna.

Essas limitações devem ser distinguidas das violações explícitas do enunciado. O modelo exigido considera parada total, não falhas bizantinas ou necessidade de consenso sob partição.

---

## 7. O que os testes atuais comprovam

Os arquivos em `logs/resumo.json` registram:

- 12 cenários;
- 59 verificações;
- nenhum resultado `"ok": false`;
- eleição e troca de líder;
- manutenção do saldo nos cenários executados;
- reenvio sem duplicação no cenário 9;
- reintegração de S1 no cenário 10;
- comportamento quando todos os servidores estão mortos.

Isso é uma boa evidência do caminho feliz em localhost, mas não comprova:

- funcionamento em três hosts diferentes;
- comportamento sob perda, duplicação ou reordenamento de UDP;
- comportamento quando o timeout de ACK termina;
- sincronização correta de réplicas que reiniciam;
- funcionamento com clientes realmente concorrentes.

Uma fragilidade secundária dos testes é que `cenarios.py:97-110` infere o estado das réplicas procurando texto nos logs, em vez de consultar diretamente o estado ou uma interface de teste.

### Resultado local após as correções

A suíte final em `logs/pos_correcoes/` contém **15 cenários e 92/92 verificações aprovadas**. Além dos 12 cenários originais:

- cenário 13: retorno de S2 com escrita durante a sincronização;
- cenário 14: retorno de S3 com escrita durante a sincronização;
- cenário 15: três clientes concorrentes, cinco depósitos de 10 por cliente, saldo final 150 em S1, S2 e S3.

A mesma execução registrou 41/41 testes unitários aprovados. Não foram encontrados `Traceback`, `INCONSISTENCIA`, `REPLICACAO_NAO_CONFIRMADA` ou verificações `ERRO` nos logs dessa execução.

---

## 8. Pendências na entrega HTML

A análise inicial encontrou placeholders de autoria, IPs de laboratório e divergência entre o código publicado e os fontes.

Durante a execução:

- a autoria foi corrigida para Eduardo Camargo Neves e Erick Graeff Petzold;
- `comunicacao.py`, `conta.py`, `membros.py` e os testes foram incluídos na entrega;
- o gerador passou a aceitar `--logs` e foi executado com `logs/pos_correcoes`;
- os 18 arquivos publicados em `site/codigo/` terminam em `.txt` e foram verificados byte a byte contra os fontes;
- os links locais dos HTML gerados foram testados;
- o relatório agora apresenta arquitetura, versionamento, timeout sem falso sucesso, 46/46 testes unitários e 15 cenários locais com 92/92 verificações.

Permanecem somente as pendências externas de 11.8: preencher os IPs reais de `config_lab.json`, produzir os logs em três hosts, acrescentar esses resultados ao relatório e remover o aviso `[A COMPLETAR PELA DUPLA]` da seção de laboratório. O aviso foi mantido deliberadamente para não apresentar a entrega como completa antes dessa evidência.

---

## 9. Avaliação da arquitetura

O principal problema arquitetural não é simplesmente o tamanho dos arquivos, mas a concentração de responsabilidades que possuem motivos diferentes para mudar.

### 9.1. `Conta`: boa coesão

A classe `Conta`, em `servidor.py:92-121`, já é um bom módulo:

- possui estado próprio;
- protege esse estado com lock;
- executa as operações do serviço;
- controla a idempotência pelo `req_id`;
- oferece uma interface pequena: `aplica()` e `consulta()`.

A classe foi extraída para `conta.py` e passou a ter testes unitários independentes de rede.

Ressalva: a correção de saldo em `trata_replica()` está fora de `Conta`. Isso distribui a responsabilidade pela consistência entre duas partes da aplicação. O ideal é a coordenação decidir qual operação deve ser aplicada e em qual ordem, enquanto `Conta` cuida do estado e dos snapshots.

### 9.2. `Servidor`: excesso de responsabilidades

Atualmente `Servidor` cuida de:

1. criação e configuração de sockets;
2. serialização JSON;
3. comunicação multicast e unicast;
4. envio e recepção de heartbeats;
5. manutenção da lista de membros vivos;
6. eleição do líder;
7. coordenação das requisições;
8. replicação e controle de ACKs;
9. sincronização de estado;
10. gerenciamento de threads;
11. tratamento de falhas injetadas.

Isso aparece principalmente em `servidor.py:127-435`.

Essa concentração dificulta testar perguntas como:

- a eleição está correta sem subir três processos?
- o que acontece quando uma mensagem chega duplicada?
- uma réplica não sincronizada pode aplicar uma escrita?
- o líder sempre aguarda os ACKs necessários?
- um `STATE` antigo pode sobrescrever uma operação nova?

Hoje essas situações são testadas indiretamente com processos, threads, sleeps e sockets reais.

### 9.3. `Cliente`: tamanho razoável

`cliente.py` mistura CLI, logs, configuração do socket, criação de `req_id`, retransmissões e apresentação das respostas.

Para um arquivo de 127 linhas, isso é aceitável. A separação mais útil é extrair a infraestrutura de comunicação, sem criar várias camadas adicionais.

### 9.4. Testes e geração da página

- `cenarios.py` cuida da orquestração dos testes;
- `gera_pagina.py` cuida da entrega HTML;
- `config.json` separa configuração e implementação.

Essas separações são adequadas e devem ser preservadas.

---

## 10. Arquitetura decidida

### 10.1. Módulo de comunicação reaproveitável

`comunicacao.py` foi criado como o transporte UDP/JSON reaproveitável do projeto.

O objetivo não deve ser apenas mover funções para outro arquivo. O módulo deve:

- esconder detalhes de sockets e multicast;
- centralizar UDP e JSON;
- apresentar uma interface pequena;
- ser injetado em cliente e servidor;
- permitir uma implementação falsa para testes determinísticos.

Interface implementada em `comunicacao.py`:

```python
class CanalUDP:
    def enviar(self, mensagem: dict, destino: Endereco) -> None:
        ...

    def receber(self, timeout: float | None = None) -> tuple[dict, Endereco]:
        ...

    def fechar(self) -> None:
        ...
```

O módulo esconde:

- criação e bind dos sockets;
- `IP_ADD_MEMBERSHIP`;
- `IP_MULTICAST_IF`, TTL e loop;
- codificação e decodificação JSON;
- configuração de timeout;
- detalhes de `sendto()` e `recvfrom()`.

Construtores implementados para as configurações necessárias:

```python
abrir_canal_cliente(iface)
abrir_canal_unicast(ip, porta, iface)
abrir_canal_multicast(grupo, porta, iface)
```

Reaproveitamento:

- **Cliente:** um canal, usado para enviar ao grupo e receber a resposta unicast.
- **Servidor:** dois canais:
  - um multicast para `REQ`, `HEARTBEAT`, `REPLICA` e `SYNC_REQ`;
  - um unicast para envio de mensagens e recepção de `ACK` e `STATE`.

O `main()` monta os canais e os entrega ao `Cliente` ou `Servidor`, que não criam mais seus próprios sockets.

### 10.2. O que não deve ficar no módulo de comunicação

O transporte não deve conhecer as regras do trabalho.

Não são desejáveis métodos como:

```python
enviar_heartbeat()
enviar_deposito()
eleger_lider()
replicar_escrita()
sincronizar_servidor()
```

Também não se deve centralizar todas as políticas de retransmissão, porque elas são diferentes:

- cliente reenvia `REQ` a cada 2 segundos, até 6 tentativas;
- líder reenvia `REPLICA` a cada 1 segundo;
- heartbeat possui periodicidade própria.

Divisão pretendida:

| Responsabilidade | Local sugerido |
|---|---|
| UDP, multicast, JSON e timeout do socket | `comunicacao.py` |
| Criar `req_id`, reenviar `REQ`, interpretar comandos | `cliente.py` |
| Saldo, operações, idempotência e snapshot | `conta.py` |
| Heartbeats, eleição, ACKs, replicação e sincronização | `servidor.py` |
| Formatos das mensagens | Inicialmente nos consumidores; opcionalmente `protocolo.py` |
| Execução dos testes | `cenarios.py` |
| Geração da entrega | `gera_pagina.py` |

As dependências devem apontar em uma direção: cliente e servidor podem importar comunicação; comunicação não deve importar cliente nem servidor.

### 10.3. Estrutura mínima recomendada

```text
comunicacao.py   # UDP/JSON, configuração multicast e canais
conta.py         # Estado e operações do serviço
servidor.py      # Coordenação do grupo e protocolo de replicação
cliente.py       # CLI, requisições e retransmissões
cenarios.py      # Testes de integração
gera_pagina.py   # Relatório e entrega
```

Se `servidor.py` continuar difícil de entender depois dessa separação, uma refatoração posterior poderá introduzir:

```text
membros.py       # Heartbeats recebidos, membros vivos e eleição
```

Não é necessário começar criando muitos módulos. Comunicação e conta já oferecem boa parte do benefício.

### 10.4. Principal benefício: testabilidade

Além do reaproveitamento, a comunicação separada cria um seam entre o protocolo e a rede.

Uma implementação falsa poderia seguir a mesma interface:

```python
class CanalFake:
    def enviar(self, mensagem, destino):
        # Guarda, descarta, duplica ou reordena mensagens.
        ...

    def receber(self, timeout=None):
        # Entrega mensagens previamente programadas.
        ...
```

Isso permitiria testar deterministicamente:

- perda de `REPLICA`;
- perda de `ACK`;
- duplicação de datagramas;
- entrega fora de ordem;
- `STATE` antigo chegando depois de uma escrita;
- heartbeat expirando;
- escolha do menor ID;
- líder tentando responder sem todos os ACKs.

Apenas mover `codifica()` e `envia_para()` para outro arquivo, mantendo os sockets escondidos dentro de `Servidor`, reduziria linhas mas não proporcionaria esse benefício.

### 10.5. Testes unitários como parte do escopo

Os testes unitários passam a fazer parte explícita do escopo do projeto. Eles devem complementar, e não substituir, os cenários de integração já existentes e os testes obrigatórios em três hosts.

Sempre que possível, os testes devem exercitar as funcionalidades pelas interfaces públicas dos módulos, sem depender de rede real, processos externos ou sleeps longos. `CanalFake`, relógio controlado e outras dependências falsas devem ser usados quando ajudarem a tornar os testes rápidos e determinísticos.

Cobertura unitária pretendida:

| Funcionalidade | Casos de teste prioritários |
|---|---|
| Conta | Saldo inicial; depósito; saque; saque sem saldo; operação desconhecida; repetição do mesmo `req_id`; preservação do saldo; snapshot e restauração quando disponíveis |
| Comunicação | Codificação e decodificação JSON; envio ao destino correto; devolução da origem; timeout de recepção; tratamento de datagrama inválido; configuração dos sockets multicast usando socket falso ou mock |
| Membros e eleição | Membro vivo antes do timeout; membro falho depois do timeout; escolha do menor ID; troca de líder; membro que retorna; comportamento durante a inicialização |
| Cliente | Criação do `req_id`; reutilização do mesmo ID nas retransmissões; limite de tentativas; resposta válida encerrando as tentativas; descarte de resposta com outro `req_id`; ausência total de resposta |
| Replicação | Execução local antes de `REPLICA`; espera pelos ACKs; retransmissão quando falta ACK; não confirmação de sucesso sem os ACKs exigidos; ACK repetido; escrita repetida sem execução dupla |
| Ordenação e consistência | `REPLICA` duplicado ou atrasado não pode fazer o saldo regredir; mensagens fora de ordem; sequência de escritas; concorrência entre requisições quando for isolável |
| Sincronização | Snapshot consistente; `STATE` antigo não pode sobrescrever escrita nova; réplica não sincronizada não confirma operações indevidamente; retorno de S1, S2 e S3 |

Os testes de sockets devem usar dublês para verificar a configuração sem exigir multicast real. Pelo menos alguns testes de integração com UDP e multicast reais continuarão necessários, pois mocks não comprovam o comportamento do sistema operacional e da rede.

Sugestão de organização futura:

```text
tests/
    test_conta.py
    test_comunicacao.py
    test_membros.py
    test_cliente.py
    test_replicacao.py
    test_sincronizacao.py
```

A estrutura e os nomes podem ser ajustados aos módulos que efetivamente existirem; não é necessário criar arquivos de teste para módulos hipotéticos. Como o projeto utiliza apenas a biblioteca padrão, `unittest` é uma opção suficiente e evita adicionar dependências sem necessidade.

Critério geral:

- **teste unitário:** valida uma regra ou funcionalidade isolada, com dependências controladas;
- **teste de integração local:** valida processos comunicando-se por UDP/multicast em uma máquina;
- **teste de laboratório:** valida a distribuição real em pelo menos três hosts e produz os logs exigidos pelo enunciado.

---

## 11. To-do list — o que precisa ser feito

Esta é a lista operacional do projeto. As seções anteriores explicam o diagnóstico e o motivo de cada tarefa. Nenhum item abaixo foi executado como parte da revisão estática; a execução autorizada passa a ser registrada aqui.

**Regras de verificação:**

- Um item só pode ser marcado como concluído depois da verificação indicada em sua subseção.
- Testes unitários serão executados com `python3 -m unittest discover -s tests -v` quando a estrutura `tests/` existir.
- Testes de integração locais usarão diretórios de saída separados para não apagar a baseline nem os logs originais.
- Tarefas de documentação e geração da página serão verificadas pelos artefatos produzidos e por testes dos links e das cópias publicadas.
- A subseção 11.8 depende de IPs e hosts externos. Ela permanecerá explicitamente pendente até que a dupla execute ou disponibilize esse ambiente; os testes locais não serão apresentados como substitutos.

### 11.1. Preservar a baseline atual

- [x] Executar os cenários atuais antes da refatoração.
- [x] Guardar os resultados e os logs dessa execução para comparação posterior.
- [x] Registrar eventuais falhas já existentes, sem alterar o comportamento para fazê-las passar.

**Verificação:** executar `python3 cenarios.py --saida logs/baseline_pre_refatoracao`; exigir término sem exceção, 12 cenários presentes no resumo e todos marcados como `PASSOU`. O resumo e os logs precisam permanecer nesse diretório.

### 11.2. Preparar a base de testes

- [x] Criar a estrutura `tests/` conforme os módulos forem sendo organizados.
- [x] Definir os dublês necessários, incluindo `CanalFake` e, quando útil, um relógio controlado.
- [x] Adicionar testes unitários para as regras que já puderem ser isoladas sem mudar o comportamento atual.
- [x] Manter os testes unitários independentes de rede real, processos externos e sleeps longos sempre que possível.

**Verificação:** executar `python3 -m unittest discover -s tests -v`; todos os testes precisam passar e os dublês devem permitir executá-los sem abrir sockets de rede.

### 11.3. Separar a comunicação

- [x] Criar `comunicacao.py` ou `transporte_udp.py` com a interface pequena do `CanalUDP`.
- [x] Centralizar UDP, JSON, bind, timeout e configuração multicast nesse módulo.
- [x] Implementar os construtores necessários para cliente, unicast do servidor e multicast do grupo.
- [x] Injetar os canais no `Cliente` e no `Servidor`, em vez de deixar essas classes criarem seus próprios sockets.
- [x] Manter heartbeat, eleição, replicação, sincronização e políticas de retransmissão fora do transporte.
- [x] Adicionar testes unitários para serialização, envio, recepção, timeout, origem/destino e configuração dos sockets com dublês.
- [x] Executar novamente todos os cenários locais para confirmar que a extração não alterou o comportamento.

**Verificação:** executar a suíte unitária e `python3 cenarios.py --saida logs/pos_comunicacao`; exigir todos os testes e 12 cenários aprovados, com as mesmas 59 verificações da baseline.

### 11.4. Separar as demais responsabilidades quando fizer sentido

- [x] Avaliar a extração de `Conta` para `conta.py`, mantendo saldo, operações, idempotência e snapshots coesos.
- [x] Adicionar testes unitários de saldo inicial, depósito, saque, saldo insuficiente, operação desconhecida e repetição de `req_id`.
- [x] Avaliar se `membros.py` é necessário para isolar heartbeats, membros vivos e eleição.
- [x] Se `membros.py` for criado, testar timeout, menor ID, troca de líder, retorno de membro e inicialização.
- [x] Evitar criar módulos ou camadas adicionais sem uma responsabilidade clara.

**Verificação:** executar a suíte unitária completa e os testes de importação dos módulos; validar que as dependências não formam ciclos e que cada módulo extraído é exercitado por pelo menos um teste de comportamento. Uma decisão de não extrair `membros.py` deve ser registrada com sua justificativa.

### 11.5. Corrigir a confirmação das escritas

- [x] Definir testes para perda de `REPLICA`, perda de ACK, ACK duplicado e réplica que continua viva sem confirmar.
- [x] Alterar a regra para não informar sucesso ao cliente sem os ACKs exigidos dos membros considerados sem-falha.
- [x] Definir e documentar o comportamento quando a espera terminar sem esses ACKs, sem transformar timeout em confirmação de sucesso.
- [x] Alinhar os timeouts e a quantidade de tentativas de cliente e servidor.
- [x] Verificar que retransmissões não executam a mesma escrita duas vezes.

**Verificação:** executar os testes unitários de replicação e cliente, incluindo perda e duplicação de ACK; demonstrar que uma réplica viva sem ACK não gera resposta de sucesso e que o saldo não muda duas vezes para o mesmo `req_id`.

### 11.6. Corrigir ordenação e sincronização

- [x] Definir um mecanismo de ordenação ou versionamento das escritas para impedir que mensagens antigas alterem estado mais novo.
- [x] Impedir que `REPLICA` duplicado, atrasado ou fora de ordem faça o saldo regredir.
- [x] Impedir que `STATE` antigo sobrescreva uma escrita já aplicada ou confirmada.
- [x] Impedir que uma réplica não sincronizada processe ou confirme operações indevidamente.
- [x] Adicionar testes de regressão para duplicação, atraso, reordenamento e sequência de escritas.
- [x] Testar o retorno de S1, S2 e S3, inclusive com escritas acontecendo durante a sincronização.

**Verificação:** executar testes unitários e de regressão com entrega controlada de `REPLICA` e `STATE`; todos precisam demonstrar que mensagens antigas não reduzem o saldo nem sobrescrevem operações mais novas.

### 11.7. Ampliar os testes de integração local

- [x] Manter os 12 cenários existentes e corrigir qualquer regressão identificada.
- [x] Adicionar testes de perda, duplicação, atraso e reordenamento de mensagens usando os dublês.
- [x] Adicionar testes com clientes concorrentes quando esse comportamento for suportado.
- [x] Executar testes de integração com UDP e multicast reais, pois os dublês não validam o sistema operacional nem a rede.
- [x] Conferir a consistência do estado em todas as réplicas sem-falha.

**Verificação:** executar a suíte unitária completa e `python3 cenarios.py --saida logs/pos_correcoes`; exigir todos os testes e cenários aprovados, inclusive os novos cenários de regressão.

### 11.8. Executar no laboratório — dependência externa

- [ ] Preencher `config_lab.json` com os IPs reais das máquinas.
- [ ] Configurar corretamente a interface multicast do cliente e dos servidores.
- [ ] Executar pelo menos três servidores em hosts diferentes.
- [ ] Executar os cenários principais de leitura, escrita, falha do líder, falha de réplica e múltiplas falhas.
- [ ] Simular parada total com `kill` e coletar os logs de cliente e servidores.
- [ ] Guardar os logs de laboratório em `logs/lab/` e registrar os resultados obtidos.

**Bloqueio atual:** este ambiente não fornece três hosts nem os IPs reais do laboratório. Estes itens não são executáveis localmente e permanecem pendentes até a dupla disponibilizar ou operar esse ambiente.

**Verificação externa:** para cada host, conferir no log o IP real e o ID do servidor; executar os cenários e validar no `logs/lab/resumo.json` os resultados esperados. Só marcar a subseção quando os arquivos existirem e demonstrarem três IPs de hosts distintos, heartbeats, eleições, escritas replicadas e reações aos `kill`.

### 11.9. Finalizar a entrega

- [x] Substituir os placeholders de autoria nos fontes e no gerador.
- [ ] Remover o aviso `[A COMPLETAR PELA DUPLA]` somente após a conclusão de 11.8.
- [x] Atualizar o relatório com a arquitetura final, o protocolo, os testes unitários e os testes de integração local.
- [ ] Acrescentar os resultados de laboratório ao relatório após a conclusão de 11.8.
- [x] Documentar as limitações restantes sem apresentar comportamento não testado como garantido.
- [x] Regenerar `site/` para sincronizar código, relatório e logs.
- [x] Verificar se todos os arquivos de código publicados terminam em `.txt` e se os links da página funcionam.
- [x] Verificar que `site/codigo/servidor.py.txt` e os demais arquivos publicados correspondem às versões atuais.
- [x] Fazer uma revisão final procurando placeholders, logs antigos e instruções de execução desatualizadas.

**Verificação:** executar `python3 gera_pagina.py --logs logs/pos_correcoes` e os testes automatizados da entrega; validar os HTML gerados, a existência dos arquivos `.txt`, a igualdade entre código-fonte e cópias publicadas e a resolução de todos os links locais. Os placeholders só poderão ser considerados eliminados quando não houver ocorrências nos artefatos gerados. A parte do relatório que depende do laboratório permanece pendente enquanto 11.8 estiver pendente.

### 11.10. Critérios de conclusão

- [x] Todos os testes unitários implementados passam.
- [x] Todos os testes de integração local passam.
- [ ] Existem logs válidos de pelo menos três servidores em hosts diferentes.
- [x] O líder não confirma uma escrita sem os ACKs exigidos.
- [x] Mensagens antigas ou duplicadas não fazem o estado regredir nos testes de regressão.
- [ ] A página final não contém placeholders nem código/logs desatualizados.

### 11.11. Registro de execução

- **Pré-execução — concluída:** todos os grupos de tarefas receberam critérios de verificação; a etapa de laboratório foi identificada como dependência externa. Restrições registradas: alterações somente neste diretório, exceto `base/`; implementação autorizada na `main`; sem commits e sem push.
- **11.1 — concluída e verificada:** `python3 cenarios.py --saida logs/baseline_pre_refatoracao` terminou sem exceção, com 12/12 cenários e 59/59 verificações aprovadas. Os logs foram preservados em `logs/baseline_pre_refatoracao/`. Nenhuma falha de cenário foi observada e nenhum código de produção foi alterado. A contagem anterior de 60 verificações estava incorreta; os resumos original e novo confirmam 59.
- **11.2 — concluída e verificada:** criados `tests/__init__.py`, `tests/doubles.py`, `tests/test_doubles.py` e `tests/test_conta.py`. O `CanalFake` implementa envio, recepção programada, cópia das mensagens e fechamento em memória. Um relógio controlado será introduzido somente quando uma funcionalidade o exigir. `python3 -m unittest discover -s tests -v`: 10/10 testes aprovados em 0,001 s, sem sockets reais, processos ou sleeps. Os testes do `CanalFake` falharam primeiro por ausência do módulo; os seis testes de `Conta` caracterizam o comportamento existente antes da extração.
- **11.3 — concluída e verificada:** criado `comunicacao.py` com `CanalUDP`, JSON, timeout e os três construtores de canais. `Servidor` recebe os canais de grupo e unicast; `Cliente` recebe seu único canal; os sockets são montados somente nos respectivos `main()`. Adicionados `tests/test_comunicacao.py` e `tests/test_injecao.py`. RED observado por ausência do módulo e pelas antigas assinaturas; GREEN: 19/19 testes unitários. Regressão com `python3 cenarios.py --saida logs/pos_comunicacao`: 12/12 cenários, 59/59 verificações e resumo idêntico à baseline.
- **11.4 — concluída e verificada:** extraídos `conta.py` e `membros.py`. `Membros` encapsula heartbeats, conjunto de vivos, flags `sinc` e eleição, com relógio injetável. Adicionados sete testes para estado inicial, timeout exato, renovação, retorno, mudança de sincronização e heartbeats próprios/desconhecidos. RED observado pela ausência dos módulos; GREEN: 26/26 testes unitários e importações sem ciclos. Regressão em `logs/pos_separacao_responsabilidades/`: 12/12 cenários, 59/59 verificações e resultados idênticos à baseline. Não foram criadas camadas adicionais.
- **11.5 — concluída e verificada:** criados `tests/test_replicacao.py` e `tests/test_cliente.py`, com relógio e condição de ACK controlados. RED: os testes de réplica viva sem ACK e ACK duplicado insuficiente falharam porque a resposta original tinha `ok=True`. GREEN: timeout de escrita configurável em 8 s, resposta `ok=False` com `REPLICACAO_NAO_CONFIRMADA`, retransmissões preservadas e idempotência verificada. A janela total padrão do cliente permanece em aproximadamente 12 s. Resultado: 33/33 testes unitários; cenários 1, 8, 9 e 11 aprovados em `logs/pos_ack/`. Uma asserção do teste de retransmissão teve seus argumentos invertidos durante o desenvolvimento; o teste foi corrigido e toda a suíte foi repetida.
- **11.6 — concluída e verificada:** `Conta` ganhou versões, mapa de versões por requisição, snapshots e restauração que rejeita estado antigo. `REPLICA` carrega versão; duplicados antigos recebem ACK sem mutação, lacunas não são aplicadas/confirmadas e réplicas não sincronizadas não aplicam escritas. `lock_estado` serializa réplica, estado e snapshots. `SYNC_REQ` marca o reintegrante como vivo para fechar a corrida entre snapshot e nova escrita. RED reproduziu regressão 150→100, lacuna aplicada e escrita antes da sincronização. GREEN: 41/41 testes unitários. Cenários 10, 13 e 14 aprovados, cobrindo retorno de S1, S2 e S3, os dois últimos com escrita durante a sincronização; saldo final 175 em todos nos cenários 13/14.
- **11.7 — concluída e verificada:** adicionado o cenário 15, com três clientes concorrentes e 15 escritas simultâneas no total. Executados `python3 -m unittest discover -s tests -v` e `python3 cenarios.py --saida logs/pos_correcoes`: 41/41 testes unitários, 15/15 cenários e 92/92 verificações. Todos os cenários usaram UDP/multicast reais; os testes com dublês cobriram perda, duplicação, atraso e lacuna. Busca nos logs finais não encontrou exceções, inconsistências, timeouts de replicação ou verificações com erro.
- **11.8 — bloqueada por dependência externa:** não há neste ambiente três hosts do laboratório nem seus IPs reais. Nenhum item foi marcado como concluído e nenhum log local foi copiado ou apresentado como evidência de laboratório.
- **11.9 — parcialmente concluída, com somente as dependências de laboratório pendentes:** autoria corrigida; `gera_pagina.py` aceita `--logs`, publica os novos módulos/testes e documenta arquitetura, versões, snapshots e timeout sem falso sucesso. Criado `tests/test_entrega.py`; RED inicial pela antiga assinatura de `gera()`, depois 5/5 testes de geração, links, resultados, autoria e cópias exatas. `python3 gera_pagina.py --logs logs/pos_correcoes` regenerou o site real. Suíte completa: 46/46 testes. Verificação adicional confirmou 18 arquivos `.txt` íntegros e sincronizados. Permanecem pendentes apenas preencher IPs/logs de laboratório, acrescentar seus resultados e remover o aviso da seção 8 após 11.8.
- **11.10 — verificação executada; projeto local concluído, entrega global ainda pendente de laboratório:** foram marcados como satisfeitos somente os critérios com evidência: 46/46 testes unitários, 15/15 cenários e 92/92 verificações locais, ausência de falso sucesso sem ACK e proteção contra regressão por mensagens antigas. Os critérios de logs em três hosts e página sem qualquer placeholder permanecem desmarcados. O site foi regenerado novamente após documentar as limitações residuais. A revisão independente por subagente foi tentada, mas o provedor excedeu o timeout e não produziu um veredito; isso não foi tratado como aprovação. A revisão estática direta de locks, failover, versões e sincronização não identificou novo bloqueador no modelo de parada total e registrou a limitação de recuperação manual após lacuna prolongada. Os diretórios `__pycache__/` gerados pelos testes na raiz e em `tests/` foram removidos após a verificação.
- **Documentação adicional — concluída:** criado `GUIA_DO_PROJETO.md`, com explicação do serviço e do protocolo, relação entre os arquivos, injeção dos canais, execução rápida e manual, preparação dos três hosts, testes, estrutura dos logs, limitações e solução de problemas. O guia deixa explícito que a etapa de laboratório permanece pendente.

---

## 12. Veredito final

- **Funcionalidade principal:** implementada e demonstrada em localhost, com 15 cenários e 92/92 verificações.
- **Uso de UDP e multicast:** correto na construção dos sockets e no modelo de comunicação.
- **Protocolo de replicação:** as falhas iniciais de confirmação sem ACK, regressão por mensagens antigas e sincronização foram corrigidas e possuem testes de regressão.
- **Arquitetura:** comunicação, conta e membros foram separados; `Servidor` permanece responsável pela coordenação do protocolo, e as dependências são injetáveis.
- **Testes:** 46/46 testes unitários e 15/15 cenários de integração local aprovados; testes em três hosts continuam obrigatórios para a entrega final.
- **Limitações residuais documentadas:** partições não são tratadas, timeout pode deixar resultado desconhecido e uma lacuna prolongada de versões ainda exige reinício para ressincronização.
- **Entrega:** parcialmente finalizada. Código e logs locais estão sincronizados no site, mas faltam os IPs e logs reais de três hosts, seus resultados no relatório e a remoção do aviso de laboratório.
