"""Support for P2000 Lifeliners sensors."""
import datetime
import logging

import feedparser
import re
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    CONF_ICON,
)
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.dispatcher import dispatcher_send
from homeassistant.helpers.event import async_track_time_interval
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.restore_state import RestoreEntity

_LOGGER = logging.getLogger(__name__)

BASE_URL = "http://feeds.feedburner.com/p2000-life-liners"

DEFAULT_INTERVAL = datetime.timedelta(seconds=20)
DATA_UPDATED = "p2000_lifeliners_data_updated"

CONF_CAPCODES = "capcodes"
CONF_ATTRIBUTION = "Data provided by www.p2000zhz-rr.nl"
CONF_CONTAINS = "contains"

DEFAULT_NAME = "P2000 Lifeliners"
DEFAULT_ICON = "mdi:helicopter"


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_INTERVAL): vol.All(
                    cv.time_period, cv.positive_timedelta
                ),
        vol.Optional(CONF_CAPCODES): cv.string,
        vol.Optional(CONF_CONTAINS): cv.string,
        vol.Optional(CONF_ICON, default=DEFAULT_ICON): cv.icon,
    }
)


async def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Set up the P2000 sensor."""
    data = P2000Data(hass, config)

    async_track_time_interval(hass, data.async_update, config[CONF_SCAN_INTERVAL])

    async_add_devices([P2000Sensor(hass, data, config.get(CONF_NAME), config.get(CONF_ICON))], True)


class P2000Data:
    """Handle P2000 object and limit updates."""

    def __init__(self, hass, config):
        """Initialize the data object."""
        self._hass = hass
        self._url = BASE_URL
        self._capcodes = config.get(CONF_CAPCODES)
        self._contains = config.get(CONF_CONTAINS)
        self._capcodelist = None
        self._feed = None
        self._etag = None
        self._modified = None
        self._restart = True
        self._event_time = None
        self._data = None

        if self._capcodes:
            self._capcodelist = self._capcodes.split(",")

    @property
    def latest_data(self):
        """Return the data object."""
        return self._data

    @staticmethod
    def _convert_time(time):
        return datetime.datetime.strptime(time.split(",")[1][:-6], " %d %b %Y %H:%M:%S")
        
    @staticmethod
    def remove_img_tags(data):
        p = re.compile(r'&lt;.*?&gt;')
        return p.sub('', data)

    async def async_update(self, dummy):
        """Update data."""

        if self._feed:
            self._modified = self._feed.get("modified")
            self._etag = self._feed.get("etag")
        else:
            self._modified = None
            self._etag = None

        self._feed = await self._hass.async_add_executor_job(
            feedparser.parse, self._url, self._etag, self._modified
        )

        if not self._feed:
            _LOGGER.debug("Failed to get feed data from %s", self._url)
            return

        if self._feed.bozo:
            _LOGGER.debug("Error parsing feed data from %s", self._url)
            return

        _LOGGER.debug("Feed url: %s data: %s", self._url, self._feed)

        if self._restart:
            self._restart = False
            self._event_time = self._convert_time(self._feed.entries[0]["published"])
            _LOGGER.debug("Start fresh after a restart")
            return

        try:
            for entry in reversed(self._feed.entries):

                event_msg = ""
                event_caps = ""
                event_time = self._convert_time(entry.published)
                if event_time < self._event_time:
                    continue
                self._event_time = event_time
                event_raw = entry.title.replace("~", "") + "\n" + entry.published + "\n"
                _LOGGER.debug("New P2000 Lifeliners event found: %s, at %s", event_msg, entry.published)

                event_msg = self.remove_img_tags(event_raw)

                if self._capcodelist:
                    _LOGGER.debug("Filtering on Capcode(s) %s", self._capcodelist)
                    capfound = False
                    for capcode in self._capcodelist:
                        _LOGGER.debug(
                            "Searching for capcode %s in %s", capcode.strip(), event_caps,
                        )
                        if event_caps.find(capcode) != -1:
                            _LOGGER.debug("Capcode filter matched")
                            capfound = True
                            break
                        _LOGGER.debug("Capcode filter mismatch, discarding")
                        continue
                    if not capfound:
                        continue

                if self._contains:
                    _LOGGER.debug("Filtering on Contains string %s", self._contains)
                    if event_msg.find(self._contains) != -1:
                        _LOGGER.debug("Contains string filter matched")
                    else:
                        _LOGGER.debug("Contains string filter mismatch, discarding")
                        continue

                if event_msg:
                    event = {}
                    event["msgtext"] = event_msg
                    event["msgtime"] = event_time
                    event["capcodetext"] = event_caps
                    _LOGGER.debug("Event: %s", event)
                    self._data = event

            dispatcher_send(self._hass, DATA_UPDATED)

        except ValueError as err:
            _LOGGER.error("Error parsing feed data %s", err)
            self._data = None


class P2000Sensor(RestoreEntity):
    """Representation of a P2000 Sensor."""

    def __init__(self, hass, data, name, icon):
        """Initialize a P2000 sensor."""
        self._hass = hass
        self._data = data
        self._name = name
        self._icon = icon
        self._state = None
        self.attrs = {}

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return self._icon

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def should_poll(self):
        """Return the polling requirement for this sensor."""
        return False

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if not state:
            return
        self._state = state.state
        self.attrs = state.attributes

        async_dispatcher_connect(
            self._hass, DATA_UPDATED, self._schedule_immediate_update
        )

    @callback
    def _schedule_immediate_update(self):
        self.async_schedule_update_ha_state(True)

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        attrs = {}
        data = self._data.latest_data
        if data:
            attrs["capcodes"] = data["capcodetext"]
            attrs["time"] = data["msgtime"]
            attrs[ATTR_ATTRIBUTION] = CONF_ATTRIBUTION
            self.attrs = attrs

        return self.attrs

    def update(self):
        """Update current values."""
        data = self._data.latest_data
        if data:
            self._state = data["msgtext"]
            _LOGGER.debug("State updated to %s", self._state)
