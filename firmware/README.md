# ARES node firmware (ESP32, PlatformIO)

One source, four builds. Node A carries the PIR, the optional temp sensor, the buzzer
and the two status LEDs. Node B carries the water sensor. The malicious builds are
byte-for-byte the honest ones plus an attack switch that only the gateway can flip.

## Wiring (see include/config.h; change pins there)

| Node | Part            | Pin              | Notes                                         |
|------|-----------------|------------------|-----------------------------------------------|
| A    | PIR OUT         | GPIO16           | VCC: try 3V3 first; many PIR modules need 5 V (VIN) |
| A    | DS18B20 DATA    | GPIO21           | 4.7 kΩ pull-up to 3V3; optional, drop if flaky |
| A    | buzzer          | GPIO15           | active HIGH                                    |
| A, B | status LED 1/2  | GPIO2 / GPIO12   | 00 normal · 01 warning · 10 shadow · 11 challenge |
| B    | water sensor AO | GPIO36 (VP)      | 3V3; input-only ADC1 pin                       |

Both boards go to the laptop over USB **data** cables.

## Build and flash

```bash
cd firmware
python make_secrets.py                              # needs ../gateway/keys.json (run the gateway once)
pio run -e nodeA -t upload --upload-port COM3
pio run -e nodeB -t upload --upload-port COM4
pio device monitor -p COM3 -b 115200
```

First line after boot:

```
{"t":"boot","node_id":"A","build":"honest","fw":"<sha256 of the running partition>"}
```

Paste that `fw` into `../gateway/known_fw.json` for the node, run `make_secrets.py`
again, then build the malicious variant:

```bash
pio run -e nodeA_malicious -t upload --upload-port COM3
```

The malicious build reports the honest fingerprint while idle and its real (different)
one while attacking, so it looks clean until it lies and fails the integrity challenge
the moment it does. Honest builds ignore attack commands entirely.

## What the board says and hears (CONTRACTS.md)

Out, every second:
```
{"t":"tel","node_id":"A","seq":41,"ts":120334,"motion":1,"temp":24.50,"hmac":"…"}
{"t":"tel","node_id":"B","seq":41,"ts":120334,"water":0,"water_raw":812,"hmac":"…"}
```
In:
```
{"t":"chal","challenge_id":"c-1043","type":"identity","nonce":"…"}   -> {"t":"resp",…}
{"t":"alarm","on":1,"reason":"…"}                                   -> buzzer
{"t":"led","code":2}                                                -> status LEDs
{"t":"atk","mode":"suppress"|"inject"|"drift"|"restore"}            -> malicious only
```

## Bench test without the gateway

Open the serial monitor and paste a line:

```
{"t":"chal","challenge_id":"x1","type":"integrity","nonce":"abc"}
```

The board answers with a `resp` line within a few milliseconds. Paste
`{"t":"alarm","on":1}` and the buzzer sounds.

## Tuning

- `WATER_WET_THRESHOLD` in config.h: watch `water_raw` dry vs in the tray, pick the middle.
- PIR modules have a hold time pot; set it to the minimum so motion clears quickly.
