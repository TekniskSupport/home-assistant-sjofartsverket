"""
Get data from sjofartsverket.se
"""

import logging
import json
import re

from collections import namedtuple
from datetime import timedelta

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.components.rest import RestData
from homeassistant.const import (CONF_NAME)
from dateutil import parser
from datetime import datetime

_LOGGER = logging.getLogger(__name__)
_ENDPOINT = 'https://services.viva.sjofartsverket.se:8080/output/vivaoutputservice.svc/vivastation/'

DEFAULT_NAME = 'Sjofartsverket'
DEFAULT_INTERVAL = 5
DEFAULT_VERIFY_SSL = True
CONF_LOCATION = 'location'
NUMERIC_VALUES = 'numeric_values'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Required(CONF_LOCATION, default=0): cv.string,
    vol.Required(NUMERIC_VALUES, default=False): cv.boolean,
})

SCAN_INTERVAL = timedelta(minutes=DEFAULT_INTERVAL)

async def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    name = config.get(CONF_NAME)
    location = config.get(CONF_LOCATION)
    force_numeric = config.get(NUMERIC_VALUES)

    if "," in location:
        location = location.split(",")

    if isinstance(location, list):
        for locationId in location:
            await add_sensors(hass, config, async_add_devices, name, locationId, force_numeric, discovery_info)
    else:
        await add_sensors(hass, config, async_add_devices, name, location, force_numeric, discovery_info)

async def add_sensors(hass, config, async_add_devices, name, location, force_numeric, discovery_info=None):
    method     = 'GET'
    payload    = ''
    encoding   = 'utf-8'
    auth       = None
    verify_ssl = DEFAULT_VERIFY_SSL
    headers    = {}
    params     = {}
    timeout    = 5000
    endpoint   = _ENDPOINT + location

    rest = RestData(hass, method, endpoint, encoding, auth, headers, params, payload, verify_ssl, timeout)
    await rest.async_update()

    if rest.data is None:
        _LOGGER.error("Unable to fetch data from Sjöfartsverket")
        return False

    restData = json.loads(rest.data)
    sensors = []
    location = restData['GetSingleStationResult']['Name']
    for data in restData['GetSingleStationResult']['Samples']:
        sensors.append(entityRepresentation(rest, name, location, force_numeric, data))
    async_add_devices(sensors, True)

# pylint: disable=no-member
class entityRepresentation(Entity):
    """Representation of a sensor."""

    def __init__(self, rest, prefix, location, force_numeric, data):
        """Initialize a sensor."""
        self._rest = rest
        self._prefix = prefix
        self._location = location
        self._force_numeric = force_numeric
        self._data = data
        self._attributes = {}

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the device."""
        if self._state is not None:
            return self._state
        return None

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the monitored installation."""
        if self._attributes is not None:
            return self._attributes

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        if self._unit is not None:
            return self._unit

    @property
    def icon(self):
        return 'mdi:ferry'

    async def async_update(self):
        """Get the latest data from the API and updates the state."""
        try:
            getAttributes = [
                "Trend",
                "Msg",
                "Calm",
                "Heading",
                "WaterLevelReference",
                "WaterLevelOffset",
            ]

            await self._rest.async_update()
            self._result                   = json.loads(self._rest.data)
            self._name                     = self._prefix + '_' + self._location + '_' + self._data['Name']
            for data in self._result['GetSingleStationResult']['Samples']:
                if self._name == self._prefix + '_' + self._location + '_' + data['Name']:
                    if (self._force_numeric):
                        try:
                            extractedValue = float(re.findall("[\d\.]+", data['Value'])[0])
                            self._state   = extractedValue
                            self._attributes.update({"Original": data['Value']})
                            self._attributes.update({"Additional": data['Value'].replace(str(extractedValue),'')})
                        except:
                            self._state   = data['Value']
                    else:
                        self._state   = data['Value']
                    self._unit = data['Unit']
                    self._attributes.update({"type"         : data['Type']})
                    self._attributes.update({"last_modified": data['Updated']})
                    for attribute in data:
                        if attribute in getAttributes and data[attribute]:
                            self._attributes.update({attribute: data[attribute]})
        except TypeError as e:
            self._result = None
            _LOGGER.error(
                "Unable to fetch data from sjofartsverket. " + str(e))
