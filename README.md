## Agrupar Widgets por Chaves no settings JSONB

```sql
WITH widgets_chaves AS (
    SELECT 
        id,
        ARRAY(
            SELECT DISTINCT jsonb_object_keys(settings) 
            ORDER BY jsonb_object_keys(settings)
        ) as chaves
    FROM widgets
    where kind <> 'content'
)
SELECT 
    chaves as estrutura,
    COUNT(*) as total_widgets,
    array_agg(id ORDER BY id) as ids_widgets
FROM widgets_chaves
GROUP BY chaves
ORDER BY total_widgets DESC;
```

## Contagem de todas as chaves utilizadas dentro do settings

```sql
SELECT 
    jsonb_object_keys(settings) as chave,
    COUNT(*) as frequencia
FROM widgets
GROUP BY chave
ORDER BY frequencia DESC, chave;

SELECT 
    jsonb_object_keys(settings) as chave,
    jsonb_typeof(settings -> jsonb_object_keys(settings)) as tipo,
    COUNT(*) as total_widgets
FROM widgets
GROUP BY chave, tipo
ORDER BY total_widgets DESC, chave;
```



- Apresentar panorama do uso e da relação entre os dados
- Discutir sobre vantagens e problemas da estrutura
- Definir planejamento de melhorias
- Conceitos Fantasmas de Widget
    - Nunca é removida
    - Muda de formato
    - Acoplada a renderização