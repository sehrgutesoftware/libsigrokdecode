#
# This file is part of the libsigrokdecode project.
#
# Copyright (C) 2021 Joseph Paul <joseph@sehrgute.software>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.
#

from rdm.rdm import CommandClass, PID


def format_value(value, fmt, size=1):
    if fmt == 'dec':
        return '{:d}'.format(value)
    if fmt == 'hex':
        return '{:0{}X}'.format(value, size*2)
    if fmt == 'bin':
        return '{:0{}b}'.format(value, size*8)

    return '{}'.format(value)

class Container:
    @property
    def fields(self):
        return {key: value for key, value in self.__dict__.items() if isinstance(value, Field)}

    def __str__(self):
        return '{}{{{}}}'.format(
            self.__class__.__name__,
            ', '.join(['{}: {}'.format(key, str(field)) for key, field in self.fields.items()])
        )

    def static_size(self):
        size = 0
        for key, field in self.fields.items():
            if field.size is None:
                continue
            size += field.size
        return size


class Field:
    START_CODE = 'START_CODE'
    SUB_START_CODE = 'SUB_START_CODE'
    LENGTH = 'LENGTH'
    DESTINATION = 'DESTINATION'
    SOURCE = 'SOURCE'
    TN = 'TN'
    PORT_ID = 'PORT_ID'
    COUNT = 'COUNT'
    SUB_DEVICE = 'SUB_DEVICE'
    DATA = 'DATA'
    CHECKSUM = 'CHECKSUM'

    def __init__(self, type, size=1):
        self.ss = None
        self.es = None
        self.value = None
        self.type = type
        self.size = size

    def load(self, data):
        self.value = 0
        self.ss = data[0][0]
        self.es = data[-1][1]
        for i in range(self.size):
            self.value |= data[self.size-i-1][2] << (i*8)

    def format(self, fmt):
        return format_value(self.value, fmt, self.size)

    def __str__(self):
        return '{}{{{} ss:{} es:{} size:{} value:{}}}'.format(
            self.__class__.__name__,
            self.type,
            self.ss,
            self.es,
            self.size,
            self.value,
        )


class EnumValueField(Field):
    def __init__(self, type, enum, size=1):
        super(EnumValueField, self).__init__(type, size)
        self.enum = enum

    def format(self, fmt):
        value = self.enum.get_name(self.value)

        if value is None:
            return super(EnumValueField, self).format(fmt)

        return value


class DataField(Field):
    def __init__(self, type, size=1):
        super(DataField, self).__init__(type, size)
        self.value = []
        self.compact_value = 0

    def load(self, data):
        self.ss = data[0][0]
        self.es = data[-1][1]
        self.value = [i[2] for i in data]
        for i in range(self.size):
            self.compact_value |= data[self.size-i-1][2] << (i*8)

    def format(self, fmt):
        if self.value is None:
            return ''

        return ' '.join([format_value(i, fmt) for i in self.value])


class DestinationField(DataField):
    BROADCAST = 0xFFFFFFFFFFFF
    MANUF_ALL = 0xFFFFFFFF

    def format(self, fmt):
        if self.compact_value == self.BROADCAST:
            return 'BROADCAST'
        if self.compact_value & self.MANUF_ALL == self.MANUF_ALL:
            manuf = (self.compact_value & 0xFFFF00000000) >> 32
            return 'MANUFACTURER {}'.format(format_value(manuf, fmt, 2))

        return super(DestinationField, self).format(fmt)


class MessageField(DataField, Container):
    CC = 'CC'
    PID = 'PID'
    PDL = 'PDL'
    PD = 'PD'

    def __init__(self, type, size=1):
        super(MessageField, self).__init__(type, size)
        self.command_class = EnumValueField(MessageField.CC, CommandClass, 1)
        self.pid = EnumValueField(MessageField.PID, PID, 2)
        self.pdl = Field(MessageField.PDL, 1)
        self.pd = DataField(MessageField.PD, None)

    def load(self, data):
        super(MessageField, self).load(data)

        cursor = 0
        for name, field in self.fields.items():
            field.load(data[cursor:cursor+field.size])
            cursor += field.size

            if field.type == MessageField.PDL:
                self.pd.size = self.pdl.value

                # Data field is empty and zero size
                if self.pdl.value == 0:
                    del self.pd
                    break
