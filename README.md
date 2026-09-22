# sait

## Телеметрия Raspberry Pi

`telemetry.py` — независимый от GUI клиент для передачи показаний и событий
устройства в серверное HTTP API. Он не выполняет сетевые операции в потоке
CustomTkinter, отправляет измерения раз в минуту и сохраняет неотправленные
сообщения в локальной JSONL-очереди.

1. Скопируйте `telemetry_config.example.json` в `telemetry_config.json`.
2. Укажите идентификатор устройства, адрес будущего API и секретный ключ.
3. Не добавляйте `telemetry_config.json` в Git: в нём будет ключ устройства.

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

### События журнала

Для отправки событий запуска, остановки и завершения программы можно вызвать:

```python
telemetry.publish_event(action="запуск", program="Имя программы", details="...")
```

Подключение `journal_utils.py` к этому вызову будет следующим этапом после
размещения исходных файлов Raspberry Pi в репозитории.

### Проверка

```bash
python -m unittest discover -s tests -v
```
