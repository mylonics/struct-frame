/**
 * Custom struct serialization implementation for JavaScript.
 * Human-readable JavaScript version providing binary struct definition,
 * serialization and deserialization.
 */
"use strict";

// Type mappings for field sizes
const FIELD_SIZES = {
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
  'String': 1 // Per character
};

const ARRAY_ELEMENT_SIZES = {
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

/**
 * Type guard to check if an object is a struct instance
 */
function isStructInstance(obj) {
  return typeof obj === 'object' && obj !== null && '_buffer' in obj && Buffer.isBuffer(obj._buffer);
}

/**
 * Struct class for defining binary message structures.
 * Provides a chainable API similar to typed-struct.
 */
class Struct {
  constructor(name) {
    this.name = name || 'Struct';
    this.fields = [];
    this.currentOffset = 0;
  }

  // Primitive field methods
  Int8(fieldName) {
    this._addField(fieldName, 'Int8', FIELD_SIZES['Int8']);
    return this;
  }

  UInt8(fieldName) {
    this._addField(fieldName, 'UInt8', FIELD_SIZES['UInt8']);
    return this;
  }

  Int16LE(fieldName) {
    this._addField(fieldName, 'Int16LE', FIELD_SIZES['Int16LE']);
    return this;
  }

  UInt16LE(fieldName) {
    this._addField(fieldName, 'UInt16LE', FIELD_SIZES['UInt16LE']);
    return this;
  }

  Int32LE(fieldName) {
    this._addField(fieldName, 'Int32LE', FIELD_SIZES['Int32LE']);
    return this;
  }

  UInt32LE(fieldName) {
    this._addField(fieldName, 'UInt32LE', FIELD_SIZES['UInt32LE']);
    return this;
  }

  BigInt64LE(fieldName) {
    this._addField(fieldName, 'BigInt64LE', FIELD_SIZES['BigInt64LE']);
    return this;
  }

  BigUInt64LE(fieldName) {
    this._addField(fieldName, 'BigUInt64LE', FIELD_SIZES['BigUInt64LE']);
    return this;
  }

  Float32LE(fieldName) {
    this._addField(fieldName, 'Float32LE', FIELD_SIZES['Float32LE']);
    return this;
  }

  Float64LE(fieldName) {
    this._addField(fieldName, 'Float64LE', FIELD_SIZES['Float64LE']);
    return this;
  }

  Boolean8(fieldName) {
    this._addField(fieldName, 'Boolean8', FIELD_SIZES['Boolean8']);
    return this;
  }

  String(fieldName, length) {
    length = length || 0;
    this._addField(fieldName, 'String', length);
    return this;
  }

  // Array field methods
  Int8Array(fieldName, length) {
    this._addArrayField(fieldName, 'Int8Array', length);
    return this;
  }

  UInt8Array(fieldName, length) {
    this._addArrayField(fieldName, 'UInt8Array', length);
    return this;
  }

  Int16Array(fieldName, length) {
    this._addArrayField(fieldName, 'Int16Array', length);
    return this;
  }

  UInt16Array(fieldName, length) {
    this._addArrayField(fieldName, 'UInt16Array', length);
    return this;
  }

  Int32Array(fieldName, length) {
    this._addArrayField(fieldName, 'Int32Array', length);
    return this;
  }

  UInt32Array(fieldName, length) {
    this._addArrayField(fieldName, 'UInt32Array', length);
    return this;
  }

  BigInt64Array(fieldName, length) {
    this._addArrayField(fieldName, 'BigInt64Array', length);
    return this;
  }

  BigUInt64Array(fieldName, length) {
    this._addArrayField(fieldName, 'BigUInt64Array', length);
    return this;
  }

  Float32Array(fieldName, length) {
    this._addArrayField(fieldName, 'Float32Array', length);
    return this;
  }

  Float64Array(fieldName, length) {
    this._addArrayField(fieldName, 'Float64Array', length);
    return this;
  }

  /**
   * ByteArray is an alias for UInt8Array, used for union data storage.
   */
  ByteArray(fieldName, length) {
    this._addArrayField(fieldName, 'UInt8Array', length);
    return this;
  }

  StructArray(fieldName, length, structType) {
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

  _addField(fieldName, type, size) {
    this.fields.push({
      name: fieldName,
      type: type,
      size: size,
      offset: this.currentOffset
    });
    this.currentOffset += size;
  }

  _addArrayField(fieldName, type, length) {
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
  compile() {
    const fields = [...this.fields];
    const totalSize = this.currentOffset;
    const structName = this.name;

    // Create a class that can be instantiated with optional buffer
    function CompiledStructClass(buffer) {
      if (buffer) {
        this._buffer = Buffer.from(buffer);
      } else {
        this._buffer = Buffer.alloc(totalSize);
      }
      this._defineProperties();
    }

    CompiledStructClass._fields = fields;
    CompiledStructClass._size = totalSize;
    CompiledStructClass._structName = structName;

    CompiledStructClass.prototype._defineProperties = function() {
      for (const field of fields) {
        this._defineFieldProperty(field);
      }
    };

    CompiledStructClass.prototype._defineFieldProperty = function(field) {
      const self = this;
      Object.defineProperty(this, field.name, {
        get: function() { return self._readField(field); },
        set: function(value) { self._writeField(field, value); },
        enumerable: true,
        configurable: true
      });
    };

    CompiledStructClass.prototype._readField = function(field) {
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
    };

    CompiledStructClass.prototype._readArrayField = function(field) {
      const buffer = this._buffer;
      const offset = field.offset;
      const length = field.arrayLength || 0;
      const result = [];

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
    };

    CompiledStructClass.prototype._readStructArray = function(field) {
      const buffer = this._buffer;
      const offset = field.offset;
      const length = field.arrayLength || 0;
      const structType = field.structType;
      const elementSize = structType.getSize();
      const result = [];

      for (let i = 0; i < length; i++) {
        const elemOffset = offset + i * elementSize;
        const elemBuffer = buffer.slice(elemOffset, elemOffset + elementSize);
        result.push(new structType(elemBuffer));
      }
      return result;
    };

    CompiledStructClass.prototype._writeField = function(field, value) {
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
    };

    CompiledStructClass.prototype._writeArrayField = function(field, value) {
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
    };

    CompiledStructClass.prototype._writeStructArray = function(field, value) {
      const buffer = this._buffer;
      const offset = field.offset;
      const length = field.arrayLength || 0;
      const structType = field.structType;
      const elementSize = structType.getSize();
      const arr = value || [];

      for (let i = 0; i < length; i++) {
        const elemOffset = offset + i * elementSize;
        if (i < arr.length && arr[i]) {
          // Check if it's a struct instance (has _buffer) or a plain object
          let srcRaw;
          const element = arr[i];
          if (isStructInstance(element)) {
            // It's a struct instance, get its raw buffer
            srcRaw = Struct.raw(element);
          } else if (typeof element === 'object' && element !== null) {
            // It's a plain object, create a new struct and copy properties
            const tempStruct = new structType();
            for (const key of Object.keys(element)) {
              tempStruct[key] = element[key];
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
    };

    CompiledStructClass.prototype.getSize = function() {
      return totalSize;
    };

    CompiledStructClass.getSize = function() {
      return totalSize;
    };

    return CompiledStructClass;
  }

  /**
   * Get raw buffer from a struct instance.
   * Static method for compatibility with typed-struct API.
   */
  static raw(instance) {
    if (isStructInstance(instance)) {
      return instance._buffer;
    }
    throw new Error('Cannot get raw buffer from non-struct instance');
  }
}

module.exports.Struct = Struct;
