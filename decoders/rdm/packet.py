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

from rdm.field import Container, Field, DataField, MessageField, DestinationField


class RDMPacket(Container):
    def __init__(self):
        self.start_code = Field(Field.START_CODE, 1)
        self.sub_start_code = Field(Field.SUB_START_CODE, 1)
        self.length = Field(Field.LENGTH, 1)
        self.destination = DestinationField(Field.DESTINATION, 6)
        self.source = DataField(Field.SOURCE, 6)
        self.tn = Field(Field.TN, 1)
        self.port_id = Field(Field.PORT_ID, 1)
        self.count = Field(Field.COUNT, 1)
        self.sub_device = Field(Field.SUB_DEVICE, 2)
        self.data = MessageField(Field.DATA, None)
        self.checksum = Field(Field.CHECKSUM, 2)
        self.raw_data = []

    @classmethod
    def parse(cls, data):
        instance = cls()

        instance.raw_data = [i[2] for i in data]

        cursor = 0
        for name, field in instance.fields.items():
            field.load(data[cursor:cursor+field.size])
            cursor += field.size

            if field.type == Field.LENGTH:
                instance.data.size = instance.length.value - (instance.static_size() - instance.checksum.size)

        return instance

    def is_checksum_valid(self):
        s = 0
        for byte in self.raw_data[:-2]:
            s += byte % 0x10000

        return (s - self.checksum.value) == 0
