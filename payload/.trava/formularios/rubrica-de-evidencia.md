# RUBRICA DE EVIDÊNCIA

Esta rubrica ajuda a classificar a força de uma prova antes de ela aparecer numa
resposta final, revisão ou laudo. Ela não emite selo e não substitui o contrato.
Serve para impedir que evidência fraca seja vendida como certeza forte.

---

## Escala

| Nível | Nome | Serve para entregar? | Exemplo |
|---|---|---|---|
| E0 | narrativa | não | "implementei", "parece bom", "deve funcionar" |
| E1 | artefato citado | não sozinho | arquivo criado, diff, screenshot solto |
| E2 | comando executado | depende | teste/lint/build com saída e código de retorno |
| E3 | selo válido | sim, para o escopo do selo | `./trava selo conferir testes-verdes` |
| E4 | revisão independente | sim, para julgamento técnico | fiscal com `arquivo:linha` reais |
| E5 | bancada humana válida | sim, para experiência | laudo com duração, jornada e veredito |
| E6 | canal protegido | sim, para autorização | ASK/TTY/branch protection fora do alcance do agente |

Regra: uma entrega final de produto não pode se apoiar em E2 quando o contrato
exige E5. Teste automatizado não vira bancada por insistência verbal.

---

## Perguntas de classificação

1. **Quem produziu a evidência?** O executor, um fiscal, um humano, o runtime ou
   um servidor externo?
2. **Ela está ligada ao fingerprint atual?** Se o código mudou depois, a prova
   descreve outra versão.
3. **Ela pode ter sido fabricada pelo mesmo agente?** Se sim, trate como fraca
   até haver verificação externa.
4. **Ela mede o que afirma medir?** `curl 200` mede disponibilidade de processo,
   não experiência de uso.
5. **Ela tem caminho de reprodução?** Um revisor consegue repetir ou conferir?

---

## Tradução para linguagem de entrega

| Se você tem | Pode dizer | Não pode dizer |
|---|---|---|
| diff apenas | alterei os arquivos X e Y | está funcionando |
| teste verde | a suíte automatizada passou | o usuário consegue usar |
| screenshot | a tela renderizou neste estado | a interação foi validada |
| fiscal aprovado | houve revisão técnica independente | houve aprovação humana de uso |
| bancada aprovada | a experiência foi usada e aprovada | não há bugs |
| ASK/TTY aprovado | o usuário autorizou a passagem | o usuário validou tudo fora do escopo |

---

## Padrão mínimo por tipo de afirmação

| Afirmação | Evidência mínima |
|---|---|
| "compilei" | comando de build com `rc=0` |
| "testei" | comando ou roteiro reproduzível, mais escopo |
| "revisei" | referências `arquivo:linha` e veredito |
| "a tela está usável" | bancada humana ou operador com reprovação possível |
| "entregue" | declaração formal com provas no disco |
| "não entregue" | bloqueio literal e próximo passo honesto |

---

## Antídoto contra excesso de confiança

Antes de promover uma evidência de nível, escreva a frase mais limitada que ela
permite. Só depois decida se precisa de prova mais forte.

Exemplo:

```text
Evidência: npm test saiu 0.
Frase limitada: a suíte automatizada existente passou.
Não cobre: UX, fluxo manual, regressão visual, casos não testados.
Próxima prova necessária: revisão cruzada e bancada.
```

Se a frase limitada não sustenta a conclusão, a conclusão ainda não existe.

