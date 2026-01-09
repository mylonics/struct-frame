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
  new (buffer?: Buffer): T;
  readonly _size: number;
  readonly _msgid?: number;
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
   * @param buffer Optional buffer to wrap. If not provided, allocates a new buffer.
   */
  constructor(buffer?: Buffer) {
    const size = (this.constructor as MessageConstructor)._size;
    if (buffer) {
      this._buffer = Buffer.from(buffer);
    } else {
      this._buffer = Buffer.alloc(size);
    }
  }

  /**
   * Get the size of this message in bytes.
   */
  getSize(): number {
    return (this.constructor as MessageConstructor)._size;
  }

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

// =========================================================================
// Legacy Struct class for backwards compatibility.
// This supports the chainable API used by existing generated code.
// New generated code should use class-based approach extending MessageBase.
// =========================================================================

// Field definition types (for legacy Struct class)
type FieldType = 
  | 'Int8' | 'UInt8' | 'Int16LE' | 'UInt16LE' | 'Int32LE' | 'UInt32LE'
  | 'BigInt64LE' | 'BigUInt64LE' | 'Float32LE' | 'Float64LE'
  | 'Boolean8' | 'String';

type ArrayFieldType =
  | 'Int8Array' | 'UInt8Array' | 'Int16Array' | 'UInt16Array'
  | 'Int32Array' | 'UInt32Array' | 'BigInt64Array' | 'BigUInt64Array'
  | 'Float32Array' | 'Float64Array' | 'StructArray';

interface FieldDefinition {
  name: string;
  type: FieldType | ArrayFieldType;
  size: number;
  offset: number;
  arrayLength?: number;
  structType?: CompiledStruct;
}

const FIELD_SIZES: Record<FieldType, number> = {
  'Int8': 1,
  'UInt8': 1,
  'Int16LE': 2,
  'UInt16LE': 2,
  'Int32LE': 4,
  'UInt32LE': 4,
  'BigInt64LE': 8,
  'BigUInt64LE': 8,
  'Float32LE': 4,
  'Float64LE': 8,
  'Boolean8': 1,
  'String': 1
};

const ARRAY_ELEMENT_SIZES: Record<string, number> = {
  'Int8Array': 1,
  'UInt8Array': 1,
  'Int16Array': 2,
  'UInt16Array': 2,
  'Int32Array': 4,
  'UInt32Array': 4,
  'BigInt64Array': 8,
  'BigUInt64Array': 8,
  'Float32Array': 4,
  'Float64Array': 8,
};

// Legacy interface for compiled struct (backwards compatibility)
export interface CompiledStruct {
  new (buffer?: Buffer): StructInstance;
  getSize(): number;
  readonly _size: number;
  readonly _msgid?: number;
}

export interface StructInstance {
  _buffer: Buffer;
  getSize(): number;
}

function isStructInstance(obj: unknown): obj is StructInstance {
  return typeof obj === 'object' && obj !== null && '_buffer' in obj && Buffer.isBuffer((obj as StructInstance)._buffer);
}

/**
 * Legacy Struct class for backwards compatibility with existing generated code.
 * Provides a chainable API for defining binary message structures.
 */
export class Struct {
  private name: string;
  private fields: FieldDefinition[] = [];
  private currentOffset: number = 0;
  private _msgid?: number;

  constructor(name?: string) {
    this.name = name || 'Struct';
  }

  msgId(id: number): Struct {
    this._msgid = id;
    return this;
  }

  // Primitive field methods
  Int8(fieldName: string): Struct {
    this.addField(fieldName, 'Int8', FIELD_SIZES['Int8']);
    return this;
  }

  UInt8(fieldName: string): Struct {
    this.addField(fieldName, 'UInt8', FIELD_SIZES['UInt8']);
    return this;
  }

  Int16LE(fieldName: string): Struct {
    this.addField(fieldName, 'Int16LE', FIELD_SIZES['Int16LE']);
    return this;
  }

  UInt16LE(fieldName: string): Struct {
    this.addField(fieldName, 'UInt16LE', FIELD_SIZES['UInt16LE']);
    return this;
  }

  Int32LE(fieldName: string): Struct {
    this.addField(fieldName, 'Int32LE', FIELD_SIZES['Int32LE']);
    return this;
  }

  UInt32LE(fieldName: string): Struct {
    this.addField(fieldName, 'UInt32LE', FIELD_SIZES['UInt32LE']);
    return this;
  }

  BigInt64LE(fieldName: string): Struct {
    this.addField(fieldName, 'BigInt64LE', FIELD_SIZES['BigInt64LE']);
    return this;
  }

  BigUInt64LE(fieldName: string): Struct {
    this.addField(fieldName, 'BigUInt64LE', FIELD_SIZES['BigUInt64LE']);
    return this;
  }

  Float32LE(fieldName: string): Struct {
    this.addField(fieldName, 'Float32LE', FIELD_SIZES['Float32LE']);
    return this;
  }

  Float64LE(fieldName: string): Struct {
    this.addField(fieldName, 'Float64LE', FIELD_SIZES['Float64LE']);
    return this;
  }

  Boolean8(fieldName: string): Struct {
    this.addField(fieldName, 'Boolean8', FIELD_SIZES['Boolean8']);
    return this;
  }

  String(fieldName: string, length: number = 0): Struct {
    this.addField(fieldName, 'String', length);
    return this;
  }

  // Array field methods
  Int8Array(fieldName: string, length: number): Struct {
    this.addArrayField(fieldName, 'Int8Array', length);
    return this;
  }

  UInt8Array(fieldName: string, length: number): Struct {
    this.addArrayField(fieldName, 'UInt8Array', length);
    return this;
  }

  Int16Array(fieldName: string, length: number): Struct {
    this.addArrayField(fieldName, 'Int16Array', length);
    return this;
  }

  UInt16Array(fieldName: string, length: number): Struct {
    this.addArrayField(fieldName, 'UInt16Array', length);
    return this;
  }

  Int32Array(fieldName: string, length: number): Struct {
    this.addArrayField(fieldName, 'Int32Array', length);
    return this;
  }

  UInt32Array(fieldName: string, length: number): Struct {
    this.addArrayField(fieldName, 'UInt32Array', length);
    return this;
  }

  BigInt64Array(fieldName: string, length: number): Struct {
    this.addArrayField(fieldName, 'BigInt64Array', length);
    return this;
  }

  BigUInt64Array(fieldName: string, length: number): Struct {
    this.addArrayField(fieldName, 'BigUInt64Array', length);
    return this;
  }

  Float32Array(fieldName: string, length: number): Struct {
    this.addArrayField(fieldName, 'Float32Array', length);
    return this;
  }

  Float64Array(fieldName: string, length: number): Struct {
    this.addArrayField(fieldName, 'Float64Array', length);
    return this;
  }

  /**
   * ByteArray is an alias for UInt8Array, used for union data storage.
   */
  ByteArray(fieldName: string, length: number): Struct {
    this.addArrayField(fieldName, 'UInt8Array', length);
    return this;
  }

  StructArray(fieldName: string, length: number, structType: CompiledStruct): Struct {
    const elementSize = structType.getSize();
    this.fields.push({
      name: fieldName,
      type: 'StructArray',
      size: elementSize * length,
      offset: this.currentOffset,
      arrayLength: length,
      structType: structType
    });
    this.currentOffset += elementSize * length;
    return this;
  }

  private addField(fieldName: string, type: FieldType, size: number): void {
    this.fields.push({
      name: fieldName,
      type: type,
      size: size,
      offset: this.currentOffset
    });
    this.currentOffset += size;
  }

  private addArrayField(fieldName: string, type: ArrayFieldType, length: number): void {
    const elementSize = ARRAY_ELEMENT_SIZES[type] || 1;
    this.fields.push({
      name: fieldName,
      type: type,
      size: elementSize * length,
      offset: this.currentOffset,
      arrayLength: length
    });
    this.currentOffset += elementSize * length;
  }

  /**
   * Compile the struct definition into a usable class.
   */
  compile(): CompiledStruct {
    const fields = [...this.fields];
    const totalSize = this.currentOffset;
    const structName = this.name;

    // Create a class that can be instantiated with optional buffer
    const CompiledStructClass = class implements StructInstance {
      // Note: _buffer needs to be public to satisfy the StructInstance interface
      // and allow Struct.raw() to access it
      _buffer: Buffer;
      private static _fields: FieldDefinition[] = fields;
      static readonly _size: number = totalSize;
      private static _structName: string = structName;

      constructor(buffer?: Buffer) {
        if (buffer) {
          this._buffer = Buffer.from(buffer);
        } else {
          this._buffer = Buffer.alloc(totalSize);
        }
        this._defineProperties();
      }

      private _defineProperties(): void {
        for (const field of fields) {
          this._defineFieldProperty(field);
        }
      }

      private _defineFieldProperty(field: FieldDefinition): void {
        const buffer = this._buffer;
        const offset = field.offset;

        Object.defineProperty(this, field.name, {
          get: () => this._readField(field),
          set: (value: any) => this._writeField(field, value),
          enumerable: true,
          configurable: true
        });
      }

      private _readField(field: FieldDefinition): any {
        const buffer = this._buffer;
        const offset = field.offset;

        switch (field.type) {
          case 'Int8':
            return buffer.readInt8(offset);
          case 'UInt8':
            return buffer.readUInt8(offset);
          case 'Int16LE':
            return buffer.readInt16LE(offset);
          case 'UInt16LE':
            return buffer.readUInt16LE(offset);
          case 'Int32LE':
            return buffer.readInt32LE(offset);
          case 'UInt32LE':
            return buffer.readUInt32LE(offset);
          case 'BigInt64LE':
            return buffer.readBigInt64LE(offset);
          case 'BigUInt64LE':
            return buffer.readBigUInt64LE(offset);
          case 'Float32LE':
            return buffer.readFloatLE(offset);
          case 'Float64LE':
            return buffer.readDoubleLE(offset);
          case 'Boolean8':
            return buffer.readUInt8(offset) !== 0;
          case 'String':
            // Read string until null terminator or field size
            const strBytes = buffer.slice(offset, offset + field.size);
            const nullIndex = strBytes.indexOf(0);
            if (nullIndex >= 0) {
              return strBytes.slice(0, nullIndex).toString('utf8');
            }
            return strBytes.toString('utf8');
          case 'Int8Array':
          case 'UInt8Array':
          case 'Int16Array':
          case 'UInt16Array':
          case 'Int32Array':
          case 'UInt32Array':
          case 'BigInt64Array':
          case 'BigUInt64Array':
          case 'Float32Array':
          case 'Float64Array':
            return this._readArrayField(field);
          case 'StructArray':
            return this._readStructArray(field);
          default:
            return undefined;
        }
      }

      private _readArrayField(field: FieldDefinition): any[] {
        const buffer = this._buffer;
        const offset = field.offset;
        const length = field.arrayLength || 0;
        const result: any[] = [];

        for (let i = 0; i < length; i++) {
          const elemOffset = offset + i * (ARRAY_ELEMENT_SIZES[field.type] || 1);
          switch (field.type) {
            case 'Int8Array':
              result.push(buffer.readInt8(elemOffset));
              break;
            case 'UInt8Array':
              result.push(buffer.readUInt8(elemOffset));
              break;
            case 'Int16Array':
              result.push(buffer.readInt16LE(elemOffset));
              break;
            case 'UInt16Array':
              result.push(buffer.readUInt16LE(elemOffset));
              break;
            case 'Int32Array':
              result.push(buffer.readInt32LE(elemOffset));
              break;
            case 'UInt32Array':
              result.push(buffer.readUInt32LE(elemOffset));
              break;
            case 'BigInt64Array':
              result.push(buffer.readBigInt64LE(elemOffset));
              break;
            case 'BigUInt64Array':
              result.push(buffer.readBigUInt64LE(elemOffset));
              break;
            case 'Float32Array':
              result.push(buffer.readFloatLE(elemOffset));
              break;
            case 'Float64Array':
              result.push(buffer.readDoubleLE(elemOffset));
              break;
          }
        }
        return result;
      }

      private _readStructArray(field: FieldDefinition): any[] {
        const buffer = this._buffer;
        const offset = field.offset;
        const length = field.arrayLength || 0;
        const structType = field.structType!;
        const elementSize = structType.getSize();
        const result: any[] = [];

        for (let i = 0; i < length; i++) {
          const elemOffset = offset + i * elementSize;
          const elemBuffer = buffer.slice(elemOffset, elemOffset + elementSize);
          result.push(new structType(elemBuffer));
        }
        return result;
      }

      private _writeField(field: FieldDefinition, value: any): void {
        const buffer = this._buffer;
        const offset = field.offset;

        switch (field.type) {
          case 'Int8':
            buffer.writeInt8(value, offset);
            break;
          case 'UInt8':
            buffer.writeUInt8(value, offset);
            break;
          case 'Int16LE':
            buffer.writeInt16LE(value, offset);
            break;
          case 'UInt16LE':
            buffer.writeUInt16LE(value, offset);
            break;
          case 'Int32LE':
            buffer.writeInt32LE(value, offset);
            break;
          case 'UInt32LE':
            buffer.writeUInt32LE(value, offset);
            break;
          case 'BigInt64LE':
            buffer.writeBigInt64LE(BigInt(value), offset);
            break;
          case 'BigUInt64LE':
            buffer.writeBigUInt64LE(BigInt(value), offset);
            break;
          case 'Float32LE':
            buffer.writeFloatLE(value, offset);
            break;
          case 'Float64LE':
            buffer.writeDoubleLE(value, offset);
            break;
          case 'Boolean8':
            buffer.writeUInt8(value ? 1 : 0, offset);
            break;
          case 'String':
            // Clear the string area first
            buffer.fill(0, offset, offset + field.size);
            // Write string (truncate if too long)
            const strValue = String(value || '');
            const strBuffer = Buffer.from(strValue, 'utf8');
            strBuffer.copy(buffer, offset, 0, Math.min(strBuffer.length, field.size));
            break;
          case 'Int8Array':
          case 'UInt8Array':
          case 'Int16Array':
          case 'UInt16Array':
          case 'Int32Array':
          case 'UInt32Array':
          case 'BigInt64Array':
          case 'BigUInt64Array':
          case 'Float32Array':
          case 'Float64Array':
            this._writeArrayField(field, value);
            break;
          case 'StructArray':
            this._writeStructArray(field, value);
            break;
        }
      }

      private _writeArrayField(field: FieldDefinition, value: any[]): void {
        const buffer = this._buffer;
        const offset = field.offset;
        const length = field.arrayLength || 0;
        const arr = value || [];

        for (let i = 0; i < length; i++) {
          const elemOffset = offset + i * (ARRAY_ELEMENT_SIZES[field.type] || 1);
          const elemValue = i < arr.length ? arr[i] : 0;
          switch (field.type) {
            case 'Int8Array':
              buffer.writeInt8(elemValue, elemOffset);
              break;
            case 'UInt8Array':
              buffer.writeUInt8(elemValue, elemOffset);
              break;
            case 'Int16Array':
              buffer.writeInt16LE(elemValue, elemOffset);
              break;
            case 'UInt16Array':
              buffer.writeUInt16LE(elemValue, elemOffset);
              break;
            case 'Int32Array':
              buffer.writeInt32LE(elemValue, elemOffset);
              break;
            case 'UInt32Array':
              buffer.writeUInt32LE(elemValue, elemOffset);
              break;
            case 'BigInt64Array':
              buffer.writeBigInt64LE(BigInt(elemValue || 0), elemOffset);
              break;
            case 'BigUInt64Array':
              buffer.writeBigUInt64LE(BigInt(elemValue || 0), elemOffset);
              break;
            case 'Float32Array':
              buffer.writeFloatLE(elemValue, elemOffset);
              break;
            case 'Float64Array':
              buffer.writeDoubleLE(elemValue, elemOffset);
              break;
          }
        }
      }

      private _writeStructArray(field: FieldDefinition, value: unknown[]): void {
        const buffer = this._buffer;
        const offset = field.offset;
        const length = field.arrayLength || 0;
        const structType = field.structType!;
        const elementSize = structType.getSize();
        const arr = value || [];

        for (let i = 0; i < length; i++) {
          const elemOffset = offset + i * elementSize;
          if (i < arr.length && arr[i]) {
            // Check if it's a struct instance (has _buffer) or a plain object
            let srcRaw: Buffer;
            const element = arr[i];
            if (isStructInstance(element)) {
              // It's a struct instance, get its raw buffer
              srcRaw = Struct.raw(element);
            } else if (typeof element === 'object' && element !== null) {
              // It's a plain object, create a new struct and copy properties
              const tempStruct = new structType();
              const elemObj = element as Record<string, unknown>;
              const tempStructObj = tempStruct as unknown as Record<string, unknown>;
              for (const key of Object.keys(elemObj)) {
                tempStructObj[key] = elemObj[key];
              }
              srcRaw = Struct.raw(tempStruct);
            } else {
              // Invalid element, zero-fill
              buffer.fill(0, elemOffset, elemOffset + elementSize);
              continue;
            }
            srcRaw.copy(buffer, elemOffset, 0, elementSize);
          } else {
            // Zero-fill
            buffer.fill(0, elemOffset, elemOffset + elementSize);
          }
        }
      }

      getSize(): number {
        return totalSize;
      }

      static getSize(): number {
        return totalSize;
      }
    };

    // Assign message ID if set
    if (this._msgid !== undefined) {
      (CompiledStructClass as any)._msgid = this._msgid;
    }

    return CompiledStructClass as CompiledStruct;
  }

  /**
   * Get raw buffer from a struct instance.
   * Static method for compatibility with typed-struct API.
   */
  static raw(instance: StructInstance | unknown): Buffer {
    if (isStructInstance(instance)) {
      return instance._buffer;
    }
    throw new Error('Cannot get raw buffer from non-struct instance');
  }
}

/**
 * ExtractType utility for TypeScript - extracts the instance type from a compiled struct.
 * This provides type inference for struct instances.
 */
export type ExtractType<T> = T extends new (buffer?: Buffer) => infer U ? U : never;
