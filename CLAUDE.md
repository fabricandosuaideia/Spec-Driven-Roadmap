# CLAUDE.md — Contrato de método deste repositório

> Este arquivo não diz **o que** a skill faz — isso está no [`README.md`](README.md), no
> [`SKILL.md`](SKILL.md) e em [`references/`](references/). Ele guarda **como se trabalha aqui**:
> técnicas que foram testadas neste repositório e que funcionaram, para não serem redescobertas a
> cada sessão.
>
> Cada lição vem com a evidência que a tornou crível. Os números são de execuções reais registradas
> no [`CHANGELOG.md`](CHANGELOG.md), não de opinião — e vários deles são defeitos que o mantenedor
> cometeu e mediu depois. Estão aqui porque o padrão é mais útil que o pudor.
>
> Origem: a sequência de releases da v3.4.0 à v3.13.0. As lições generalizam para outros projetos;
> a evidência é local.

---

## 1. Mudança em prosa não vale nada até ser executada

**A lição mais cara da sessão.** Nove releases seguidas de revisão de prosa — leitura adversarial,
verificação cruzada, contagens conferidas — não acharam nada do que **uma única execução** achou.

Pior: toda vez que uma correção de prosa foi embarcada sem execução, a execução seguinte achou
defeito nela. Inclusive nas correções feitas para consertar defeitos:

```
3.6.1  fechou 3 graves  →  criou 2
3.10.0 fechou 4 graves  →  criou 1 (que o rerun pegou)
3.12.0 fechou 1 grave   →  criou 2 (um deles quebrando a mesma regra que consertava)
```

**Portanto:** ao editar procedimento, especificação, prompt ou qualquer artefato que outra pessoa (ou
agente) vai *executar*, planeje a execução junto com a edição. "Reli e está certo" não é verificação
— foi exatamente o que precedeu cada um dos casos acima.

## 2. Quando uma regra pode virar script, faça

Quatro vezes neste repositório uma regra escrita virou código, sempre pelo mesmo motivo: **procedimento
escrito não roda contra caso de teste.**

O caso definitivo: um procedimento de migração destrutiva foi **reprovado três vezes seguidas** por
revisão adversarial. Reescrito como script, a primeira execução expôs um quarto defeito que nenhuma
das três revisões podia ver, e uma quarta rodada contra 54 fixtures achou mais cinco — incluindo dois
que só apareciam rodando comandos `git` de verdade.

**Sinais de que uma regra deveria ser script:** ela tem ordem de operações; ela tem caminho de
rollback; ela deriva um valor de outro lugar; ela é verificável por comparação. Se você está
escrevendo "nunca faça X antes de Y" em prosa, considere que uma função faz isso melhor.

## 3. Verificador sem chamador é decoração

Um script de consistência existiu por duas releases **sem nenhum chamador**: fora dos instaladores,
não citado em documento nenhum, sem CI. Só rodava quando alguém lembrava — e memória falhando é
exatamente a doença que ele existia para pegar.

> Um verificador que ninguém invoca é **pior** que nenhum: produz a crença numa rede sem a rede.

**Portanto:** ao criar uma checagem, decida no mesmo commit **onde ela é invocada** e escolha um
ponto por onde o processo não passa ao largo. Aqui foi o script de bump de versão — não se corta um
release sem bumpar.

## 4. Constante declarada sem leitor apodrece

Duas tabelas declarativas foram embarcadas com **zero leitores**. Uma delas guardava um fato
**errado** (listava 7 itens onde o canônico eram 6) — parado no repositório, invisível, porque nada
a consultava.

Virou checagem automática: *toda constante de módulo precisa ser lida em algum lugar do próprio
arquivo.* É a única verificação que ataca a doença em vez do sintoma.

## 5. Verifique o remédio, não só o achado

Taxa medida ao longo da sessão, em três lotes:

```
6 remédios refutados de N  →  26 de 31 precisaram de correção  →  5 de 7 rejeitados na triagem
```

Um remédio errado, aplicado, **introduz defeito enquanto parece progresso**. Exemplos reais pegos
antes de escrever: um conserto que faria um laço de propagação girar para sempre; uma cláusula que
recusaria semear uma seção em construção; um check que inventava um artefato inexistente.

**Portanto:** entre "achado confirmado" e "aplicar", insira uma fase que responda **duas** perguntas
separadas — *(a) o defeito ainda existe hoje?* e *(b) o remédio proposto quebra alguma outra coisa?*
— relendo o trecho inteiro que a correção altera. Descartar é resultado legítimo, e a lista de
descartes costuma ser mais informativa que a de aplicados.

## 6. Num portão, pular em silêncio é pior que falhar

Um linter tinha o princípio "pular em vez de chutar", certo para arquivo ilegível e **errado** para
item ilegível: transformava falha total de parse em aprovação. Um roadmap com dependência circular e
uma feature de 40 tarefas passava com `0 failed`, exit 0.

**Regra:** se a unidade que você deveria julgar não pôde ser lida, isso é **falha**, não silêncio.
Verde vazio é a pior saída que um portão pode dar, porque desliga a atenção de quem lê.

## 7. Meça antes de propor; não invente número

Dois números foram publicados sem medição — "300 linhas" e "29 achados" — e os dois estavam
errados. O primeiro estava errado **em espécie**: a distância real não era dentro do arquivo, era
entre arquivos, e uma ferramenta baseada em proximidade teria pego 1 caso de 7.

A medição também mudou uma decisão de desenho: contar os fatos duplicados (64 candidatos, sem
saturar) provou que um registro manual cobriria ~13% e viraria mais uma coisa a derivar. A conclusão
correta foi **não construir** o mecanismo proposto.

**Portanto:** toda afirmação quantitativa vem de um comando que você rodou. Se não mediu, escreva
"não medido" — é mais útil que uma estimativa que parece dado.

## 8. Para testar execução, use agentes sem histórico

Quem escreveu o procedimento é o **pior leitor possível** dele: sabe o que ele *deveria* dizer.

Instruções que fizeram a diferença nos testes daqui:

- **"Siga literalmente."** Diante de ambiguidade, seguir a leitura mais literal e registrar — nunca
  preencher a lacuna com bom senso. Um agente que conserta o procedimento enquanto executa esconde
  exatamente o que se quer ver.
- **"Atrito é o produto."** Declarar que travar, improvisar, achar contradição são o *resultado*, não
  efeito colateral. Uma execução que reporta zero atrito é suspeita de não ter seguido o texto.
- **Não contar o que mudou.** Para validar uma mudança, o executor não deve saber qual é. Se o texto
  só funciona com alguém explicando, ele não funciona.

A métrica mais útil que saiu disso: a proporção de atrito do tipo **"improvisou"** — agente decidindo
algo que o procedimento deveria ter decidido. Caiu de 56% para 33% e apontou exatamente o que
consertar.

## 9. Isole o ambiente de teste

Sete execuções concluídas ficaram lado a lado sob o mesmo diretório pai. Qualquer uma podia fazer
`ls ..` e ver os resultados das outras para a mesma entrada.

**Portanto:** o diretório pai do projeto de teste contém **só ele**. E arquive o estado anterior antes
de limpar — ele é a base de comparação de tudo que foi medido, e apagá-lo custa o "antes" dos números.

## 10. Plante defeitos conhecidos para tornar qualidade mensurável

O PRD de teste levou **sete ambiguidades plantadas de propósito**. Isso transformou "a regra de nunca
decidir ambiguidade funciona?" de impressão em placar: **5 de 7 → 7 de 7**.

Sem os defeitos plantados não há como saber se uma correção funcionou. Com eles, a resposta é um
número, e regressão fica visível.

**Complemento honesto que vale copiar:** peça ao executor que **declare quando decidiu em silêncio**,
deixando claro que isso é o dado e não falha dele. Foi assim que apareceu o desconto que importa —
7/7 pela métrica "ninguém preencheu lacuna em silêncio", mas 4/7 pela métrica "um humano decidiu de
fato".

---

## Padrão que atravessa tudo

**Acréscimo sem reconciliação.** Toda vez que uma release acrescentou um fato num lugar, os lugares
que **escrevem**, **auditam** e **documentam** esse fato ficaram na versão anterior. Explicou 15 de 37
achados numa revisão completa, e voltou a acontecer duas releases depois, cometido enquanto se
consertava outra coisa.

Duplicar fato de propósito — para cada arquivo ser autossuficiente — é uma escolha defensável. Não
ter mecanismo para manter as cópias em sincronia não é. Enquanto isso depender de memória do
mantenedor, a memória vai falhar; aqui falhou em pelo menos cinco fatos distintos em duas releases — que é por que
`scripts/check-consistency.py` existe.

## O que não funcionou

Registrado para não ser tentado de novo:

- **Registro manual de fatos** (`facts.yaml` e afins) para manter cópias em sincronia. Medido: cobre
  ~13% das afirmações normativas, precisa de manutenção manual, e o próprio registro deriva — as duas
  tabelas declarativas deste repositório apodreceram em semanas.
- **Portão de release por julgamento de LLM** sem determinismo. Sem CI, sem hook e com custo por
  release, vira teatro: gera um artefato que *parece* verificação.
- **Cortar arquivo por tamanho.** Dividir só funcionou onde havia uma costura real — dois gatilhos e
  dois leitores no mesmo arquivo. Cortar pelo número de linhas é o tipo de cirurgia que introduziu
  defeito três vezes.
