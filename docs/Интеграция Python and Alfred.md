---
id: 20250803114628
cssclasses:
  - wide
created: 2025-08-03
updated: 2025-08-03
last_activity: 2025-08-03
class: Concept
type: Manual
tags:
  - coding
  - python
  - alfred
status: active
---


## 1. Возможности интеграции Python и Alfred (Alfred 5.5+)

С версии Alfred 5.5 официально поддерживается запуск скриптов на **Python 3** без сторонних костылей. Можно напрямую выбрать в настройках workflow язык запуска как Python 3.

- В Alfred Preferences откройте вкладку **Workflows** и создайте "Blank Workflow".
- Перетащите **Script Filter** (“Inputs > Script Filter”) на схему.
- В опциях Script Filter выберите язык **Python 3** (“Language: /usr/bin/python3” или "Python 3") и пишите свой скрипт.

## 2. Пример скелета для Python workflow

Минимальный рабочий пример поиска файлов через Alfred и Python:

```python
import os
import sys
import json

query = sys.argv[1] if len(sys.argv) > 1 else ""
search_dir = "/Users/your_username/Documents"  # укажите нужную папку

results = []
for root, dirs, files in os.walk(search_dir):
    for filename in files:
        if query.lower() in filename.lower():
            results.append({
                "title": filename,
                "subtitle": root,
                "arg": os.path.join(root, filename)
            })

# Alfred ожидает выходные данные в виде JSON (если используете Script Filter с JSON output)
print(json.dumps({"items": results}))
```
- **{query}** автоматически подставляется Alfred-ом, когда вы вводите поисковый запрос.
- Для сложных фильтраций используйте регулярные выражения или сторонние модули.

## 3. Рекомендованные библиотеки для упрощения интеграции

- **Alfred-Workflow** ([PyPI Alfred-PyWorkflow](https://pypi.org/project/Alfred-PyWorkflow/), [GitHub](https://github.com/NorthIsUp/alfred-workflow-py3) : обеспечивает быстрый обмен данными, кеширование, прослушивание событий от Alfred и удобный синтаксис для создания выдачи и работы с настройками.
  - Поддерживает Alfred 4 и 5, macOS 11+ и Python 3.9+.
  - Кратко о синтаксисе использования см. в официальной документации и туториалах

- **alfred-python**: простая обертка для доступа к настройкам Alfred, формированию выдачи и пр.

## 4. Основные шаги создания workflow c Python-интеграцией

1. **Создайте Blank Workflow** в Alfred.
2. **Откройте его в Finder** (правый клик по workflow — "Open in Finder").
3. **Добавьте Python-скрипт** в эту директорию (например, `search.py`).
4. В Script Filter (или Run Script) настройте:
    - Язык: Python 3.
    - Скрипт: `python3 search.py "{query}"`
    - Output: JSON (либо текст для базового варианта).
    - Передавайте query из Alfred: используйте `{query}` или получайте через `sys.argv`.
5. **Свяжите Script Filter с Action** — например, действие "Open File" для открытия выбранного через Python файла.

## 5. Особенности и возможные сложности

- **Python 3 now bundled:** Новые версии Alfred больше не нуждаются в системном Python, можно выбрать интерпретатор прямо в GUI.
- **Ошибки запуска скриптов**: при отсутствии вывода — отладьте скрипт вручную (например, через Terminal), проверьте права доступа, убедитесь, что указали верный путь к python3.
- Для сложных фильтраций в workflow удобно использовать File Filters и File Actions, а не только Python-код.

## 6. Альтернативные подходы

- Использовать сторонние workflow-комьюнити (Reddit, GitHub) — есть готовые шаблоны и вдохновляющие примеры.

### Валидация и альтернативные мнения

- Основные библиотеки (`alfred-pyworkflow`, `alfred-python`) обслуживаются и обновляются под последние версии Alfred, поддержка Python 3 подтверждена как официальной документацией, так и независимым коммьюнити.
- На форумах Reddit периодически обсуждаются проблемы с запуском сторонних скриптов, чаще всего они связаны не с Alfred, а с несовпадением версий Python или ошибками путей к файлам. Решаются через деинсталляцию workflow или явное указание полного пути к python3.
- Обратите внимание: в некоторых случаях могут возникать проблемы при переходе между macOS с разными версиями Python, поэтому желательно придерживаться системного python3, поставляемого с macOS/Alfred.
- Возможны дополнительные трудности с правами доступа (особенно если указаны защищенные системные папки).

### Ссылки на полезные руководства и документацию

- [Официальная документация по Script Filters и Script Actions для Alfred 5.5](https://www.alfredapp.com/help/workflows/actions/run-script/)
- [Документация и примеры alfred-workflow (с поддержкой Python 3)](https://alfred-workflow.readthedocs.io/en/latest/)
- [Пример подробного workflow с Python](https://www.maharsh.net/blog/alfred-workflow-python?from=mishatugushev.ru)
- Форумы Alfred и Stack Overflow для регулярных обновлений и troubleshooting[9][12]

**Связи**
[[Python]]

