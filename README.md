## Описание

Этот сервер может принимать файлы от камер с определенных IP-адресов, указанных в списке разрешенных устройств.
Загруженные файлы затем отправляются в Telegram.
Также в MQTT приходят данные об алерте, что позволяет реализовать логику в Home Asisstant.
Кроме того, FTP-сервер автоматически удаляет старые файлы для сохранения свободного места.

# Сборка
```
git clone git@github.com:xomarnd/cctvftpmqtttg.git
cd cctvftpmqtttg/
docker build -t cctvftpmqtttg .
docker compose build
docker compose up
```

# Настройка docker compose
ALLOWED_DEVICES: Список разрешенных устройств в формате JSON, содержащий информацию об IP-адресе и имени устройства.

```[{"ip": "192.168.100.112", "name": "device1"}, {"ip": "192.168.100.113", "name": "device2"}]```

`TELEGRAM_MESSAGE:` Сообщение, которое будет отправлено в Telegram при получении файла.

`TELEGRAM_CHANNEL_ID:` ID канала в Telegram, куда будут отправляться файлы.

`TELEGRAM_BOT_TOKEN:` Токен Telegram бота.

`CHANNEL_DELAY:` Задержка между получением файлов от одного и того же устройства (в секундах).


`MAX_FILES:` Максимальное количество файлов, которое может храниться на сервере. Когда это количество превышено, самые старые файлы будут автоматически удаляться.

`FILES_TO_DELETE:` Количество файлов, которые будут удаляться при превышении лимита MAX_FILES.

`FTP_DIR:` Директория, где будут храниться загруженные файлы.


`HOME_ASSISTANT_SERVER_ADR:` Адрес сервера Home Assistant.

`HOME_ASSISTANT_SERVER_PORT:` Порт сервера Home Assistant (по умолчанию 8123).

`HOME_ASSISTANT_SERVER_BEARER:` Bearer token для сервера Home Assistant. https://developers.home-assistant.io/docs/api/rest/

`INPUT_BOOLEAN_ALARM:` Имя boolean input в Home Assistant, которое определяет статус сигнализации.


`MQTT_BASE_TOPIC:` Базовый топик для MQTT.


`MQTT_TOPIC:` Топик для MQTT.

`MQTT_BROKER:` Адрес MQTT брокера.

`MQTT_PORT:` Порт MQTT брокера.

`MQTT_USERNAME:` Имя пользователя для MQTT брокера.

`MQTT_PASSWORD:` Пароль для MQTT брокера.


`FTP_USER:` Имя пользователя для FTP сервера.

`FTP_PASSWORD:` Пароль для FTP сервера.

`FTP_PERM:` Права доступа пользователя FTP в формате строки, которая может включать следующие символы: "elradfmwM".


# Настройка камеры
Включаем отправку снимков по детекции на FTP, вносим настроки FTP.
Частота отправления файлов будет зависить от настроек камер.
# Настройка HA

/config/configuration.yaml
```python_script:```

/config/python_scripts/set_state.py
````inputEntity = data.get('entity_id')
if inputEntity is None:
logger.warning("===== entity_id is required if you want to set something.")
else:
inputStateObject = hass.states.get(inputEntity)
if inputStateObject is None and not data.get('allow_create'):
logger.warning("===== unknown entity_id: %s", inputEntity)
else:
if not inputStateObject is None:
inputState = inputStateObject.state
inputAttributesObject = inputStateObject.attributes.copy()
else:
inputAttributesObject = {}

    for item in data:
        newAttribute = data.get(item)
        logger.debug("===== item = {0}; value = {1}".format(item,newAttribute))
        if item == 'entity_id':
            continue            # already handled
        elif item == 'allow_create':
            continue            # already handled
        elif item == 'state':
            inputState = newAttribute
        else:
            inputAttributesObject[item] = newAttribute
      
    hass.states.set(inputEntity, inputState, inputAttributesObject)
````
    
input_boolean.yaml
Прописываем этот сенсор в `INPUT_BOOLEAN_ALARM`
```
input_boolean_camers_alarm:
  name: Режим детекции камер
  initial: on
```

packages:
```
cam_alarm:
  mqtt:
    sensor:
    - state_topic: "cameras/192.168.100.112/event"
      name: "Sensor cam 1"
      value_template: "{{ value }}"
    - state_topic: "cameras/192.168.100.113/event"
      name: "Sensor cam 2"
      value_template: "{{ value }}"
```
automations:
```
- id: 'alarm cam 1'
  alias: Send camera snapshot on alarm 1
  trigger:
  platform: state
  entity_id: sensor.sensor_cam_1
  condition:
    condition: template
    value_template: "{{ trigger.to_state.state != 'Processed' }}"
  action:
  - delay:
    seconds: 5
  - service: python_script.set_state
    data_template:
    entity_id: sensor.sensor_cam_1
    state: "Processed"
    
- id: 'alarm cam 2'
  alias: Send camera snapshot on alarm 2
  trigger:
  platform: state
  entity_id: sensor.sensor_cam_2
  condition:
    condition: template
    value_template: "{{ trigger.to_state.state != 'Processed' }}"
  action:
  - delay:
    seconds: 5
  - service: python_script.set_state
    data_template:
    entity_id: sensor.sensor_cam_2
    state: "Processed"
```
