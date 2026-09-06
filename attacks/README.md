# Attack scripts

Laptop-side attackers for the demo. They talk to the gateway's HTTP inbox, the same
door the vision service uses, so they work in both `sim` and `serial` mode and can be
run from a second laptop to show the attack coming from outside.

```bash
../gateway/.venv/Scripts/python spoof.py  --node A        # forged signature -> identity 0, SHADOW
../gateway/.venv/Scripts/python replay.py --node A        # genuine captured frames re-sent -> rejected on seq
```

The judge panel's SPOOF and REPLAY buttons do the same thing from inside the gateway
(`POST /attack`), which is what the live demo uses. These scripts exist for the
"show me it from the outside" question.

`drift` is not here: it is a firmware mode on the malicious builds (`{"t":"atk","mode":"drift"}`),
triggered by the DRIFT button, and in the simulator.
