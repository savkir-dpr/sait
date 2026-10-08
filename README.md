# sait

## Телеметрия Raspberry Pi

Панель мониторинга показывает одно значение давления (абсолютное давление),
состояние обеих дверец (`Открыта`, `Закрыта` или `Нет данных`), четыре текущие
температуры и график температуры. Разрежение по-прежнему сохраняется в
телеметрии, но отдельной карточкой на сайте не отображается.

`telemetry.py` — независимый от GUI клиент для передачи показаний и событий
устройства в серверное HTTP API. Он не выполняет сетевые операции в потоке
CustomTkinter, отправляет измерения раз в минуту и сохраняет неотправленные
сообщения в локальной JSONL-очереди.

1. Скопируйте `telemetry_config.example.json` в `telemetry_config.json`.
2. Укажите идентификатор устройства, адрес будущего API и секретный ключ.
3. Не добавляйте `telemetry_config.json` в Git: в нём будет ключ устройства.

### Публичный адрес Amvera

> **Куда вносить изменения:** файл `telemetry_config.json` используется только
> приложением на Raspberry Pi. Его не нужно отправлять в Amvera или Git — файл
> содержит секретный ключ и исключён через `.gitignore`. На стороне Amvera при
> смене домена достаточно изменить переменную окружения
> `DJANGO_ALLOWED_HOSTS` и перезапустить приложение. Сам код сайта повторно
> отправлять в Amvera не требуется, если менялся только адрес сервера.

После переноса приложения на сервер `waw0` публичные адреса имеют следующий
вид:

```text
Сайт: https://monitoringpiro-52356436s.waw0.amvera.tech/
API:  https://monitoringpiro-52356436s.waw0.amvera.tech/api/v1/telemetry
```

На Raspberry Pi поменяйте поле `endpoint` в локальном (не отслеживаемом Git)
файле `telemetry_config.json`:

```json
{
  "endpoint": "https://monitoringpiro-52356436s.waw0.amvera.tech/api/v1/telemetry"
}
```

Поле `api_key` при смене домена менять не требуется: оно должно по-прежнему
точно совпадать с переменной `TELEMETRY_API_KEY` в Amvera.

В настройках переменных окружения приложения Amvera также замените значение
`DJANGO_ALLOWED_HOSTS` на домен без протокола и завершающего слеша:

```text
monitoringpiro-52356436s.waw0.amvera.tech
```

После сохранения переменной перезапустите приложение. В исходном Python-коде,
`dashboard.html` и `dashboard.js` домен менять не нужно: браузер обращается к
API по относительным адресам (`/api/v1/latest`, `/api/v1/history` и
`/api/v1/events`).

#### После миграции сайт открывается, но показания не обновляются

Если на странице видны старые значения и статус «Устройство офлайн», сервер и
dashboard уже работают, но Raspberry Pi не присылает новые измерения. После
смены сервера выполните все пункты ниже:

Состояние нагревателей не определяет статус сайта: переключение реле выполняется
локально на Raspberry Pi. Статус становится `online` только после успешного
приёма сервером нового сообщения телеметрии, поэтому работающий нагреватель не
исключает ошибку endpoint, API-ключа или сети.

1. На Raspberry Pi откройте `telemetry_config.json` и проверьте, что `endpoint`
   содержит новый хост `waw0`, а не старый `mia0`:

   ```text
   https://monitoringpiro-52356436s.waw0.amvera.tech/api/v1/telemetry
   ```

   Команды проверки запускайте из каталога приложения, где рядом находятся
   `main.py`, `telemetry.py` и `telemetry_config.json`. Ошибка
   `ModuleNotFoundError: No module named 'telemetry'` при запуске из `~`
   означает не поломку модуля, а неверный текущий каталог. Найти приложение
   можно командой `find ~ -type f -name telemetry.py -print 2>/dev/null`, после
   чего перейти в найденную папку командой `cd`.

2. В Amvera повторно проверьте переменную `TELEMETRY_API_KEY`. При миграции на
   другой сервер переменные окружения могли не перенестись. Значение должно
   точно совпадать с полем `api_key` на Raspberry Pi. Сам переход с `mia0` на
   `waw0` не требует создавать новый ключ: если прежнее значение перенесено в
   переменные нового приложения, на Raspberry Pi ключ оставьте без изменений.
   Новый ключ нужен только тогда, когда старый потерян, скомпрометирован или вы
   намеренно решили его заменить; в таком случае обновите его одновременно в
   Amvera и в `telemetry_config.json` на Raspberry Pi.
3. Перезапустите приложение Raspberry Pi после изменения JSON: уже созданный
   `TelemetryPublisher` читает конфигурацию только при запуске процесса.
4. Проверьте доступ Raspberry Pi к новому серверу:

   ```bash
   curl -i https://monitoringpiro-52356436s.waw0.amvera.tech/api/v1/latest
   ```

   Ответ `200 OK` с JSON подтверждает доступность сайта.
5. Проверьте авторизованную отправку, не публикуя ключ в чате или Git:

   ```bash
   export TELEMETRY_API_KEY='значение-из-Amvera'
   curl -i -X POST \
     'https://monitoringpiro-52356436s.waw0.amvera.tech/api/v1/telemetry' \
     -H "Authorization: Bearer ${TELEMETRY_API_KEY}" \
     -H 'Content-Type: application/json' \
     --data "{\"type\":\"measurement\",\"device_id\":\"raspberry-pi-01\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"status\":\"online\",\"temperatures_c\":{\"t0\":20.0,\"t1\":20.0,\"t2\":20.0,\"t3\":20.0},\"vacuum_kpa\":0.0,\"absolute_pressure_kpa\":101.325,\"doors_closed\":{\"door_1\":true,\"door_2\":true}}"
   unset TELEMETRY_API_KEY
   ```

   Ожидается ответ `201 Created`. `401 Unauthorized` означает несовпадение
   ключей; тайм-аут или ошибка DNS означает проблему доступа к новому домену.
6. Посмотрите очередь и вывод приложения на Raspberry Pi:

   ```bash
   tail -n 5 telemetry_queue.jsonl
   ```

   Непустая очередь вместе с сообщением `Телеметрия не отправлена: ...`
   показывает точную сетевую или HTTP-ошибку. Не удаляйте очередь: после
   исправления адреса или ключа клиент отправит накопленные записи.
   Для диагностики нужен полный текст после двоеточия: например,
   `HTTP Error 401: Unauthorized`, `Name or service not known`,
   `Connection timed out` или ошибка сертификата указывают на разные причины.
   Не перезаписывайте очередь и не меняйте ключ наугад до фиксации полной строки
   ошибки.

#### После миграции отображается старая версия dashboard

Если сайт открывается, но всё ещё показывает `кПа` и четыре линии графика,
Amvera запустила старый коммит либо браузер использует старые статические
файлы. В актуальной версии карточка давления подписана `бар`, а график имеет
заголовок «Средняя температура» и рисует одну линию.

На ноутбуке убедитесь, что изменения действительно входят в коммит:

```powershell
git status
git add templates/monitoring/dashboard.html monitoring/static/monitoring/dashboard.js tests/test_dashboard_files.py
git commit -m "Deploy bar pressure and average temperature chart"
git push amvera master
```

После завершения новой сборки Amvera выполните жёсткое обновление страницы
`Ctrl+F5`. В шаблоне добавлена версия `average-bar-v2` к URL CSS и JavaScript,
чтобы браузер не использовал файлы предыдущей сборки. В исходном коде страницы
можно дополнительно найти маркер `data-dashboard-version="average-bar-v2"`:
если его нет, Amvera всё ещё обслуживает старый коммит.

##### Пошаговая диагностика с остановкой после каждого шага

Чтобы не смешивать несколько причин, выполняйте по одной команде и проверяйте
её результат перед продолжением:

1. `git status` — выяснить, сохранены ли изменения dashboard локально.
   Если `dashboard.html` и `dashboard.js` находятся в разделе
   `Changes not staged for commit`, изменения существуют только на ноутбуке:
   Amvera их ещё не получила и поэтому продолжает показывать старую страницу.
2. `git diff -- templates/monitoring/dashboard.html monitoring/static/monitoring/dashboard.js` — увидеть незакоммиченные изменения этих файлов.
   Если Git открыл длинный вывод в постраничном просмотрщике, нажмите `q`, а
   затем проверьте ключевые изменения короткой командой `Select-String` для
   строк `бар`, `Средняя температура`, `formatPressureBar` и
   `getAverageTemperature`.
   Если найдены все четыре маркера, добавьте в индекс только два файла сайта
   (`dashboard.html` и `dashboard.js`), не захватывая клиентские файлы
   Raspberry Pi, и снова проверьте `git status` перед созданием коммита. В
   правильном состоянии два dashboard-файла находятся в `Changes to be
   committed`, а `journal_utils.py`, `manual_page.py` и `telemetry.py` остаются
   в `Changes not staged for commit`.
3. `git log -1 --oneline` — определить локальный коммит.
   Сообщение `Your branch is ahead of 'amvera/master' by 1 commit` после
   создания коммита означает, что dashboard уже сохранён локально и готов к
   отправке; незакоммиченные файлы Raspberry Pi в этот коммит не попали.
4. `git ls-tree -r --name-only HEAD` — убедиться, что оба dashboard-файла входят в коммит.
5. Только после этих проверок выполнить `git push amvera master`.
   Домен в этой команде указывать не нужно: remote `amvera` уже хранит Git URL
   конкретного приложения, а `master` обозначает отправляемую ветку. Проверить
   назначение можно командой `git remote -v`. Публичный домен используется
   отдельно в `DJANGO_ALLOWED_HOSTS` и в Raspberry Pi `endpoint`, но не в
   команде `git push`.
   После миграции между регионами проверьте страницу «Репозиторий» нового
   приложения: если локальный remote всё ещё содержит старый регион (например,
   `git.mia0...`), не выполняйте push, пока не скопируете из кабинета точный Git
   URL нового приложения и не обновите remote командой
   `git remote set-url amvera <новый-Git-URL>`.
   Если remote `amvera` уже существует, не используйте повторно
   `git remote add`: Git ответит `remote amvera already exists`. Для миграции
   меняется адрес существующего remote через `set-url`, после чего результат
   обязательно проверяется командой `git remote -v`. Перед первым push на
   новый регион выполните `git fetch amvera` и снова посмотрите `git status`,
   чтобы Git загрузил состояние ветки нового репозитория и заранее обнаружил
   возможное расхождение истории.
6. После успешной сборки проверить маркер `average-bar-v2` в исходном HTML
   публичной страницы и выполнить `Ctrl+F5`.

Если команда возвращает неожиданный результат, не переходите к следующей:
сначала сохраните полный вывод текущего шага. Это позволяет отличить
незакоммиченные изменения от старого коммита Amvera и от кэша браузера.

### Подключение к существующему обновлению датчиков

Создайте издатель один раз после инициализации `QuadMAX31865` и
`PressureSensor`:

```python
from telemetry import TelemetryConfig, TelemetryPublisher

telemetry = TelemetryPublisher(TelemetryConfig.from_file("telemetry_config.json"))
```

После чтения температур, давления и концевиков добавьте:

```python
telemetry.publish_measurement(
    temperatures_c={"t0": t0, "t1": t1, "t2": t2, "t3": t3},
    vacuum_kpa=vacuum_kpa,
    absolute_pressure_kpa=absolute_pressure_kpa,
    doors_closed={"door_1": d1_closed, "door_2": d2_closed},
)
```

Метод безопасно вызывать каждую секунду: он отправит данные только раз в
60 секунд (`interval_seconds`), а пользовательский интерфейс продолжит
обновляться с прежней частотой.

#### Изменения в `manual_page.py`

Добавьте импорт рядом с импортами датчиков:

```python
from telemetry import TelemetryConfig, TelemetryPublisher
```

После создания `PressureSensor` один раз создайте издатель, используя путь
относительно самого приложения:

```python
base_dir = os.path.dirname(__file__)
telemetry = TelemetryPublisher(
    TelemetryConfig.from_file(os.path.join(base_dir, "telemetry_config.json"))
)
```

При чтении давления сохраните оба результата (раньше первый мог отбрасываться):

```python
try:
    vacuum_kpa, absolute_pressure_kpa = pressure_sensor.read_pressure_kpa()
except Exception as exc:
    print(f"Не удалось прочитать датчик давления: {exc}")
    vacuum_kpa = None
    absolute_pressure_kpa = None
```

Вызов `publish_measurement` разместите после чтения температур и обеих дверей,
но перед следующим `frame.after(1000, _update_sensors)`.

### Проверка в локальной сети

1. Узнайте IPv4-адрес компьютера командой `ipconfig`.
2. Запустите Django на всех сетевых интерфейсах:

   ```powershell
   $env:DJANGO_DEBUG = "1"
   $env:DJANGO_ALLOWED_HOSTS = "localhost,127.0.0.1,192.168.1.25"
   $env:TELEMETRY_API_KEY = "test-secret-key"
   .\.venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
   ```

3. Замените `192.168.1.25` на адрес компьютера и задайте на Raspberry Pi:

   ```json
   {
     "device_id": "raspberry-pi-01",
     "endpoint": "http://192.168.1.25:8000/api/v1/telemetry",
     "api_key": "test-secret-key",
     "interval_seconds": 60,
     "queue_path": "telemetry_queue.jsonl",
     "timeout_seconds": 10
   }
   ```

4. Проверьте с Raspberry Pi командой
   `curl http://192.168.1.25:8000/api/v1/latest`. Если соединение отклонено,
   разрешите входящие TCP-подключения к порту 8000 в брандмауэре Windows.
5. Запустите приложение Raspberry Pi и дождитесь первой минутной отправки.
   Файл `telemetry_queue.jsonl` должен опустеть после успешной доставки.

Тестовый HTTP-режим используйте только внутри доверенной локальной сети. Для
публичного сервера endpoint обязательно должен начинаться с `https://`.

### События журнала

`TelemetryPublisher`, созданный в `manual_page.py`, автоматически становится
издателем по умолчанию. В `journal_utils.py` добавьте импорт:

```python
from telemetry import publish_journal_event
```

В конце `journal_add_event`, сразу после `write_journal(fp, events)`, добавьте:

```python
publish_journal_event(
    action=action,
    program=program_name or "(без названия)",
    details=details or "",
)
```

Это сохраняет событие в старом локальном журнале и одновременно ставит его в
очередь отправки на сайт. До создания издателя функция ничего не отправляет и
не мешает локальному журналу.

Для прямой отправки события также можно вызвать:

```python
telemetry.publish_event(action="запуск", program="Имя программы", details="...")
```

Подключение `journal_utils.py` к этому вызову будет следующим этапом после
размещения исходных файлов Raspberry Pi в репозитории.

### Проверка

```bash
python -m unittest discover -s tests -v
```
