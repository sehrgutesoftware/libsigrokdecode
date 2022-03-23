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


import sigrokdecode as srd
import json
from pprint import pprint

from rdm.rdm import StartCode
from rdm.packet import RDMPacket
from rdm.field import Field, MessageField, Container


class Ann:
    TYPE, \
        START_CODE, SUB_START_CODE, LENGTH, DESTINATION, SOURCE, TN, PORT_ID, COUNT, SUB_DEVICE, DATA, CHECKSUM, \
        CC, PID, PDL, PD, \
        CHECKSUM_PASS, CHECKSUM_FAIL = range(18)


class Decoder(srd.Decoder):
    api_version = 3
    id = 'rdm'
    name = 'RDM'
    longname = 'Remote Device Management'
    desc = 'Remote Device Management extension to the DMX512 protocol (ANSI E1.20).'
    license = 'gplv2+'
    inputs = ['dmx512']
    outputs = ['rdm']
    tags = ['Embedded/industrial', 'Lighting']
    options = (
        {'id': 'format', 'desc': 'Data format', 'default': 'hex',
            'values': ('dec', 'hex', 'bin')},
    )
    annotations = (
        # Packet type
        ('type', 'Type'),
        # Packet structure
        ('start_code', 'Start Code'),
        ('sub_start_code', 'Sub Start Code'),
        ('length', 'Length'),
        ('destination', 'Destination'),
        ('source', 'Source'),
        ('tn', 'Transaction Number'),
        ('port_id', 'Port ID'),
        ('count', 'Message Count'),
        ('sub_device', 'Sub-Device'),
        ('data', 'Data'),
        ('checksum', 'Checksum'),
        # Packet Message
        ('cc', 'Command Class'),
        ('pid', 'Parameter ID'),
        ('pdl', 'Parameter Data Length'),
        ('pd', 'Parameter Data'),
        # Validation
        ('checksum_pass', 'Checksum Pass'),
        ('checksum_fail', 'Checksum Fail'),
    )
    annotation_rows = (
        ('types', 'Type', (Ann.TYPE,)),
        ('packets', 'Packet', (
            Ann.START_CODE, Ann.SUB_START_CODE, Ann.LENGTH,
            Ann.DESTINATION, Ann.SOURCE,
            Ann.TN, Ann.PORT_ID, Ann.COUNT, Ann.SUB_DEVICE,
            Ann.DATA,
            Ann.CHECKSUM,
        )),
        ('messages', 'Message', (Ann.CC, Ann.PID, Ann.PDL, Ann.PD)),
        ('validation', 'Validation', (Ann.CHECKSUM_PASS, Ann.CHECKSUM_FAIL)),
    )

    type_ann_map = {
        Field.START_CODE: Ann.START_CODE,
        Field.SUB_START_CODE: Ann.SUB_START_CODE,
        Field.LENGTH: Ann.LENGTH,
        Field.DESTINATION: Ann.DESTINATION,
        Field.SOURCE: Ann.SOURCE,
        Field.TN: Ann.TN,
        Field.PORT_ID: Ann.PORT_ID,
        Field.COUNT: Ann.COUNT,
        Field.SUB_DEVICE: Ann.SUB_DEVICE,
        Field.DATA: Ann.DATA,
        Field.CHECKSUM: Ann.CHECKSUM,
        MessageField.CC: Ann.CC,
        MessageField.PID: Ann.PID,
        MessageField.PDL: Ann.PDL,
        MessageField.PD: Ann.PD,
    }

    def __init__(self):
        self.reset()

    def reset(self):
        pass

    def metadata(self, key, value):
        pass

    def start(self):
        self.out_ann = self.register(srd.OUTPUT_ANN)
        self.out_python = self.register(srd.OUTPUT_PYTHON)

    def putg(self, ss, es, data):
        self.put(ss, es, self.out_ann, data)

    def putpy(self, ss, es, data):
        self.put(ss, es, self.out_python, data)

    def decode(self, ss, es, data):
        type, payload = data
        if type != 'PACKET':
            return

        packet = self.parse_packet(ss, es, payload)
        if packet is None:
            return

        self.put_packet(ss, es, packet)
        self.put_fields(packet)
        self.put_checksum(packet)

    def parse_packet(self, ss, es, data):
        if len(data) < 1:
            return None

        s, e, start_code, valid = data[0]
        if not valid:
            return None
        if not start_code == StartCode.RDM:
            return None

        return RDMPacket.parse(data)

    def put_packet(self, ss, es, packet):
        self.putpy(ss, es, packet)
        self.putg(ss, es, [Ann.TYPE, ['RDM Packet', 'Packet', 'P']])

    def put_fields(self, packet):
        for key, field in packet.fields.items():
            ann = self.map_ann(field.type)
            if ann is None:
                continue

            value = field.format(self.options['format'])

            # print(field)
            self.putg(field.ss, field.es, [ann, [
                '{}: {}'.format(field.type, value),
                value,
            ]])

            if isinstance(field, Container):
                self.put_fields(field)

    def put_checksum(self, packet):
        if packet.is_checksum_valid():
            self.putg(packet.checksum.ss, packet.checksum.es, [Ann.CHECKSUM_PASS, ['RDM Checksum Pass', 'Checksum Pass', 'Pass', 'P']])
        else:
            self.putg(packet.checksum.ss, packet.checksum.es, [Ann.CHECKSUM_FAIL, ['RDM Checksum Fail', 'Checksum Fail', 'Fail', 'F']])

    def map_ann(self, type):
        if type not in self.type_ann_map:
            return None
        return self.type_ann_map[type]
