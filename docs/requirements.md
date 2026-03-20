# Requisitos Iniciais do Projeto

## 1. Objetivo

Criar uma ferramenta capaz de fazer o backup integral da interação local com o Codex, permitindo restauração em outro computador ou no mesmo computador em caso de necessidade.

## 2. Requisitos Funcionais

- RF-01: Detectar automaticamente o diretório base do Codex, preferindo `CODEX_HOME` e, na ausência dele, `~/.codex`.
- RF-02: Inventariar arquivos e diretórios relevantes do Codex, incluindo sessões, bancos SQLite, configuração, regras, skills e credenciais.
- RF-03: Criar backup restaurável em diretório.
- RF-04: Criar backup restaurável em arquivo `.zip`.
- RF-05: Gerar manifesto com data de criação, versão da ferramenta, modo do backup, lista de arquivos e hash SHA-256.
- RF-06: Restaurar o backup para um diretório de destino escolhido pelo usuário.
- RF-07: Permitir sobrescrever arquivos de destino mediante opção explícita.
- RF-08: Oferecer exclusão opcional de segredos sensíveis, como `auth.json` e `cap_sid`.
- RF-09: Realizar snapshot consistente de bancos SQLite para evitar inconsistência ao copiar arquivos ativos.
- RF-10: Permitir inspeção prévia do inventário antes do backup.

## 3. Requisitos Não Funcionais

- RNF-01: Funcionar com Python 3.11 ou superior.
- RNF-02: Não depender de bibliotecas externas para o fluxo principal.
- RNF-03: Ser utilizável em linha de comando.
- RNF-04: Produzir saída legível para uso manual e saída determinística o suficiente para automação simples.
- RNF-05: Priorizar portabilidade do backup entre máquinas.

## 4. Modos Iniciais

- `portable`: exclui diretórios transitórios e artefatos de sandbox que tendem a ser recriados na máquina de destino.
- `mirror`: inclui praticamente todo o conteúdo do diretório do Codex, mantendo o backup o mais fiel possível ao ambiente de origem.

## 5. Hipóteses de Projeto

- O estado do Codex reside primariamente em um diretório local semelhante a `~/.codex`.
- Os arquivos SQLite representam parte importante do estado recuperável.
- Os arquivos `*.sqlite-wal` e `*.sqlite-shm` não precisam ser armazenados se o snapshot do banco principal for consistente.
- A restauração inicial será do tipo merge com sobrescrita opcional, sem remoção automática de arquivos extras no destino.

## 6. Próximos Passos Sugeridos

- Adicionar verificação de integridade do backup após criação.
- Adicionar exportação opcional criptografada.
- Adicionar suporte a política de retenção e backups incrementais.
- Adicionar verificação opcional de integridade logo após a criação do backup.
