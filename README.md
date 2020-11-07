[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs)  [![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/) [![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.me/cyberjunkynl/)

# P2000 Lifeliners Sensor Component
This is a Custom Component for Home-Assistant (https://home-assistant.io) that tracks P2000 Lifeliners emergency events in The Netherlands.

## About
This component queries http://feeds.feedburner.com/p2000-life-liners at the configured interval and applies filters for capcodes specified.

When events are found the P2000 Lifeliners sensor state gets set, which you can use to trigger automation, display sensor data.

## Installation

### Manual
- Copy directory `custom_components/p2000lifeliners` to your `<config dir>/custom_components` directory.
- Configure with config below.
- Restart Home-Assistant.

## Usage
To use this component in your installation, add the following to your `configuration.yaml` file:

```yaml
# Example configuration.yaml entries

sensor:
  - platform: p2000lifeliners
    name: LIFELN1 VUmc
    capcodes: 120901

  - platform: p2000lifeliners
    name: LIFELN2 Rotterdam
    capcodes: 1420059

  - platform: p2000lifeliners
    name: LIFELN3 Volkel
    capcodes: 923993

  - platform: p2000lifeliners
    name: LIFELN5 Lelystad Corona
    capcodes: 923995

  - platform: p2000lifeliners
    name: MEDIC1 Leeuwarden
    capcodes: 320591
```

Configuration variables:

- **scan_interval** (*Optional*): Check every x seconds. (default = 20)
- **name** (*Optional*): Name for sensor.
- **capcodes** (*Optional*): Capcode(s) you want to filter on. http://capcode.nl
- **contains** (*Optional*): Search for events which contains this word exactly how it is written, for example GRIP


You can use a state trigger event to send push notifications like this:
```yaml
# Example automation.yaml entry

automation:
  - alias: 'P2000 Lifeliners Bericht'
    trigger:
      platform: state
      entity_id:
        - sensor.lifeln1_vumc
        - sensor.lifeln2_rotterdam
        - sensor.lifeln3_volkel
        - sensor.lifeln5_lelystad_corona
        - sensor.medic1_leeuwarden
    action:
      - service_template: notify.html5
        data:
          title: "P2000 Lifeliners"
          message: >
            {{ trigger.to_state.attributes.friendly_name }} is onderweg naar {{ trigger.to_state.state }}
```


## Screenshots

![alt text](https://github.com/cyberjunky/home-assistant-p2000lifeliners/blob/master/screenshots/p2000lifeliners.png?raw=true "Screenshot Sensor")

## Lovelace card example:

```yaml
cards:
      - entity: sensor.lifeln1_vumc
        name: P2000 Lifeliner VUmc
        type: sensor
```

## Debugging
If you experience unexpected output, please create an issue.
Share your configuration and post some debug log info.
You can obtain this by adding this line to your config and restart homeassistant.


```
logger:
  default: info
  logs:
      custom_components.p2000lifeliners: debug
```

## Donation
[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.me/cyberjunkynl/)
