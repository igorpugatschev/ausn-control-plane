# Slider-autotests: триаж падений `framework_tests` на Windows

Источник: `slider-autotests` @ `fdfe495` (`C:\rocketscience\slider-web\slider-autotests`).
Команда: `.\.venv\Scripts\python.exe -m pytest framework_tests\ -q --tb=line -p no:cacheprovider`
Окружение: Windows 11, `.venv` Python 3.12.10, Chromium (playwright) установлен.

## Итог прогона

`772 passed, 138 failed, 1 warning in 86.9s`.

Все падения — **платформенные (Windows vs POSIX)**, не дефекты фреймворка и не дефекты продукта.
Фреймворк по дизайну **жёстко фейлит**, когда платформа не даёт обязательных POSIX-примитивов
(в текстах исключений прямо стоит «platform не поддерживает …»), поэтому на Windows эти тесты
падают, а не скипаются.

## Категории причин

| Причина | Признак в трейсбеке | ≈ Кол-во |
|---|---|---|
| POSIX-примитивы недоступны (dir_fd / `O_NOFOLLOW` / `O_DIRECTORY`) | `utils.ephemeral_lifecycle.EphemeralLifecycleError: platform не поддерживает обязательные O_NOFOLLOW/O_DIRECTORY/dir_fd primitives` | 46 |
| Запуск POSIX-скриптов | `OSError: [WinError 193] %1 не является приложением Win32` | 21+ |
| Нет атрибутов `os` | `AttributeError: module 'os' has no attribute 'O_NOFOLLOW' / 'O_DIRECTORY' / 'mkfifo'` | ~17 |
| Guard записи JSON | `scripts.run_mutation_pilot.MutationPilotError: platform не поддерживает guarded json-output write` | 11 |
| Нет POSIX-deadline в контексте очистки | `scripts.qa_readiness.CleanupFailure: … cleanup wall-time deadline недоступен в текущем execution context` | ~11 |
| Блокировка файлов Windows | `PermissionError: [WinError 32] … этот файл занят другим процессом` | 5 |
| Декодирование вывода подпроцесса | `UnicodeDecodeError` (cp1251/utf-8) | 3 |

Примечание: упоминания `allure` (≈56 строк) — часть проверок redaction/интеграции, **не причина** падений.

## Вывод и рекомендации

1. Самопроверки `framework_tests/` рассчитаны на **Linux/POSIX**; на Windows они неприменимы
   по построению (это осознанные guard'ы, а не баги).
2. Полноценный прогон самопроверок и продукта `tests/` выполнять в **WSL/Linux**, там же поставить
   внешние инструменты (`k6`; Allure CLI уже есть в scoop на Windows).
3. На Windows допустим только прогон продукта `tests/` с осознанным исключением POSIX-зависимых
   сценариев; список исключений — по признакам выше.
4. Причины `UnicodeDecodeError` (3) стоит отдельно проверить в Linux-прогоне: там они, вероятно,
   не воспроизведутся.
