// Struct-frame boilerplate: frame parser base utilities

// Fletcher-16 checksum calculation
export function fletcherChecksum(buffer: Uint8Array | number[], start: number = 0, end?: number, 
                                 init1: number = 0, init2: number = 0): [number, number] {
    if (end === undefined) {
        end = buffer.length;
    }

    let byte1 = 0;
    let byte2 = 0;

    for (let i = start; i < end; i++) {
        byte1 = (byte1 + buffer[i]) % 256;
        byte2 = (byte2 + byte1) % 256;
    }

    // Add magic numbers at the end
    byte1 = (byte1 + init1) % 256;
    byte2 = (byte2 + byte1) % 256;
    byte1 = (byte1 + init2) % 256;
    byte2 = (byte2 + byte1) % 256;

    return [byte1, byte2];
}

// Parse result interface
export interface FrameMsgInfo {
    valid: boolean;
    msg_id: number;
    msg_len: number;
    msg_data: Uint8Array;
}

// Create default FrameMsgInfo
export function createFrameMsgInfo(): FrameMsgInfo {
    return {
        valid: false,
        msg_id: 0,
        msg_len: 0,
        msg_data: new Uint8Array(0)
    };
}

// =============================================================================
// Frame Format Configuration
// =============================================================================

/**
 * Configuration interface for frame format parsers.
 * This allows code reuse through configuration instead of code generation.
 */
export interface FrameParserConfig {
    /** Name of the frame format (e.g., 'BasicDefault', 'TinyMinimal') */
    readonly name: string;
    /** Start byte values (0, 1, or 2 bytes) */
    readonly startBytes: readonly number[];
    /** Total header size in bytes */
    readonly headerSize: number;
    /** Total footer size in bytes (usually 0 or 2 for CRC) */
    readonly footerSize: number;
    /** Whether this format includes a length field */
    readonly hasLength: boolean;
    /** Number of bytes for length field (1 or 2) */
    readonly lengthBytes: number;
    /** Whether this format includes CRC */
    readonly hasCrc: boolean;
}

// =============================================================================
// Shared Payload Parsing Functions
// =============================================================================
// These functions handle payload validation/encoding independent of framing.
// Frame formats (Tiny/Basic) use these for the common parsing logic.

/**
 * Validate a payload with CRC (shared by Default, Extended, etc. payload types).
 */
export function validatePayloadWithCrc(
    buffer: Uint8Array | number[],
    headerSize: number,
    lengthBytes: number,
    crcStartOffset: number
): FrameMsgInfo {
    const result = createFrameMsgInfo();
    const footerSize = 2; // CRC is always 2 bytes
    const overhead = headerSize + footerSize;

    if (buffer.length < overhead) {
        return result;
    }

    const msgLength = buffer.length - overhead;

    // Calculate expected CRC range: from crcStartOffset to before the CRC bytes
    const crcDataLen = msgLength + 1 + lengthBytes; // msg_id (1) + lengthBytes + payload
    const ck = fletcherChecksum(buffer, crcStartOffset, crcStartOffset + crcDataLen);

    if (ck[0] === buffer[buffer.length - 2] && ck[1] === buffer[buffer.length - 1]) {
        result.valid = true;
        result.msg_id = buffer[headerSize - 1]; // msg_id is last byte of header
        result.msg_len = msgLength;
        result.msg_data = new Uint8Array(Array.prototype.slice.call(buffer, headerSize, buffer.length - footerSize));
    }

    return result;
}

/**
 * Validate a minimal payload (no CRC, no length field).
 */
export function validatePayloadMinimal(
    buffer: Uint8Array | number[],
    headerSize: number
): FrameMsgInfo {
    const result = createFrameMsgInfo();

    if (buffer.length < headerSize) {
        return result;
    }

    result.valid = true;
    result.msg_id = buffer[headerSize - 1]; // msg_id is last byte of header
    result.msg_len = buffer.length - headerSize;
    result.msg_data = new Uint8Array(Array.prototype.slice.call(buffer, headerSize));

    return result;
}

/**
 * Encode payload with length and CRC (modifies output array in place).
 */
export function encodePayloadWithCrc(
    output: number[],
    msgId: number,
    msg: Uint8Array | number[],
    lengthBytes: number,
    crcStartOffset: number
): void {
    // Add length field
    if (lengthBytes === 1) {
        output.push(msg.length & 0xFF);
    } else {
        output.push(msg.length & 0xFF);
        output.push((msg.length >> 8) & 0xFF);
    }

    // Add msg_id
    output.push(msgId);

    // Add payload
    for (let i = 0; i < msg.length; i++) {
        output.push(msg[i]);
    }

    // Calculate and add CRC
    const crcDataLen = msg.length + 1 + lengthBytes;
    const ck = fletcherChecksum(output, crcStartOffset, crcStartOffset + crcDataLen);
    output.push(ck[0]);
    output.push(ck[1]);
}

/**
 * Encode minimal payload (no length, no CRC).
 */
export function encodePayloadMinimal(
    output: number[],
    msgId: number,
    msg: Uint8Array | number[]
): void {
    output.push(msgId);
    for (let i = 0; i < msg.length; i++) {
        output.push(msg[i]);
    }
}

// =============================================================================
// Generic Frame Parser
// =============================================================================
// This class provides a reusable frame parser that can be configured
// for different frame formats, reducing code duplication.

/** Parser state enumeration */
export enum GenericParserState {
    LOOKING_FOR_START1 = 0,
    LOOKING_FOR_START2 = 1,
    GETTING_MSG_ID = 2,
    GETTING_LENGTH = 3,
    GETTING_PAYLOAD = 4
}

/**
 * Generic frame parser that works with any frame format configuration.
 * This class eliminates the need for separate parser classes per format.
 */
export class GenericFrameParser {
    readonly config: FrameParserConfig;

    private state: GenericParserState;
    private buffer: number[];
    private packet_size: number;
    private msg_id: number;
    private msg_length: number;
    private length_lo: number;
    private get_msg_length?: (msg_id: number) => number | undefined;

    constructor(config: FrameParserConfig, get_msg_length?: (msg_id: number) => number | undefined) {
        this.config = config;
        this.get_msg_length = get_msg_length;
        this.state = this.getInitialState();
        this.buffer = [];
        this.packet_size = 0;
        this.msg_id = 0;
        this.msg_length = 0;
        this.length_lo = 0;
    }

    private getInitialState(): GenericParserState {
        if (this.config.startBytes.length === 0) {
            return GenericParserState.GETTING_MSG_ID;
        } else if (this.config.startBytes.length === 1) {
            return GenericParserState.LOOKING_FOR_START1;
        } else {
            return GenericParserState.LOOKING_FOR_START1;
        }
    }

    reset(): void {
        this.state = this.getInitialState();
        this.buffer = [];
        this.packet_size = 0;
        this.msg_id = 0;
        this.msg_length = 0;
        this.length_lo = 0;
    }

    parse_byte(byte: number): FrameMsgInfo {
        const result = createFrameMsgInfo();
        const startBytes = this.config.startBytes;
        const overhead = this.config.headerSize + this.config.footerSize;

        switch (this.state) {
            case GenericParserState.LOOKING_FOR_START1:
                if (byte === startBytes[0]) {
                    this.buffer = [byte];
                    if (startBytes.length > 1) {
                        this.state = GenericParserState.LOOKING_FOR_START2;
                    } else {
                        this.state = GenericParserState.GETTING_MSG_ID;
                    }
                }
                break;

            case GenericParserState.LOOKING_FOR_START2:
                if (byte === startBytes[1]) {
                    this.buffer.push(byte);
                    this.state = GenericParserState.GETTING_MSG_ID;
                } else if (byte === startBytes[0]) {
                    this.buffer = [byte];
                    // Stay in LOOKING_FOR_START2
                } else {
                    this.state = GenericParserState.LOOKING_FOR_START1;
                }
                break;

            case GenericParserState.GETTING_MSG_ID:
                this.buffer.push(byte);
                this.msg_id = byte;
                if (this.config.hasLength) {
                    this.state = GenericParserState.GETTING_LENGTH;
                } else if (this.get_msg_length) {
                    const msgLen = this.get_msg_length(byte);
                    if (msgLen !== undefined) {
                        this.packet_size = overhead + msgLen;
                        this.state = GenericParserState.GETTING_PAYLOAD;
                    } else {
                        this.state = this.getInitialState();
                    }
                } else {
                    this.state = this.getInitialState();
                }
                break;

            case GenericParserState.GETTING_LENGTH:
                this.buffer.push(byte);
                if (this.config.lengthBytes === 1) {
                    this.msg_length = byte;
                    this.packet_size = overhead + this.msg_length;
                    this.state = GenericParserState.GETTING_PAYLOAD;
                } else {
                    // 2-byte length
                    if (this.buffer.length === startBytes.length + 2) {
                        this.length_lo = byte;
                    } else {
                        this.msg_length = this.length_lo | (byte << 8);
                        this.packet_size = overhead + this.msg_length;
                        this.state = GenericParserState.GETTING_PAYLOAD;
                    }
                }
                break;

            case GenericParserState.GETTING_PAYLOAD:
                this.buffer.push(byte);
                if (this.buffer.length >= this.packet_size) {
                    if (this.config.hasCrc) {
                        const validationResult = validatePayloadWithCrc(
                            this.buffer, this.config.headerSize, this.config.lengthBytes, startBytes.length);
                        if (validationResult.valid) {
                            result.valid = validationResult.valid;
                            result.msg_id = validationResult.msg_id;
                            result.msg_len = validationResult.msg_len;
                            result.msg_data = validationResult.msg_data;
                        }
                    } else {
                        const validationResult = validatePayloadMinimal(this.buffer, this.config.headerSize);
                        result.valid = validationResult.valid;
                        result.msg_id = validationResult.msg_id;
                        result.msg_len = validationResult.msg_len;
                        result.msg_data = validationResult.msg_data;
                    }
                    this.state = this.getInitialState();
                }
                break;
        }

        return result;
    }

    /**
     * Encode a message using this format
     */
    static encode(config: FrameParserConfig, msg_id: number, msg: Uint8Array | number[]): Uint8Array {
        const output: number[] = [];

        // Add start bytes
        for (const startByte of config.startBytes) {
            output.push(startByte);
        }

        // Use appropriate payload encoding
        if (config.hasCrc) {
            encodePayloadWithCrc(output, msg_id, msg, config.lengthBytes, config.startBytes.length);
        } else {
            encodePayloadMinimal(output, msg_id, msg);
        }

        return new Uint8Array(output);
    }

    /**
     * Validate a complete packet buffer using this format
     */
    static validate_packet(config: FrameParserConfig, buffer: Uint8Array | number[]): FrameMsgInfo {
        const overhead = config.headerSize + config.footerSize;

        if (buffer.length < overhead) {
            return createFrameMsgInfo();
        }

        // Check start bytes
        for (let i = 0; i < config.startBytes.length; i++) {
            if (buffer[i] !== config.startBytes[i]) {
                return createFrameMsgInfo();
            }
        }

        // Validate payload
        if (config.hasCrc) {
            return validatePayloadWithCrc(buffer, config.headerSize, config.lengthBytes, config.startBytes.length);
        } else {
            return validatePayloadMinimal(buffer, config.headerSize);
        }
    }
}

/**
 * Create a typed frame parser class for a specific configuration.
 * This factory function provides type-safe wrappers around GenericFrameParser.
 */
export function createFrameParserClass(config: FrameParserConfig) {
    return class extends GenericFrameParser {
        // Static properties from config
        static readonly START_BYTES = config.startBytes;
        static readonly HEADER_SIZE = config.headerSize;
        static readonly FOOTER_SIZE = config.footerSize;
        static readonly OVERHEAD = config.headerSize + config.footerSize;
        static readonly HAS_LENGTH = config.hasLength;
        static readonly LENGTH_BYTES = config.lengthBytes;
        static readonly HAS_CRC = config.hasCrc;
        static readonly CONFIG = config;

        constructor(get_msg_length?: (msg_id: number) => number | undefined) {
            super(config, get_msg_length);
        }

        static encodeMsg(msg_id: number, msg: Uint8Array | number[]): Uint8Array {
            return GenericFrameParser.encode(config, msg_id, msg);
        }

        static validatePacket(buffer: Uint8Array | number[]): FrameMsgInfo {
            return GenericFrameParser.validate_packet(config, buffer);
        }
    };
}
