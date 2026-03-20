# Como Publicar um Release

Este projeto usa releases por tag no GitHub.

## Fluxo recomendado

1. Atualizar a versão em `pyproject.toml`.
2. Atualizar a versão em `codex_backup/__init__.py`.
3. Executar os testes:

```bash
python -m unittest discover -s tests -v
```

4. Commitar as mudanças:

```bash
git add .
git commit -m "Release vX.Y.Z"
```

5. Criar a tag:

```bash
git tag vX.Y.Z
```

6. Enviar branch e tag:

```bash
git push
git push origin vX.Y.Z
```

## O que acontece depois

Quando a tag `v*` chega ao GitHub:

- a workflow `Release` é disparada;
- o projeto é empacotado em `sdist` e `wheel`;
- um GitHub Release é criado automaticamente;
- as notas de release são geradas automaticamente;
- os artefatos em `dist/` são anexados ao release.

## Boas práticas

- Use tags no formato `vX.Y.Z`.
- Garanta que a versão do código coincide com a versão da tag.
- Atualize a documentação se o release alterar a experiência de uso.
- Prefira releases pequenos e verificáveis.

