/**
 * Base class and utilities for struct-frame generated message classes.
 * 
 * This module provides a lightweight base class that generated message classes
 * extend. The generated code handles field access directly for better performance.
 */
"use strict";

/**
 * Base class for all generated message types.
 * Provides common buffer management and utility methods.
 * 
 * Generated classes extend this and add typed field accessors
 * that read/write directly to the buffer at known offsets.
 */
class MessageBase {
  /**
   * Create a new message instance.
   * @param {Buffer|Object} [bufferOrInit] - Optional buffer to wrap, or an init object with field values.
   *                                         If not provided, allocates a new zero-filled buffer.
   */
  constructor(bufferOrInit) {
    const size = this.constructor._size;
    if (Buffer.isBuffer(bufferOrInit)) {
      this._buffer = Buffer.from(bufferOrInit);
    } else {
      this._buffer = Buffer.alloc(size);
      // If init object provided, it will be applied by generated constructors
    }
  }

  /**
   * Apply initialization values from an object.
   * Called by generated constructors after super() when init object is provided.
   * @param {Object} init - Object with field values to apply
   */
  _applyInit(init) {
    for (const [key, value] of Object.entries(init)) {
      if (value !== undefined && key in this) {
        this[key] = value;
      }
    }
  }

  /**
   * Get the size of this message in bytes.
   */
  getSize() {
    return this.constructor._size;
  }

  /**
   * Get the message ID for this message type.
   * @returns {number|undefined} The message ID, or undefined if not defined
   */
  getMsgId() {
    return this.constructor._msgid;
  }

  /**
   * Get the magic1 checksum value for this message type.
   * @returns {number} The magic1 value, or 0 if not defined
   */
  getMagic1() {
    return this.constructor._magic1 ?? 0;
  }

  /**
   * Get the magic2 checksum value for this message type.
   * @returns {number} The magic2 value, or 0 if not defined
   */
  getMagic2() {
    return this.constructor._magic2 ?? 0;
  }

  /**
   * Get the raw buffer containing the message data.
   * @param {MessageBase} instance - The message instance
   * @returns {Buffer} The raw buffer
   */
  static raw(instance) {
    return instance._buffer;
  }

  // =========================================================================
  // Helper methods for reading fields from the buffer.
  // These are called by generated getter methods.
  // =========================================================================

  _readInt8(offset) {
    return this._buffer.readInt8(offset);
  }

  _readUInt8(offset) {
    return this._buffer.readUInt8(offset);
  }

  _readInt16LE(offset) {
    return this._buffer.readInt16LE(offset);
  }

  _readUInt16LE(offset) {
    return this._buffer.readUInt16LE(offset);
  }

  _readInt32LE(offset) {
    return this._buffer.readInt32LE(offset);
  }

  _readUInt32LE(offset) {
    return this._buffer.readUInt32LE(offset);
  }

  _readBigInt64LE(offset) {
    return this._buffer.readBigInt64LE(offset);
  }

  _readBigUInt64LE(offset) {
    return this._buffer.readBigUInt64LE(offset);
  }

  _readFloat32LE(offset) {
    return this._buffer.readFloatLE(offset);
  }

  _readFloat64LE(offset) {
    return this._buffer.readDoubleLE(offset);
  }

  _readBoolean8(offset) {
    return this._buffer.readUInt8(offset) !== 0;
  }

  _readString(offset, size) {
    const strBytes = this._buffer.subarray(offset, offset + size);
    const nullIndex = strBytes.indexOf(0);
    if (nullIndex >= 0) {
      return strBytes.subarray(0, nullIndex).toString('utf8');
    }
    return strBytes.toString('utf8');
  }

  _readInt8Array(offset, length) {
    const result = [];
    for (let i = 0; i < length; i++) {
      result.push(this._buffer.readInt8(offset + i));
    }
    return result;
  }

  _readUInt8Array(offset, length) {
    const result = [];
    for (let i = 0; i < length; i++) {
      result.push(this._buffer.readUInt8(offset + i));
    }
    return result;
  }

  _readInt16Array(offset, length) {
    const result = [];
    for (let i = 0; i < length; i++) {
      result.push(this._buffer.readInt16LE(offset + i * 2));
    }
    return result;
  }

  _readUInt16Array(offset, length) {
    const result = [];
    for (let i = 0; i < length; i++) {
      result.push(this._buffer.readUInt16LE(offset + i * 2));
    }
    return result;
  }

  _readInt32Array(offset, length) {
    const result = [];
    for (let i = 0; i < length; i++) {
      result.push(this._buffer.readInt32LE(offset + i * 4));
    }
    return result;
  }

  _readUInt32Array(offset, length) {
    const result = [];
    for (let i = 0; i < length; i++) {
      result.push(this._buffer.readUInt32LE(offset + i * 4));
    }
    return result;
  }

  _readBigInt64Array(offset, length) {
    const result = [];
    for (let i = 0; i < length; i++) {
      result.push(this._buffer.readBigInt64LE(offset + i * 8));
    }
    return result;
  }

  _readBigUInt64Array(offset, length) {
    const result = [];
    for (let i = 0; i < length; i++) {
      result.push(this._buffer.readBigUInt64LE(offset + i * 8));
    }
    return result;
  }

  _readFloat32Array(offset, length) {
    const result = [];
    for (let i = 0; i < length; i++) {
      result.push(this._buffer.readFloatLE(offset + i * 4));
    }
    return result;
  }

  _readFloat64Array(offset, length) {
    const result = [];
    for (let i = 0; i < length; i++) {
      result.push(this._buffer.readDoubleLE(offset + i * 8));
    }
    return result;
  }

  _readStructArray(offset, length, ctor) {
    const result = [];
    const elemSize = ctor._size;
    for (let i = 0; i < length; i++) {
      const elemOffset = offset + i * elemSize;
      const elemBuffer = this._buffer.subarray(elemOffset, elemOffset + elemSize);
      result.push(new ctor(elemBuffer));
    }
    return result;
  }

  // =========================================================================
  // Helper methods for writing fields to the buffer.
  // These are called by generated setter methods.
  // =========================================================================

  _writeInt8(offset, value) {
    this._buffer.writeInt8(value, offset);
  }

  _writeUInt8(offset, value) {
    this._buffer.writeUInt8(value, offset);
  }

  _writeInt16LE(offset, value) {
    this._buffer.writeInt16LE(value, offset);
  }

  _writeUInt16LE(offset, value) {
    this._buffer.writeUInt16LE(value, offset);
  }

  _writeInt32LE(offset, value) {
    this._buffer.writeInt32LE(value, offset);
  }

  _writeUInt32LE(offset, value) {
    this._buffer.writeUInt32LE(value, offset);
  }

  _writeBigInt64LE(offset, value) {
    this._buffer.writeBigInt64LE(BigInt(value), offset);
  }

  _writeBigUInt64LE(offset, value) {
    this._buffer.writeBigUInt64LE(BigInt(value), offset);
  }

  _writeFloat32LE(offset, value) {
    this._buffer.writeFloatLE(value, offset);
  }

  _writeFloat64LE(offset, value) {
    this._buffer.writeDoubleLE(value, offset);
  }

  _writeBoolean8(offset, value) {
    this._buffer.writeUInt8(value ? 1 : 0, offset);
  }

  _writeString(offset, size, value) {
    this._buffer.fill(0, offset, offset + size);
    const strValue = String(value || '');
    const strBuffer = Buffer.from(strValue, 'utf8');
    strBuffer.copy(this._buffer, offset, 0, Math.min(strBuffer.length, size));
  }

  _writeInt8Array(offset, length, value) {
    const arr = value || [];
    for (let i = 0; i < length; i++) {
      this._buffer.writeInt8(i < arr.length ? arr[i] : 0, offset + i);
    }
  }

  _writeUInt8Array(offset, length, value) {
    const arr = value || [];
    for (let i = 0; i < length; i++) {
      this._buffer.writeUInt8(i < arr.length ? arr[i] : 0, offset + i);
    }
  }

  _writeInt16Array(offset, length, value) {
    const arr = value || [];
    for (let i = 0; i < length; i++) {
      this._buffer.writeInt16LE(i < arr.length ? arr[i] : 0, offset + i * 2);
    }
  }

  _writeUInt16Array(offset, length, value) {
    const arr = value || [];
    for (let i = 0; i < length; i++) {
      this._buffer.writeUInt16LE(i < arr.length ? arr[i] : 0, offset + i * 2);
    }
  }

  _writeInt32Array(offset, length, value) {
    const arr = value || [];
    for (let i = 0; i < length; i++) {
      this._buffer.writeInt32LE(i < arr.length ? arr[i] : 0, offset + i * 4);
    }
  }

  _writeUInt32Array(offset, length, value) {
    const arr = value || [];
    for (let i = 0; i < length; i++) {
      this._buffer.writeUInt32LE(i < arr.length ? arr[i] : 0, offset + i * 4);
    }
  }

  _writeBigInt64Array(offset, length, value) {
    const arr = value || [];
    for (let i = 0; i < length; i++) {
      this._buffer.writeBigInt64LE(i < arr.length ? BigInt(arr[i]) : 0n, offset + i * 8);
    }
  }

  _writeBigUInt64Array(offset, length, value) {
    const arr = value || [];
    for (let i = 0; i < length; i++) {
      this._buffer.writeBigUInt64LE(i < arr.length ? BigInt(arr[i]) : 0n, offset + i * 8);
    }
  }

  _writeFloat32Array(offset, length, value) {
    const arr = value || [];
    for (let i = 0; i < length; i++) {
      this._buffer.writeFloatLE(i < arr.length ? arr[i] : 0, offset + i * 4);
    }
  }

  _writeFloat64Array(offset, length, value) {
    const arr = value || [];
    for (let i = 0; i < length; i++) {
      this._buffer.writeDoubleLE(i < arr.length ? arr[i] : 0, offset + i * 8);
    }
  }

  _writeStructArray(offset, length, elemSize, value, ctor) {
    const arr = value || [];
    for (let i = 0; i < length; i++) {
      const elemOffset = offset + i * elemSize;
      if (i < arr.length && arr[i]) {
        const element = arr[i];
        let srcBuffer;
        if (element instanceof MessageBase) {
          srcBuffer = element._buffer;
        } else if (typeof element === 'object' && element !== null) {
          const tempStruct = new ctor();
          for (const key of Object.keys(element)) {
            tempStruct[key] = element[key];
          }
          srcBuffer = tempStruct._buffer;
        } else {
          this._buffer.fill(0, elemOffset, elemOffset + elemSize);
          continue;
        }
        srcBuffer.copy(this._buffer, elemOffset, 0, elemSize);
      } else {
        this._buffer.fill(0, elemOffset, elemOffset + elemSize);
      }
    }
  }
}

module.exports.MessageBase = MessageBase;
