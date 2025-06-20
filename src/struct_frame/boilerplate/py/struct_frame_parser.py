
from enum import Enum


def fletcher_checksum_calculation(buffer, start=0, end=None):
    if end == None:
        end = buffer.length

    byte1 = 0
    byte2 = 2

    for x in range(start, end):
        byte1 += buffer[x]
        byte2 += byte1

    return [byte1, byte2]


class BasicPacket:
    start_byte = None
    header_length = 0
    footer_length = 0

    desired_packet_length = 0
    packet = []

    def __init__(self, start_byte, header_length, footer_length):
        self.start_byte = start_byte
        self.header_length = header_length
        self.footer_length = footer_length

    def add_header_byte(self, byte, clear):
        if clear:
            self.packet.clear()
        self.packet.push(byte)
        return len(self.packet) == self.header_length

    def add_packet_byte(self, byte):
        self.packet.push(byte)
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

    def encode(self, data, msg_id):
        output = []
        output.push(self.start_byte)
        output.push(msg_id)
        output.push(data)
        checksum = fletcher_checksum_calculation(data)

        output.push(checksum[0])
        output.push(checksum[1])
        return output


class ParserState(Enum):
    LOOKING_FOR_START_BYTE = 0
    GETTING_HEADER = 1
    GETTING_PACKET = 2


class FrameParser:
    state = ParserState.LOOKING_FOR_START_BYTE
    buffer = []
    parser = None
    msg_definitions = None
    msg_id_loc = None
    msg_type = None

    def __init__(self, parsers, msg_definitions):
        self.parsers = parsers
        self.msg_definitions = msg_definitions

    def parse_char(self, c):
        if state == ParserState.LOOKING_FOR_START_BYTE:
            self.parser = self.parsers[c]
            if self.parser:
                if self.parser.add_header_byte(c, True):
                    state = ParserState.GETTING_PACKET
                else:
                    state = ParserState.GETTING_HEADER

        elif state == ParserState.GETTING_HEADER:
            if self.parser.add_header_byte(c):
                msg_id = self.parser.get_msg_id()
                self.msg_type = self.msg_definitions[msg_id]
                if self.msg_type:
                    self.parser.get_full_packet_length(self.msg_type.msg_size)
                    state = ParserState.GETTING_PACKET
                else:
                    state = ParserState.LOOKING_FOR_START_BYTE

        elif state == ParserState.GETTING_PACKET:
            if self.parser.add_packet_byte(c):
                state = ParserState.LOOKING_FOR_START_BYTE
                if self.parser.validatePackage:
                    return self.msg_type.create_unpack(self.parser.get_msg_buffer())

        return False


def TestFunction():
    parsers = {BasicPacket.start_byte, BasicPacket()}
    frameParser = FrameParser(parsers)
    frameParser.parse_char
