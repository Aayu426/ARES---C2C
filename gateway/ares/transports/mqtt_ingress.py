"""MQTT attack ingress. Lets an attacker on another PC inject frames over a Mosquitto
broker, without touching the honest USB-serial path.

The gateway CONNECTS OUT to a broker (usually running on the attacker's PC) and:
  - subscribes to `ares/inject/<node>` : any frame published here is fed to the engine
    exactly as if it had arrived from that node. No key -> bad HMAC -> impersonation
    caught. A genuine captured frame re-sent here -> replay caught on the sequence.
  - (optional --mqtt-echo) republishes every honest telemetry frame it accepts to
    `ares/<node>/telemetry`, so an attacker can `mosquitto_sub` to capture a real signed
    frame and then replay it. Off by default.

This is deliberately a separate ingress, not a Transport: it can only inject inbound
messages, never carry honest traffic, so enabling it cannot break the working demo."""
from __future__ import annotations

import asyncio
import json

import paho.mqtt.client as mqtt

INJECT_TOPIC = "ares/inject/#"
ECHO_TOPIC = "ares/{node}/telemetry"


class MqttIngress:
    def __init__(self, engine, host: str, port: int = 1883, echo: bool = False) -> None:
        self.engine = engine
        self.host = host
        self.port = port
        self.echo = echo
        self.loop: asyncio.AbstractEventLoop | None = None
        self.connected = False
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="ares-gateway")
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

    async def start(self, loop: asyncio.AbstractEventLoop) -> None:
        self.loop = loop
        try:
            self.client.connect_async(self.host, self.port, keepalive=30)
            self.client.loop_start()
            print(f"[mqtt] connecting to broker {self.host}:{self.port} (attack ingress)", flush=True)
        except Exception as exc:
            print(f"[mqtt] cannot reach broker {self.host}:{self.port}: {exc!r}", flush=True)
        if self.echo:
            self.engine.mqtt_echo = self._echo   # engine calls this on each accepted honest frame

    async def stop(self) -> None:
        try:
            self.client.loop_stop()
            self.client.disconnect()
        except Exception:
            pass

    def _on_connect(self, client, userdata, flags, reason_code, properties=None) -> None:
        ok = not getattr(reason_code, 'is_failure', bool(int(reason_code)) if str(reason_code).isdigit() else True)
        self.connected = ok
        if ok:
            client.subscribe(INJECT_TOPIC, qos=0)
            print(f"[mqtt] connected; listening for injected frames on {INJECT_TOPIC}", flush=True)
        else:
            print(f"[mqtt] broker refused connection: {reason_code}", flush=True)

    def _on_disconnect(self, *args) -> None:
        self.connected = False
        print("[mqtt] broker connection lost (will retry)", flush=True)

    def _on_message(self, client, userdata, msg) -> None:
        try:
            data = json.loads(msg.payload.decode("utf-8"))
        except Exception:
            return
        node = msg.topic.rsplit("/", 1)[-1]
        data.setdefault("node_id", node)
        data.setdefault("t", "tel")
        if self.loop is not None:
            asyncio.run_coroutine_threadsafe(
                self.engine.on_message(data, f"mqtt-attacker:{msg.topic}"), self.loop)

    def _echo(self, frame: dict) -> None:
        if self.connected:
            try:
                self.client.publish(ECHO_TOPIC.format(node=frame.get("node_id")),
                                    json.dumps(frame, separators=(",", ":")), qos=0)
            except Exception:
                pass
