# Attacking ARES over MQTT from another PC

The sensor nodes talk to the gateway over USB serial. MQTT is **only** an extra ingress
so a second machine can attack the mesh over the network, the way a real intruder would.
Turning it on cannot affect the honest serial path.

```
  ATTACKER PC                     BROKER (Mosquitto)                 GATEWAY LAPTOP
  mqtt_attack.py / mosquitto_pub  ---- ares/inject/A -->  subscribes, feeds ARES engine
                                  <--- ares/A/telemetry --  (only with --mqtt-echo)
```

## 1. Run the broker

Mosquitto is a broker plus CLI tools. Run the broker on whichever PC is easiest; the
attacker PC usually already has it. Allow anonymous connections on the LAN:

`mosquitto.conf`
```
listener 1883 0.0.0.0
allow_anonymous true
```
```
mosquitto -c mosquitto.conf -v
```

Both PCs must be on the same hotspot. Note the broker PC's IP (e.g. `10.212.204.125`).
On Windows, allow port 1883 through the firewall the first time.

## 2. Start the gateway pointing at the broker

```
cd gateway
.venv\Scripts\python run.py --mode serial --ports COM3,COM5 --mqtt-host <BROKER_IP> --mqtt-echo
```

`--mqtt-echo` republishes each honest frame to `ares/<node>/telemetry` so the attacker
can capture a genuine frame and replay it. Leave it off if you only want the spoof demo.
Check it connected: `GET /health` shows `"mqtt": {"connected": true}`, and the log prints
`[mqtt] connected; listening for injected frames on ares/inject/#`.

## 3. Attack from the other PC

```
# impersonation: publish as node A with no key
python attacks\mqtt_attack.py --broker <BROKER_IP> --node A --mode spoof
# or with the mosquitto CLI:
mosquitto_pub -h <BROKER_IP> -t ares/inject/A -m "{\"seq\":9999,\"motion\":1,\"hmac\":\"bad\"}"

# replay: sniff a real signed frame, then send it back (needs --mqtt-echo)
python attacks\mqtt_attack.py --broker <BROKER_IP> --node A --mode replay
```

What ARES does, visible live on the dashboard:

| Attack | Why it fails | What shows on the dashboard |
|--------|--------------|------------------------------|
| spoof  | forged frame has no valid HMAC -> identity 0 -> node A to SHADOW | the forged value appears as a **REJECTED** ghost reading (source `mqtt-attacker`); the real reading is untouched; trust bar collapses; node greys out |
| replay | signature is genuine but the sequence number is stale -> rejected -> SHADOW | `replay_rejected` event; node to SHADOW |

The point to say out loud: the attacker *did* push a value over the network, ARES showed
it and refused it. The trusted reading never changed. **Authentic beats authenticated.**

In both cases node A's real serial telemetry keeps arriving honestly; the attack rides in
over the network and is caught without touching the board. This is the same outcome as the
local `spoof.py` / `replay.py` scripts, but the frames genuinely cross the network from a
separate machine.

## Notes

- The gateway retries the broker automatically if it is not up yet.
- `ares/inject/<node>` accepts any node id (`A`, `B`, `C`, `WEBCAM`).
- Verified end to end against a real broker on 2026-09-06: spoof and replay both shadow
  the target.
