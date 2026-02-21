#!/usr/bin/env python3

# SPDX-License-Identifier: CC0-1.0

import argparse
import http.cookiejar
import json
import logging
import multiworld
import pathlib
import sys
import time
import urllib.parse
import urllib.request
import yaml

log = logging.getLogger(__name__)

http_headers = {
    'User-Agent': "ap-upload/0.1 (https://github.com/Neui/ap-misc)",
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
        # TODO: Use self.anap_webhost?
        # https://github.com/OriginalTomPouce/anaptracker/blob/3cfa3d925b88864cb1ef723a649b75c10b03c009/src/components/Home.vue#L76
        return self.anap_instance + '/room/' + room_id

    def fill(self, data):
        self.service = data.get('service', self.service).rstrip('/')
        if 'host' not in data.keys():
            u = urllib.parse.urlparse(self.service)
            self.host = data.get("host", u.hostname)
        else:
            self.host = data.get("host", self.host)
        self.message = data.get("message", self.message)
        self.message_output = data.get("message_output", self.message_output)
        if 'anap' in data:
            anap = data['anap']
            self.anap_instance = anap.get('instance', self.anap_instance) \
                .rstrip('/')
            self.anap_webhost = anap.get('webhost', self.anap_webhost)


def generate_multipart_file(data, filename: str,
                            content_type: str = 'application/octet-stream'
                            ) -> tuple[str, bytes]:
    boundary_str = 'iamaboundaryseparatorillprobablynotappearintheedata'
    http_content_type = f'multipart/form-data; boundary={boundary_str}'
    boundary = b'--' + boundary_str.encode('utf-8')
    header = (
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n' # noqa
        f'Content-Type: {content_type}\r\n').encode('utf-8')
    return (http_content_type,
            boundary + b'\r\n' + header + b'\r\n' + data + b'\r\n'
            + boundary + b'--\r\n')


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
            log.error(f"No session found for {u.hostname} in secrets file")
            return 1
        session_url = str(secrets[u.hostname])
        log.debug("Found secret for %s", u.hostname)
        del secrets
    del u

    log.info("Loading session cookies")
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(
        jar))
    opener.addheaders = list(http_headers.items())
    with opener.open(session_url) as r:
        log.debug("Loading session status code: %r", r.status)

    log.info("Loading multiworld data")
    with open(args.multiworld, 'rb') as mw_file:
        multiworld_data = mw_file.read()

    try:
        apdata = multiworld.parse(multiworld_data)
    except:
        logging.exception("Failed to parse multiworld data")
        apdata = multiworld.MultiWorld()

    log.info("Uploading multiworld")
    content_type, mwdata = generate_multipart_file(
        multiworld_data,
        pathlib.Path(args.multiworld).name,
        'application/zip' if args.multiworld.lower().endswith('.zip')
        else 'application/octet-stream'
    )
    with opener.open(urllib.request.Request(
            config.upload_url,
            headers={'Content-Type': content_type},
            data=mwdata, method='POST')) as r:
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
    with opener.open(config.new_room_url(seed_id)) as r:
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
        with opener.open(room_status_url) as r:
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
        seed_id=seed_id,
        room_id=room_id,
        room_link=config.room_url(room_id),
        host=config.host,
        port=port,
        password=apdata.server_options.visible_password,
        tracker_id=tracker_id,
        tracker_link=config.tracker_url(tracker_id),
        sphere_tracker_link=config.sphere_tracker_url(tracker_id),
        anap_tracker_link=config.anap_url(room_id),
    )
    log.info("Message:\n%s", message)
    with open(config.message_output, "wt") as msg_out_file:
        msg_out_file.write(message)

    return 0


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    sys.exit(main())
