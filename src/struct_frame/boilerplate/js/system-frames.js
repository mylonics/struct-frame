"use strict";
/**
 * System frames: struct-frame's own messages (heartbeat, ping, link tests, RPC).
 *
 * A system frame uses the header of the profile it travels with (Basic or Tiny; profiles
 * without start bytes cannot carry system frames) followed by a fixed payload layout:
 *
 *     [start bytes][SEQ][SYS][COMP][LEN lo][LEN hi][SYS_MSG_ID] payload [CRC1][CRC2]
 *
 * The second start byte (Basic) or the start byte (Tiny) is 0x79: payload type 9. System
 * message ids are a separate id space (see sf-system.structframe.ts), so they never collide
 * with application messages. The CRC is the usual Fletcher-16 over everything after the
 * start bytes, with the system message's magic bytes mixed in after the data.
 *
 * Some system messages carry a raw *tail* after their fixed fields (ping padding, link-test
 * data, RPC payloads); its length is the frame length minus the message's fixed size.
 *
 * The frame readers in frame-profiles.ts use this module to tell system frames apart; this
 * module only imports types from frame-profiles, so there is no runtime import cycle.
 */
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.TAIL_MESSAGES = exports.MAX_TAIL = exports.SYSTEM_START_BYTE = exports.SYSTEM_PAYLOAD_TYPE_VALUE = void 0;
exports.supportsSystemFrames = supportsSystemFrames;
exports.systemProfileConfig = systemProfileConfig;
exports.systemMessageInfo = systemMessageInfo;
exports.systemMessageClass = systemMessageClass;
exports.encodeSystemMessage = encodeSystemMessage;
exports.decodeSystemMessage = decodeSystemMessage;
const frame_headers_1 = require("./frame-headers");
const payload_types_1 = require("./payload-types");
const frame_base_1 = require("./frame-base");
const sf = __importStar(require("./sf-system.structframe"));
/** Payload type of system frames. */
exports.SYSTEM_PAYLOAD_TYPE_VALUE = payload_types_1.PayloadType.SYSTEM;
/** Start byte of system frames (second byte after a Basic header, the only byte of a Tiny one). */
exports.SYSTEM_START_BYTE = frame_headers_1.PAYLOAD_TYPE_BASE + payload_types_1.PayloadType.SYSTEM;
/** Largest tail accepted after a system message's fixed fields. */
exports.MAX_TAIL = sf.MAX_TAIL;
const CLASSES = [
    sf.Heartbeat, sf.LinkStats, sf.Ping, sf.Pong, sf.LinkTestStart, sf.LinkTestAck,
    sf.LinkTestData, sf.LinkTestStop, sf.LinkTestReport, sf.RpcRequest, sf.RpcResponse,
];
/** System message ids that may carry a tail. */
exports.TAIL_MESSAGES = new Set([
    sf.Ping._msgid, sf.Pong._msgid, sf.LinkTestData._msgid, sf.RpcRequest._msgid, sf.RpcResponse._msgid,
]);
const MESSAGES = new Map(CLASSES.map((cls) => [cls._msgid, cls]));
const INFOS = new Map(CLASSES.map((cls) => {
    const largest = cls._size + (exports.TAIL_MESSAGES.has(cls._msgid) ? exports.MAX_TAIL : 0);
    // baseSize === size so the CRC is never extension-split.
    const info = {
        size: largest, minSize: cls._size, isVariable: largest !== cls._size,
        magic1: cls._magic1, magic2: cls._magic2, baseSize: largest,
    };
    return [cls._msgid, info];
}));
/**
 * True when frames of `config` can be told apart from system frames: the header carries
 * the payload type in a start byte (Basic and Tiny headers).
 */
function supportsSystemFrames(config) {
    return config.header.encodesPayloadType && config.header.numStartBytes >= 1;
}
const SYSTEM_CONFIGS = new Map();
/** The system-frame profile for the header of `config`. */
function systemProfileConfig(config) {
    if (!supportsSystemFrames(config)) {
        throw new Error(`profile ${config.name} has no start byte that identifies the payload ` +
            `type, so it cannot carry system frames`);
    }
    let cached = SYSTEM_CONFIGS.get(config.header);
    if (cached === undefined) {
        const header = config.header;
        cached = {
            name: `${header.headerType === frame_headers_1.HeaderType.TINY ? 'Tiny' : 'Basic'}System`,
            header,
            payload: payload_types_1.PAYLOAD_SYSTEM_CONFIG,
            startByte1: header.numStartBytes === 1 ? exports.SYSTEM_START_BYTE : header.startByte1,
            startByte2: header.numStartBytes === 2 ? exports.SYSTEM_START_BYTE : header.startByte2,
        };
        SYSTEM_CONFIGS.set(config.header, cached);
    }
    return cached;
}
/**
 * Size limits and magic bytes of a system message, for the frame readers.
 * `minSize` is the fixed size; `size` also allows a tail for the messages that take one.
 */
function systemMessageInfo(msgId) {
    return INFOS.get(msgId);
}
/** The generated class of a system message id, or undefined. */
function systemMessageClass(msgId) {
    return MESSAGES.get(msgId);
}
/** Encode a system message (and its tail) as a system frame for the header of `config`. */
function encodeSystemMessage(config, message, options = {}) {
    const cfg = systemProfileConfig(config);
    const cls = message.constructor;
    if (MESSAGES.get(cls._msgid) !== cls) {
        throw new Error(`${cls.name} is not a system message`);
    }
    const tail = options.tail ?? new Uint8Array(0);
    if (tail.length > 0 && !exports.TAIL_MESSAGES.has(cls._msgid)) {
        throw new Error(`${cls.name} does not take a tail`);
    }
    if (tail.length > exports.MAX_TAIL) {
        throw new RangeError(`tail of ${tail.length} bytes exceeds MAX_TAIL (${exports.MAX_TAIL})`);
    }
    const fixed = message.serialize?.() ?? message._buffer;
    const payloadLen = fixed.length + tail.length;
    const starts = cfg.header.numStartBytes;
    const out = new Uint8Array(starts + 6 + payloadLen + 2);
    let idx = 0;
    if (starts >= 1)
        out[idx++] = cfg.startByte1;
    if (starts >= 2)
        out[idx++] = cfg.startByte2;
    const crcStart = idx;
    out[idx++] = (options.seq ?? 0) & 0xFF;
    out[idx++] = (options.sysId ?? 0) & 0xFF;
    out[idx++] = (options.compId ?? 0) & 0xFF;
    out[idx++] = payloadLen & 0xFF;
    out[idx++] = (payloadLen >> 8) & 0xFF;
    out[idx++] = cls._msgid & 0xFF;
    out.set(fixed, idx);
    idx += fixed.length;
    out.set(tail, idx);
    idx += tail.length;
    const ck = (0, frame_base_1.fletcherChecksum)(out, crcStart, idx, cls._magic1, cls._magic2);
    out[idx++] = ck[0];
    out[idx++] = ck[1];
    return out;
}
/** The message and tail of a valid system frame returned by a reader (`frame.isSystem`). */
function decodeSystemMessage(frame) {
    const cls = MESSAGES.get(frame.msgId);
    if (cls === undefined) {
        throw new Error(`unknown system message id 0x${frame.msgId.toString(16).padStart(2, '0').toUpperCase()}`);
    }
    const data = frame.msgData.subarray(0, frame.msgLen);
    return {
        message: cls.deserialize(data.slice(0, cls._size), 'fixed'),
        tail: data.slice(cls._size),
    };
}
