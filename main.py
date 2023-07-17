import os
import requests
import time
from pyftpdlib.authorizers import DummyAuthorizer, AuthenticationFailed
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
from telegram import Bot
import paho.mqtt.client as mqtt
from io import BytesIO
import json


class CustomAuthorizer(DummyAuthorizer):
    def validate_authentication(self, username, password, handler):
        ip = handler.remote_ip
        allowed_devices_str = os.getenv('ALLOWED_DEVICES', '[]')
        allowed_devices = json.loads(allowed_devices_str)

        for device in allowed_devices:
            if device['ip'] == ip:
                super().validate_authentication(username, password, handler)
                return

        raise AuthenticationFailed("This IP is not allowed.")


def get_message():
    return os.getenv('TELEGRAM_MESSAGE', 'Alarma!').replace('"', '').replace("'", '')


class CustomFTPHandler(FTPHandler):
    channel_id = os.getenv('TELEGRAM_CHANNEL_ID')
    channel_delay = int(os.getenv('CHANNEL_DELAY', 5))
    max_files = int(os.getenv('MAX_FILES', 100))
    files_to_delete = int(os.getenv('FILES_TO_DELETE', 50))
    upload_folder = os.getenv('FTP_DIR', '/data')  # adjust to your needs
    home_assistant_server_address = os.getenv('HOME_ASSISTANT_SERVER_ADR')
    home_assistant_server_port = int(os.getenv('HOME_ASSISTANT_SERVER_PORT', 8123))  # 8123 is default port
    home_assistant_server_bearer = os.getenv('HOME_ASSISTANT_SERVER_BEARER')
    home_assistant_input_boolean_alarm = os.getenv('INPUT_BOOLEAN_ALARM')
    mqtt_base_topic = os.getenv('MQTT_BASE_TOPIC', 'cameras')
    mqtt_topic = os.getenv('MQTT_TOPIC')

    client = None
    last_file_time = {}

    def on_connect(self):
        print(f"{self.remote_ip} has connected")

    def on_disconnect(self):
        print(f"{self.remote_ip} has disconnected")

    def on_file_sent(self, file):
        print(f"{self.remote_ip} sent a file: {file}")

    def on_file_received(self, file):
        print(f"{self.remote_ip} uploaded a file: {file}")

        if not self.get_home_assistant_alarm_status():
            print(f"Alarm is off, skipping processing for file: {file}")
            self.manage_files_buffer()
            return

        # Check if file from the same IP was received less than channel_delay seconds ago
        if self.remote_ip in self.last_file_time and time.time() - self.last_file_time[
            self.remote_ip] < self.channel_delay:
            print(f"File from {self.remote_ip} ignored due to channel delay")
            os.remove(file)
            return

        self.last_file_time[self.remote_ip] = time.time()
        self.send_to_mqtt()
        self.send_to_telegram(file)
        self.manage_files_buffer()

    def send_to_telegram(self, file):
        try:
            with open(file, 'rb') as f:
                photo_data = BytesIO(f.read())
                self.bot.send_photo(chat_id=self.channel_id, photo=photo_data,
                                    caption=self.get_user_name())
            print(f"Send to telegram {self.get_user_name()}")
        except ValueError:
            print(ValueError)

    def send_to_mqtt(self):
        try:
            topic = f"{self.mqtt_base_topic}/{self.remote_ip}/event"
            self.client.publish(topic, "snapshot")
            print(f"Send to mqtt {topic}/snapshot")
        except ValueError:
            print(ValueError)

    def manage_files_buffer(self):
        files = [os.path.join(dp, f) for dp, dn, fn in os.walk(self.upload_folder) for f in fn]
        files_sorted = sorted(files, key=os.path.getmtime)
        total_files = len(files_sorted)
        if total_files > self.max_files:
            for file in files_sorted[:total_files - self.max_files]:
                os.remove(file)
                print(f"Removed file {file}")

        for folder in [f.path for f in os.scandir(self.upload_folder) if f.is_dir()]:
            if not os.listdir(folder):
                os.rmdir(folder)
                print(f"Removed empty folder {folder}")

    def get_user_name(self):
        allowed_devices_str = os.getenv('ALLOWED_DEVICES', '[]')
        allowed_devices = json.loads(allowed_devices_str)

        for device in allowed_devices:
            if device['ip'] == self.remote_ip:
                return f" {get_message()} {device['name']}"

        return f"Unknown User - {self.remote_ip}"

    def get_home_assistant_alarm_status(self):
        headers = {'Authorization': f'Bearer {self.home_assistant_server_bearer}'}
        url = f'http://{self.home_assistant_server_address}:{self.home_assistant_server_port}/api/states/{self.home_assistant_input_boolean_alarm}'
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            return data.get('state') == 'on'
        else:
            print(f'Error getting status from Home Assistant: {response.status_code}')
            return True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
        self.mqtt_broker = os.getenv('MQTT_BROKER')
        self.mqtt_port = int(os.getenv('MQTT_PORT', 1883))
        self.mqtt_user = os.getenv('MQTT_USERNAME')
        self.mqtt_password = os.getenv('MQTT_PASSWORD')

        if self.mqtt_broker and self.mqtt_port:
            self.client = mqtt.Client()
            if self.mqtt_user and self.mqtt_password:
                self.client.username_pw_set(self.mqtt_user, self.mqtt_password)
            self.client.connect(self.mqtt_broker, self.mqtt_port, 60)
            self.client.loop_start()
        else:
            print("MQTT credentials not provided. MQTT client cannot be initialized.")


def main():
    try:
        authorizer = CustomAuthorizer()
        ftp_user = os.getenv('FTP_USER', 'user')
        ftp_password = os.getenv('FTP_PASSWORD', '12345')
        authorizer.add_user(ftp_user, ftp_password, homedir=os.getenv('FTP_DIR', '/data'),
                            perm=os.getenv('FTP_PERM', 'elradfmw'))

        handler = CustomFTPHandler
        handler.authorizer = authorizer

        server = FTPServer(("0.0.0.0", 21), handler)
        server.serve_forever()

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
