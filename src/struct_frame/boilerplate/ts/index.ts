// Struct-frame boilerplate: frame parser package

// Struct base class for message types
export { MessageBase } from './struct_base';
export type { MessageConstructor } from './struct_base';

// Base utilities and generic parser infrastructure
export type { FrameMsgInfo, FrameParserConfig } from './frame_base';
export {
    FrameFormatType,
    createFrameMsgInfo,
    fletcher_checksum,
    // Generic parser class (use createFrameParserClass for type-safe wrappers)
    GenericFrameParser,
    GenericParserState,
    createFrameParserClass,
    // Shared payload parsing functions
    validate_payload_with_crc,
    validate_payload_minimal,
    encode_payload_with_crc,
    encode_payload_minimal,
} from './frame_base';

// Frame headers - Start byte patterns and header types
export type { HeaderConfig } from './frame_headers';
export {
    HeaderType,
    BASIC_START_BYTE,
    PAYLOAD_TYPE_BASE,
    UBX_SYNC1,
    UBX_SYNC2,
    MAVLINK_V1_STX,
    MAVLINK_V2_STX,
    MAX_PAYLOAD_TYPE,
    HEADER_NONE_CONFIG,
    HEADER_TINY_CONFIG,
    HEADER_BASIC_CONFIG,
    HEADER_UBX_CONFIG,
    HEADER_MAVLINK_V1_CONFIG,
    HEADER_MAVLINK_V2_CONFIG,
} from './frame_headers';

// Payload types - Message structure definitions
export type { PayloadConfig } from './payload_types';
export {
    PayloadType,
    MAX_PAYLOAD_TYPE_VALUE,
    payloadHeaderSize,
    payloadFooterSize,
    payloadOverhead,
    payloadMaxPayload,
    PAYLOAD_MINIMAL_CONFIG,
    PAYLOAD_DEFAULT_CONFIG,
    PAYLOAD_EXTENDED_MSG_IDS_CONFIG,
    PAYLOAD_EXTENDED_LENGTH_CONFIG,
    PAYLOAD_EXTENDED_CONFIG,
    PAYLOAD_SYS_COMP_CONFIG,
    PAYLOAD_SEQ_CONFIG,
    PAYLOAD_MULTI_SYSTEM_STREAM_CONFIG,
    PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM_CONFIG,
} from './payload_types';

// Frame profiles - Pre-defined Header + Payload combinations
export type { FrameProfileConfig, EncodeOptions } from './frame_profiles';
export {
    // Profile helper functions
    profileHeaderSize,
    profileFooterSize,
    profileOverhead,
    // Profile configurations
    ProfileStandardConfig,
    ProfileSensorConfig,
    ProfileIPCConfig,
    ProfileBulkConfig,
    ProfileNetworkConfig,
    // Generic encode/parse functions
    encodeFrameWithCrc,
    encodeFrameMinimal,
    parseFrameWithCrc,
    parseFrameMinimal,
    // BufferReader/BufferWriter/AccumulatingReader base classes
    BufferReader,
    BufferWriter,
    AccumulatingReader,
    AccumulatingReaderState,
    // Profile-specific subclasses
    ProfileStandardReader,
    ProfileStandardWriter,
    ProfileStandardAccumulatingReader,
    ProfileSensorReader,
    ProfileSensorWriter,
    ProfileSensorAccumulatingReader,
    ProfileIPCReader,
    ProfileIPCWriter,
    ProfileIPCAccumulatingReader,
    ProfileBulkReader,
    ProfileBulkWriter,
    ProfileBulkAccumulatingReader,
    ProfileNetworkReader,
    ProfileNetworkWriter,
    ProfileNetworkAccumulatingReader,
} from './frame_profiles';

