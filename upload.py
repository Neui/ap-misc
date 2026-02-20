#!/usr/bin/env python3

# SPDX-License-Identifier: CC0-1.0

import argparse
import http.cookiejar
import json
import logging
import pathlib
import sys
import time
import urllib.parse
import urllib.request
import yaml


log = logging.getLogger(__name__)

user_agent = "ap-upload/0.1 (@Neui, dev)"
http_headers = {
    'User-Agent': user_agent,
}


class Config:
    service: str = "https://archipelago.gg"
    host: str = "archipelago.gg"
    message: str = "{room_link}"
    message_output: str = "output.txt"
    anap_instance: str = "https://tomagueri.fr/anaptracker"
    anap_webhost: str = "archipelago"

    @property
    def upload_url(self) -> str:
        return self.service + '/uploads'

    def new_room_url(self, seed_id: str) -> str:
        return self.service + '/new_room/' + seed_id

    def room_status_url(self, room_id: str) -> str:
        return self.service + '/api/room_status/' + room_id

    def room_url(self, room_id: str) -> str:
        return self.service + '/room/' + room_id

    def tracker_url(self, tracker_id: str) -> str:
        return self.service + '/tracker/' + tracker_id

    def sphere_tracker_url(self, tracker_id: str) -> str:
        return self.service + '/sphere_tracker/' + tracker_id

    def anap_url(self, room_id: str) -> str:
        return self.anap_instance + '/room/' + room_id

    def fill(self, data):
        self.service = data.get('service', self.service)
        if 'host' not in data.keys():
            u = urllib.parse.urlparse(self.service)
            self.host = data.get("host", u.hostname)
        else:
            self.host = data.get("host", self.host)
        self.message = data.get("message", self.message)
        self.message_output = data.get("message_output", self.message_output)
        if 'anap' in data:
            anap = data['anap']
            self.anap_instance = anap.get('instance', self.anap_instance)
            self.anap_webhost = anap.get('webhost', self.anap_webhost)


def generate_multipart_file(data, filename: str,
                            content_type: str = 'application/octet-stream'
                            ) -> tuple[bytes, bytes]:
    boundary = 'iamaboundaryseparatorillprobablynotappearintheedata'.encode('utf-8') # noqa
    content_type = b'multipart/form-data; boundary=' + boundary
    boundary = b'--' + boundary
    header = (
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n' # noqa
        f'Content-Type: {content_type}\r\n').encode('utf-8')
    return (content_type,
            boundary + b'\r\n' + header + b'\r\n'
            + data + b'\r\n' + boundary + b'--\r\n')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.description = "Upload a multiworld and prepare chat message"

    parser.add_argument("--secrets", type=str, default="secrets.yaml",
                        help="Where to find secrets file")
    parser.add_argument("--config", type=str, default="upload.yaml",
                        help="Configuration file")
    parser.add_argument("multiworld", type=str,
                        help="Generated multiworld zip to upload")

    args = parser.parse_args()

    config = Config()
    try:
        with open(args.config, "rt") as config_file:
            config.fill(yaml.safe_load(config_file.read()))
    except FileNotFoundError:
        log.exception("Trying to load config file %r", args.config)

    u = urllib.parse.urlparse(config.service)
    with open(args.secrets, "rt") as secret_file:
        secrets = yaml.safe_load(secret_file.read())
        if u.hostname not in secrets.keys():
            log.error(f"No secret found for {u.hostname}")
            return 1
        secret_url = str(secrets[u.hostname])
        log.debug("Found secret for %s", u.hostname)
        del secrets
    del u

    log.info("Loading secret cookies")
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(
        jar))
    opener.addheaders = list(http_headers.items())
    req = urllib.request.Request(secret_url, method='GET')
    with opener.open(req) as r:
        log.debug("Loading secret status code: %r", r.status)

    log.info("Loading multiworld data")
    with open(args.multiworld, 'rb') as mw_file:
        multiworld_data = mw_file.read()

    log.info("Uploading multiworld")
    content_type, mwdata = generate_multipart_file(
        multiworld_data,
        pathlib.Path(args.multiworld).name,
        'application/zip')
    req = urllib.request.Request(config.upload_url,
                                 headers={
                                     'Content-Type': content_type.decode('utf-8')
                                 },
                                 data=mwdata,
                                 method='POST')
    with opener.open(req) as r:
        log.debug("Status code: %r, url: %r", r.status, r.url)
        u = urllib.parse.urlparse(r.url)
        path = pathlib.PurePosixPath(u.path)
        if len(path.parts) >= 3 and path.parts[1] == 'seed':
            seed_id = path.parts[2]
            log.debug("Found seed id: %r", seed_id)
        else:
            log.error("Failed to find seed id")
            log.debug("Reponse: %r", r.read())
            return 1

    log.info("Opening new room")
    req = urllib.request.Request(config.new_room_url(seed_id),
                                 method='GET')
    with opener.open(req) as r:
        log.debug("Status code: %r, url: %r", r.status, r.url)
        u = urllib.parse.urlparse(r.url)
        path = pathlib.PurePosixPath(u.path)
        if len(path.parts) >= 3 and path.parts[1] == 'room':
            room_id = path.parts[2]
            log.debug("Found room id: %r", seed_id)
        else:
            log.error("Failed to find room id")
            return 1

    log.info("Waiting for server to start up")
    room_status_url = config.room_status_url(room_id)
    attempts = 30
    port = 0
    for attempt in range(attempts):
        time.sleep(1)
        log.info("Attempt %d/%d", attempt + 1, attempts)
        req = urllib.request.Request(room_status_url, method='GET')
        with opener.open(req) as r:
            data = json.loads(r.read().decode('utf-8'))
        log.debug("Output: %r", data)
        if type(data) is dict and 'tracker' in data:
            tracker_id = data['tracker']
        if type(data) is not dict or 'last_port' not in data \
                or type(data['last_port']) is not int \
                or data['last_port'] <= 0:
            continue
        port = data['last_port']
        break
    log.debug("Found connection: %r:%r", config.host, port)

    message = config.message.format(
        room_link=config.room_url(room_id),
        host=config.host,
        port=port,
        tracker_link=config.tracker_url(tracker_id),
        anap_tracker_link=config.anap_url(room_id)
    )
    log.info("Message:\n%s", message)
    with open(config.message_output, "wt") as msg_out_file:
        msg_out_file.write(message)

    return 0


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    sys.exit(main())
