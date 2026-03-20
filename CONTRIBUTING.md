# Como Contribuir

Este projeto foi criado para preservar e restaurar o estado local do Codex. A ideia é que qualquer pessoa consiga usar a ferramenta, corrigir problemas e adicionar novas funcionalidades sem precisar descobrir tudo do zero.

## 1. Preparar o ambiente

```bash
python -m pip install -e .
```

Opcionalmente, valide a instalação:

```bash
python -m codex_backup --help
codex-backup --help
```

## 2. Executar os testes

```bash
python -m unittest discover -s tests -v
```

## 3. Ler a documentação base

Antes de alterar o projeto, vale consultar:

- `README.md`
- `docs/usage.md`
- `docs/architecture.md`
- `docs/requirements.md`

## 4. Estrutura do projeto

- `codex_backup/core.py`: engine principal de backup, verificação e restauração
- `codex_backup/cli.py`: interface de linha de comando
- `codex_backup/models.py`: estruturas de dados do manifesto
- `tests/`: testes automatizados
- `docs/`: documentação de uso, arquitetura e requisitos

## 5. Diretrizes para novas funcionalidades

- Preserve a compatibilidade do `manifest.json` sempre que possível.
- Toda alteração de comportamento em `restore` deve continuar priorizando segurança dos dados.
- Novas opções da CLI devem ter ajuda clara e exemplos na documentação.
- Sempre que possível, adicione ou atualize testes para cobrir o novo comportamento.

## 6. Fluxo sugerido para evoluir o projeto

1. criar ou atualizar testes;
2. implementar a funcionalidade;
3. atualizar a documentação;
4. validar com `python -m unittest discover -s tests -v`;
5. testar manualmente a CLI em um cenário real ou sintético.

## 7. Ideias de evolução

- criptografia opcional do pacote de backup
- backup incremental
- retenção de versões
- comando de reparo ou diagnóstico de backup
- relatórios mais detalhados em JSON

