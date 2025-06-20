
from enum import Enum


def fletcher_checksum_calculation(buffer, start=0, end=None):
    if end == None:
        end = len(buffer)

    byte1 = 0
    byte2 = 0

    for x in range(start, end):
        byte1 += buffer[x]
        byte2 += byte1

    return [byte1, byte2]


class BasicPacket:
    start_byte = 0x90
    header_length = 0
    footer_length = 0

    desired_packet_length = 0
    packet = []

    def __init__(self, start_byte=0x90, header_length=2, footer_length=2):
        self.start_byte = start_byte
        self.header_length = header_length
        self.footer_length = footer_length

    def add_header_byte(self, byte, clear=False):
        if clear:
            self.packet.clear()
        self.packet.append(byte)
        return len(self.packet) == self.header_length

    def add_packet_byte(self, byte):
        self.packet.append(byte)
        return len(self.packet) == self.desired_packet_length

    def get_msg_id(self):
        return self.packet[1]

    def get_full_packet_length(self, msg_length):
        self.desired_packet_length = self.header_length + self.footer_length + msg_length
        return self.desired_packet_length

    def validate_packet(self):
        checksum = fletcher_checksum_calculation(
            self.packet, self.header_length, self.desired_packet_length - self.footer_length)
        return checksum[0] == self.packet[-2] and checksum[1] == self.packet[-1]

    def get_msg_buffer(self):
        return self.packet[self.header_length:self.desired_packet_length - self.footer_length]

    def encode_msg(self, msg):
        return self.encode(msg.pack(), msg.msg_id)

    def encode(self, data, msg_id):
        output = []
        output.append(self.start_byte)
        output.append(msg_id)
        if (len(data)):
            for b in data:
                output.append(b)
        checksum = fletcher_checksum_calculation(data)

        output.append(checksum[0])
        output.append(checksum[1])
        return output


class ParserState(Enum):
    LOOKING_FOR_START_BYTE = 0
    GETTING_HEADER = 1
    GETTING_PACKET = 2


class FrameParser:
    state = ParserState.LOOKING_FOR_START_BYTE
    buffer = []
    packetFormat = None
    msg_definitions = None
    msg_id_loc = None
    msg_type = None

    def __init__(self, packetFormats, msg_definitions):
        self.packetFormats = packetFormats
        self.msg_definitions = msg_definitions

    def parse_char(self, c):
        if self.state == ParserState.LOOKING_FOR_START_BYTE:
            self.packetFormat = self.packetFormats[c]
            if self.packetFormat:
                if self.packetFormat.add_header_byte(c, True):
                    self.state = ParserState.GETTING_PACKET
                else:
                    self.state = ParserState.GETTING_HEADER

        elif self.state == ParserState.GETTING_HEADER:
            if self.packetFormat.add_header_byte(c):
                msg_id = self.packetFormat.get_msg_id()
                self.msg_type = self.msg_definitions[msg_id]
                if self.msg_type:
                    self.packetFormat.get_full_packet_length(
                        self.msg_type.msg_size)
                    self.state = ParserState.GETTING_PACKET
                else:
                    self.state = ParserState.LOOKING_FOR_START_BYTE

        elif self.state == ParserState.GETTING_PACKET:
            if self.packetFormat.add_packet_byte(c):
                self.state = ParserState.LOOKING_FOR_START_BYTE
                if self.packetFormat.validate_packet():
                    return self.msg_type.create_unpack(bytes(self.packetFormat.get_msg_buffer()))

        return False
