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

import { HeaderConfig, HeaderType, PAYLOAD_TYPE_BASE } from './frame-headers';
import { PAYLOAD_SYSTEM_CONFIG, PayloadType } from './payload-types';
import { fletcherChecksum, FrameMsgInfo } from './frame-base';
import type { FrameProfileConfig, MessageInfo } from './frame-profiles';
import { MessageBase } from './struct-base';
import * as sf from './sf-system.structframe';

/** Payload type of system frames. */
export const SYSTEM_PAYLOAD_TYPE_VALUE = PayloadType.SYSTEM;
/** Start byte of system frames (second byte after a Basic header, the only byte of a Tiny one). */
export const SYSTEM_START_BYTE = PAYLOAD_TYPE_BASE + PayloadType.SYSTEM;
/** Largest tail accepted after a system message's fixed fields. */
export const MAX_TAIL = sf.MAX_TAIL;

/** Union of the generated system message classes. */
export type SystemMessage =
    sf.Heartbeat | sf.LinkStats | sf.Ping | sf.Pong | sf.LinkTestStart | sf.LinkTestAck |
    sf.LinkTestData | sf.LinkTestStop | sf.LinkTestReport | sf.RpcRequest | sf.RpcResponse;

interface SystemMessageClass {
    readonly _msgid: number;
    readonly _size: number;
    readonly _magic1: number;
    readonly _magic2: number;
    readonly name: string;
    deserialize(buffer: Uint8Array, mode?: 'wire' | 'fixed' | 'auto'): SystemMessage;
}

const CLASSES: readonly SystemMessageClass[] = [
    sf.Heartbeat, sf.LinkStats, sf.Ping, sf.Pong, sf.LinkTestStart, sf.LinkTestAck,
    sf.LinkTestData, sf.LinkTestStop, sf.LinkTestReport, sf.RpcRequest, sf.RpcResponse,
] as unknown as readonly SystemMessageClass[];

/** System message ids that may carry a tail. */
export const TAIL_MESSAGES: ReadonlySet<number> = new Set<number>([
    sf.Ping._msgid, sf.Pong._msgid, sf.LinkTestData._msgid, sf.RpcRequest._msgid, sf.RpcResponse._msgid,
]);

const MESSAGES = new Map<number, SystemMessageClass>(CLASSES.map((cls) => [cls._msgid, cls]));

const INFOS = new Map<number, MessageInfo>(CLASSES.map((cls) => {
    const largest = cls._size + (TAIL_MESSAGES.has(cls._msgid) ? MAX_TAIL : 0);
    // baseSize === size so the CRC is never extension-split.
    const info: MessageInfo = {
        size: largest, minSize: cls._size, isVariable: largest !== cls._size,
        magic1: cls._magic1, magic2: cls._magic2, baseSize: largest,
    };
    return [cls._msgid, info];
}));

/**
 * True when frames of `config` can be told apart from system frames: the header carries
 * the payload type in a start byte (Basic and Tiny headers).
 */
export function supportsSystemFrames(config: FrameProfileConfig): boolean {
    return config.header.encodesPayloadType && config.header.numStartBytes >= 1;
}

const SYSTEM_CONFIGS = new Map<HeaderConfig, FrameProfileConfig>();

/** The system-frame profile for the header of `config`. */
export function systemProfileConfig(config: FrameProfileConfig): FrameProfileConfig {
    if (!supportsSystemFrames(config)) {
        throw new Error(`profile ${config.name} has no start byte that identifies the payload ` +
            `type, so it cannot carry system frames`);
    }
    let cached = SYSTEM_CONFIGS.get(config.header);
    if (cached === undefined) {
        const header = config.header;
        cached = {
            name: `${header.headerType === HeaderType.TINY ? 'Tiny' : 'Basic'}System`,
            header,
            payload: PAYLOAD_SYSTEM_CONFIG,
            startByte1: header.numStartBytes === 1 ? SYSTEM_START_BYTE : header.startByte1,
            startByte2: header.numStartBytes === 2 ? SYSTEM_START_BYTE : header.startByte2,
        };
        SYSTEM_CONFIGS.set(config.header, cached);
    }
    return cached;
}

/**
 * Size limits and magic bytes of a system message, for the frame readers.
 * `minSize` is the fixed size; `size` also allows a tail for the messages that take one.
 */
export function systemMessageInfo(msgId: number): MessageInfo | undefined {
    return INFOS.get(msgId);
}

/** The generated class of a system message id, or undefined. */
export function systemMessageClass(msgId: number): SystemMessageClass | undefined {
    return MESSAGES.get(msgId);
}

export interface SystemEncodeOptions {
    /** Raw bytes after the fixed fields (Ping, Pong, LinkTestData, RpcRequest, RpcResponse only). */
    tail?: Uint8Array;
    seq?: number;
    sysId?: number;
    compId?: number;
}

/** Encode a system message (and its tail) as a system frame for the header of `config`. */
export function encodeSystemMessage(
    config: FrameProfileConfig,
    message: MessageBase,
    options: SystemEncodeOptions = {}
): Uint8Array {
    const cfg = systemProfileConfig(config);
    const cls = message.constructor as unknown as SystemMessageClass;
    if (MESSAGES.get(cls._msgid) !== cls) {
        throw new Error(`${cls.name} is not a system message`);
    }
    const tail = options.tail ?? new Uint8Array(0);
    if (tail.length > 0 && !TAIL_MESSAGES.has(cls._msgid)) {
        throw new Error(`${cls.name} does not take a tail`);
    }
    if (tail.length > MAX_TAIL) {
        throw new RangeError(`tail of ${tail.length} bytes exceeds MAX_TAIL (${MAX_TAIL})`);
    }
    const fixed: Uint8Array = message.serialize?.() ?? message._buffer;
    const payloadLen = fixed.length + tail.length;
    const starts = cfg.header.numStartBytes;
    const out = new Uint8Array(starts + 6 + payloadLen + 2);
    let idx = 0;
    if (starts >= 1) out[idx++] = cfg.startByte1;
    if (starts >= 2) out[idx++] = cfg.startByte2;
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
    const ck = fletcherChecksum(out, crcStart, idx, cls._magic1, cls._magic2);
    out[idx++] = ck[0];
    out[idx++] = ck[1];
    return out;
}

/** The message and tail of a valid system frame returned by a reader (`frame.isSystem`). */
export function decodeSystemMessage(frame: FrameMsgInfo): { message: SystemMessage; tail: Uint8Array } {
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
