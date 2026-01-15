/**
 * Base class and utilities for struct-frame generated message classes.
 * 
 * This module provides a lightweight base class that generated message classes
 * extend. The generated code handles field access directly for better performance
 * and type safety.
 */

/**
 * Interface for message class constructors.
 * Used for nested message types and StructArray fields.
 */
export interface MessageConstructor<T extends MessageBase = MessageBase> {
  new(bufferOrInit?: Buffer | Record<string, unknown>): T;
  readonly _size: number;
  readonly _msgid?: number;
  readonly _magic1?: number;
  readonly _magic2?: number;
  getSize(): number;
  unpack?(buffer: Buffer): T;
}

/**
 * Base class for all generated message types.
 * Provides common buffer management and utility methods.
 * 
 * Generated classes extend this and add typed field accessors
 * that read/write directly to the buffer at compile-time known offsets.
 */
export abstract class MessageBase {
  /** Internal buffer storing the binary data */
  readonly _buffer: Buffer;

  /**
   * Create a new message instance.
   * @param bufferOrInit Optional buffer to wrap, or an init object with field values.
   *                     If not provided, allocates a new zero-filled buffer.
   */
  constructor(bufferOrInit?: Buffer | Record<string, unknown>) {
    const size = (this.constructor as MessageConstructor)._size;
    if (Buffer.isBuffer(bufferOrInit)) {
      this._buffer = Buffer.from(bufferOrInit);
    } else {
      this._buffer = Buffer.alloc(size);
      // If init object provided, apply values after subclass constructor runs
      // This is handled by generated constructors calling _applyInit()
    }
  }

  /**
   * Apply initialization values from an object.
   * Called by generated constructors after super() when init object is provided.
   */
  protected _applyInit(init: Record<string, unknown>): void {
    for (const [key, value] of Object.entries(init)) {
      if (value !== undefined && key in this) {
        (this as Record<string, unknown>)[key] = value;
      }
    }
  }

  /**
   * Get the size of this message in bytes.
   */
  getSize(): number {
    return (this.constructor as MessageConstructor)._size;
  }

  /**
   * Get the message ID for this message type.
   * Returns undefined if no message ID is defined.
   */
  getMsgId(): number | undefined {
    return (this.constructor as MessageConstructor)._msgid;
  }

  /**
   * Get the magic1 checksum value for this message type.
   * Returns 0 if not defined.
   */
  getMagic1(): number {
    return (this.constructor as MessageConstructor)._magic1 ?? 0;
  }

  /**
   * Get the magic2 checksum value for this message type.
   * Returns 0 if not defined.
   */
  getMagic2(): number {
    return (this.constructor as MessageConstructor)._magic2 ?? 0;
  }

  /**
   * Check if this message uses variable-length encoding.
   * Returns false for non-variable messages.
   * Variable messages override this to return true.
   */
  isVariable?(): boolean;

  /**
   * Serialize the message to a Buffer.
   * For variable messages, returns only the used bytes.
   * For non-variable messages, returns the full buffer.
   * Generated message classes override this method.
   */
  serialize?(): Buffer;

  /**
   * Calculate the packed size for variable messages.
   * Only available on variable messages.
   */
  packSize?(): number;

  /**
   * Pack message using variable-length encoding.
   * Only available on variable messages.
   */
  packVariable?(): Buffer;

  /**
   * Get the raw buffer containing the message data.
   */
  static raw<T extends MessageBase>(instance: T): Buffer {
    return instance._buffer;
  }

  // =========================================================================
  // Helper methods for reading fields from the buffer.
  // These are called by generated getter methods.
  // =========================================================================

  protected _readInt8(offset: number): number {
    return this._buffer.readInt8(offset);
  }

  protected _readUInt8(offset: number): number {
    return this._buffer.readUInt8(offset);
  }

  protected _readInt16LE(offset: number): number {
    return this._buffer.readInt16LE(offset);
  }

  protected _readUInt16LE(offset: number): number {
    return this._buffer.readUInt16LE(offset);
  }

  protected _readInt32LE(offset: number): number {
    return this._buffer.readInt32LE(offset);
  }

  protected _readUInt32LE(offset: number): number {
    return this._buffer.readUInt32LE(offset);
  }

  protected _readBigInt64LE(offset: number): bigint {
    return this._buffer.readBigInt64LE(offset);
  }

  protected _readBigUInt64LE(offset: number): bigint {
    return this._buffer.readBigUInt64LE(offset);
  }

  protected _readFloat32LE(offset: number): number {
    return this._buffer.readFloatLE(offset);
  }

  protected _readFloat64LE(offset: number): number {
    return this._buffer.readDoubleLE(offset);
  }

  protected _readBoolean8(offset: number): boolean {
    return this._buffer.readUInt8(offset) !== 0;
  }

  protected _readString(offset: number, size: number): string {
    const strBytes = this._buffer.subarray(offset, offset + size);
    const nullIndex = strBytes.indexOf(0);
    if (nullIndex >= 0) {
      return strBytes.subarray(0, nullIndex).toString('utf8');
    }
    return strBytes.toString('utf8');
  }

  protected _readInt8Array(offset: number, length: number): number[] {
    const result: number[] = [];
    for (let i = 0; i < length; i++) {
      result.push(this._buffer.readInt8(offset + i));
    }
    return result;
  }

  protected _readUInt8Array(offset: number, length: number): number[] {
    const result: number[] = [];
    for (let i = 0; i < length; i++) {
      result.push(this._buffer.readUInt8(offset + i));
    }
    return result;
  }

  protected _readInt16Array(offset: number, length: number): number[] {
    const result: number[] = [];
    for (let i = 0; i < length; i++) {
      result.push(this._buffer.readInt16LE(offset + i * 2));
    }
    return result;
  }

  protected _readUInt16Array(offset: number, length: number): number[] {
    const result: number[] = [];
    for (let i = 0; i < length; i++) {
      result.push(this._buffer.readUInt16LE(offset + i * 2));
    }
    return result;
  }

  protected _readInt32Array(offset: number, length: number): number[] {
    const result: number[] = [];
    for (let i = 0; i < length; i++) {
      result.push(this._buffer.readInt32LE(offset + i * 4));
    }
    return result;
  }

  protected _readUInt32Array(offset: number, length: number): number[] {
    const result: number[] = [];
    for (let i = 0; i < length; i++) {
      result.push(this._buffer.readUInt32LE(offset + i * 4));
    }
    return result;
  }

  protected _readBigInt64Array(offset: number, length: number): bigint[] {
    const result: bigint[] = [];
    for (let i = 0; i < length; i++) {
      result.push(this._buffer.readBigInt64LE(offset + i * 8));
    }
    return result;
  }

  protected _readBigUInt64Array(offset: number, length: number): bigint[] {
    const result: bigint[] = [];
    for (let i = 0; i < length; i++) {
      result.push(this._buffer.readBigUInt64LE(offset + i * 8));
    }
    return result;
  }

  protected _readFloat32Array(offset: number, length: number): number[] {
    const result: number[] = [];
    for (let i = 0; i < length; i++) {
      result.push(this._buffer.readFloatLE(offset + i * 4));
    }
    return result;
  }

  protected _readFloat64Array(offset: number, length: number): number[] {
    const result: number[] = [];
    for (let i = 0; i < length; i++) {
      result.push(this._buffer.readDoubleLE(offset + i * 8));
    }
    return result;
  }

  protected _readStructArray<T extends MessageBase>(
    offset: number,
    length: number,
    ctor: MessageConstructor<T>
  ): T[] {
    const result: T[] = [];
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

  protected _writeInt8(offset: number, value: number): void {
    this._buffer.writeInt8(value, offset);
  }

  protected _writeUInt8(offset: number, value: number): void {
    this._buffer.writeUInt8(value, offset);
  }

  protected _writeInt16LE(offset: number, value: number): void {
    this._buffer.writeInt16LE(value, offset);
  }

  protected _writeUInt16LE(offset: number, value: number): void {
    this._buffer.writeUInt16LE(value, offset);
  }

  protected _writeInt32LE(offset: number, value: number): void {
    this._buffer.writeInt32LE(value, offset);
  }

  protected _writeUInt32LE(offset: number, value: number): void {
    this._buffer.writeUInt32LE(value, offset);
  }

  protected _writeBigInt64LE(offset: number, value: bigint): void {
    this._buffer.writeBigInt64LE(BigInt(value), offset);
  }

  protected _writeBigUInt64LE(offset: number, value: bigint): void {
    this._buffer.writeBigUInt64LE(BigInt(value), offset);
  }

  protected _writeFloat32LE(offset: number, value: number): void {
    this._buffer.writeFloatLE(value, offset);
  }

  protected _writeFloat64LE(offset: number, value: number): void {
    this._buffer.writeDoubleLE(value, offset);
  }

  protected _writeBoolean8(offset: number, value: boolean): void {
    this._buffer.writeUInt8(value ? 1 : 0, offset);
  }

  protected _writeString(offset: number, size: number, value: string): void {
    this._buffer.fill(0, offset, offset + size);
    const strValue = String(value || '');
    const strBuffer = Buffer.from(strValue, 'utf8');
    strBuffer.copy(this._buffer, offset, 0, Math.min(strBuffer.length, size));
  }

  protected _writeInt8Array(offset: number, length: number, value: number[]): void {
    const arr = value || [];
    for (let i = 0; i < length; i++) {
      this._buffer.writeInt8(i < arr.length ? arr[i] : 0, offset + i);
    }
  }

  protected _writeUInt8Array(offset: number, length: number, value: number[]): void {
    const arr = value || [];
    for (let i = 0; i < length; i++) {
      this._buffer.writeUInt8(i < arr.length ? arr[i] : 0, offset + i);
    }
  }

  protected _writeInt16Array(offset: number, length: number, value: number[]): void {
    const arr = value || [];
    for (let i = 0; i < length; i++) {
      this._buffer.writeInt16LE(i < arr.length ? arr[i] : 0, offset + i * 2);
    }
  }

  protected _writeUInt16Array(offset: number, length: number, value: number[]): void {
    const arr = value || [];
    for (let i = 0; i < length; i++) {
      this._buffer.writeUInt16LE(i < arr.length ? arr[i] : 0, offset + i * 2);
    }
  }

  protected _writeInt32Array(offset: number, length: number, value: number[]): void {
    const arr = value || [];
    for (let i = 0; i < length; i++) {
      this._buffer.writeInt32LE(i < arr.length ? arr[i] : 0, offset + i * 4);
    }
  }

  protected _writeUInt32Array(offset: number, length: number, value: number[]): void {
    const arr = value || [];
    for (let i = 0; i < length; i++) {
      this._buffer.writeUInt32LE(i < arr.length ? arr[i] : 0, offset + i * 4);
    }
  }

  protected _writeBigInt64Array(offset: number, length: number, value: bigint[]): void {
    const arr = value || [];
    for (let i = 0; i < length; i++) {
      this._buffer.writeBigInt64LE(i < arr.length ? BigInt(arr[i]) : 0n, offset + i * 8);
    }
  }

  protected _writeBigUInt64Array(offset: number, length: number, value: bigint[]): void {
    const arr = value || [];
    for (let i = 0; i < length; i++) {
      this._buffer.writeBigUInt64LE(i < arr.length ? BigInt(arr[i]) : 0n, offset + i * 8);
    }
  }

  protected _writeFloat32Array(offset: number, length: number, value: number[]): void {
    const arr = value || [];
    for (let i = 0; i < length; i++) {
      this._buffer.writeFloatLE(i < arr.length ? arr[i] : 0, offset + i * 4);
    }
  }

  protected _writeFloat64Array(offset: number, length: number, value: number[]): void {
    const arr = value || [];
    for (let i = 0; i < length; i++) {
      this._buffer.writeDoubleLE(i < arr.length ? arr[i] : 0, offset + i * 8);
    }
  }

  protected _writeStructArray<T extends MessageBase>(
    offset: number,
    length: number,
    elemSize: number,
    value: (T | Record<string, unknown>)[],
    ctor: MessageConstructor<T>
  ): void {
    const arr = value || [];
    for (let i = 0; i < length; i++) {
      const elemOffset = offset + i * elemSize;
      if (i < arr.length && arr[i]) {
        const element = arr[i];
        let srcBuffer: Buffer;
        if (element instanceof MessageBase) {
          srcBuffer = element._buffer;
        } else if (typeof element === 'object' && element !== null) {
          const tempStruct = new ctor();
          const elemObj = element as Record<string, unknown>;
          const tempStructObj = tempStruct as unknown as Record<string, unknown>;
          for (const key of Object.keys(elemObj)) {
            tempStructObj[key] = elemObj[key];
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
