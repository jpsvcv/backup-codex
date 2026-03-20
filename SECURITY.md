# Politica de Seguranca

## Escopo

Este projeto lida com backups do estado local do Codex e pode manipular arquivos sensiveis, incluindo configuracoes, historico local e credenciais opcionais.

Por isso, problemas de seguranca devem ser reportados com cuidado, especialmente se puderem:

- expor `auth.json`, `cap_sid` ou outros segredos
- permitir sobrescrita destrutiva de diretorios indevidos
- aceitar backups adulterados como validos
- executar escrita fora do destino esperado

## Versoes com suporte

As correcoes de seguranca sao priorizadas para a linha mais recente publicada no GitHub Releases.

| Versao | Suporte |
| --- | --- |
| `0.1.x` | Sim |

## Como reportar uma vulnerabilidade

Se o problema puder expor dados, credenciais ou causar perda de ficheiros:

1. nao abra uma issue publica com detalhes exploraveis;
2. use o fluxo privado de reporte do GitHub, se estiver disponivel no repositorio;
3. se esse fluxo nao estiver disponivel, contacte o mantenedor pelo GitHub antes de publicar detalhes tecnicos.

Para problemas de endurecimento, melhorias preventivas ou duvidas sem risco imediato, uma issue publica pode ser apropriada.

## O que incluir no reporte

- descricao do problema
- impacto potencial
- passos para reproduzir
- sistema operativo e versao do Python
- comandos utilizados
- logs ou mensagens de erro relevantes

## Boas praticas para contribuidores

- nunca publique credenciais reais em issues, logs ou pull requests
- use backups sinteticos ou anonimizados ao reproduzir problemas
- verifique qualquer mudanca em `restore`, `verify` e manipulacao de caminhos com testes

