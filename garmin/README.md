# House Tools watch app (Garmin fēnix 6S Pro / 6X Pro)

Pick a room (Ryan's first), then Alarm, Benny Hill or Chime; the server's `/watch/`
endpoint plays it on that room's Echo through Voice Monkey.

## Build

Needs the Connect IQ SDK (SDK Manager), `brew install openjdk@17`, a developer key at
`~/.connectiq/developer_key.der`, and `secrets/properties.xml` holding the token:

```xml
<properties>
    <property id="token" type="string">SAME VALUE AS WATCH_TOKEN ON APPLIKU</property>
</properties>
```

Sideloaded apps can't have settings edited in Garmin Connect, so the token is compiled in.

```
export JAVA_HOME=$(brew --prefix openjdk@17)
"$(cat ~/Library/Application\ Support/Garmin/ConnectIQ/current-sdk.cfg)bin/monkeyc" \
  -d fenix6spro -f monkey.jungle -o bin/HouseTools.prg -y ~/.connectiq/developer_key.der
```

## Install

Plug the watch in, open OpenMTP, copy `bin/HouseTools.prg` into `GARMIN/APPS/`, unplug.
