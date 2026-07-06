<div align="center">

# AssistantEngine

**Платформа для голосового ассистента.**

[![Version](https://img.shields.io/badge/version-1.0-green.svg)](#)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)

**Авторы:** [Makss](https://github.com/Makss235), [Sintaro](https://github.com/SintaroSan)

</div>

---

Платформа для голосового ассистента. Проект состоит из независимых сервисов, каждый из которых отвечает за свой этап обработки команд - от распознавания речи до формирования ответа.

## Компоненты

- **[CommandEngine](CommandEngine/README.md)** - ядро проекта. Модульный сборщик конфигураций для [Rasa](https://rasa.com/): собирает `nlu.yml`, `domain.yml`, `rules.yml` и `stories.yml` из набора компактных, самодостаточных модулей. Включает CLI-сборщик и веб-панель управления.

- **STTCore** - модуль распознавания речи (speech-to-text). В разработке.

## Структура

```
AssistantEngine/
├── CommandEngine/      # сборщик конфигураций Rasa + панель управления
├── STTCore/            # распознавание речи (заготовка)
└── docker-compose.yml  # оркестрация сервисов
```

Подробности по основному компоненту - в [CommandEngine/README.md](CommandEngine/README.md).
Подробности по работе с Rasa - в [CommandEngine/rasa/README.md](CommandEngine/rasa/README.md).