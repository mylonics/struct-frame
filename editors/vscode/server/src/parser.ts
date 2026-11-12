export interface FieldOptionToken {
  key: string;
  rawKey: string;
  value: string;
  malformed: boolean;
  keyStart: number;
  keyEnd: number;
  valueStart: number;
  valueEnd: number;
  tokenStart: number;
  tokenEnd: number;
}

export interface FieldHeadMatch {
  repeated: boolean;
  type: string;
  name: string;
  tag: number;
  typeStart: number;
  typeEnd: number;
  nameStart: number;
  nameEnd: number;
  tagStart: number;
  tagEnd: number;
  headEnd: number;
}

export interface FieldDeclMatch extends FieldHeadMatch {
  optionsRaw: string;
  optionsStart: number;
  bracketStart: number;
  bracketEnd: number;
}

export interface FieldDefinition {
  name: string;
  type: string;
  tag: number;
  repeated: boolean;
  options: Record<string, string>;
  optionTokens: FieldOptionToken[];
  optionsRaw: string;
  inOneof: boolean;
  oneofName?: string;
  bracketStart?: number;
  bracketEnd?: number;
  line: number;
}

export interface OneofDefinition {
  name: string;
  line: number;
  endLine: number;
  fields: FieldDefinition[];
  options: Record<string, string>;
  optionLines: Record<string, number>;
}

export interface MessageDefinition {
  name: string;
  line: number;
  endLine: number;
  fields: FieldDefinition[];
  oneofs: OneofDefinition[];
  nestedMessages: MessageDefinition[];
  options: Record<string, string>;
  optionLines: Record<string, number>;
}

export interface EnumValue {
  name: string;
  value: number;
  line: number;
}

export interface EnumDefinition {
  name: string;
  line: number;
  endLine: number;
  values: EnumValue[];
  options: Record<string, string>;
  optionLines: Record<string, number>;
  parentMessage?: string;
}

export interface ParsedDocument {
  uri: string;
  packageName: string;
  imports: string[];
  importLines: Record<string, number>;
  messages: MessageDefinition[];
  enums: EnumDefinition[];
  fileOptions: Record<string, string>;
  fileOptionLines: Record<string, number>;
}

// Language tables (primitive types, option names, limits) live in facts.ts, which is
// generated from the compiler; this module only tokenizes and parses.
import { QUALIFIED_OPTION_SOURCE, normalizeFieldOptionKey } from './facts';

export { normalizeFieldOptionKey };

const FIELD_HEAD_RE = /^(\s*)(repeated\s+)?([A-Za-z_]\w*)(\s+)([A-Za-z_]\w*)(\s*=\s*)(\d+)(\s*)/;
// A field option is `name = value` or `(sf.name) = value`. A bare `sf.name` is kept as-is
// so it is reported as unknown, exactly as the compiler ignores it.
const FIELD_OPTION_RE = new RegExp(`^(\\s*)(${QUALIFIED_OPTION_SOURCE}|[\\w.]+)(\\s*=\\s*)(.*?)(\\s*)$`);

export function stripLineComment(line: string): string {
  let inString = false;
  let escaped = false;
  for (let i = 0; i < line.length - 1; i++) {
    const ch = line[i];
    if (inString) {
      if (escaped) {
        escaped = false;
      } else if (ch === '\\') {
        escaped = true;
      } else if (ch === '"') {
        inString = false;
      }
    } else if (ch === '"') {
      inString = true;
    } else if (ch === '/' && line[i + 1] === '/') {
      return line.substring(0, i);
    }
  }
  return line;
}

export function matchFieldHead(line: string): FieldHeadMatch | null {
  const match = line.match(FIELD_HEAD_RE);
  if (!match) return null;
  const indentLength = match[1].length;
  const repeatedLength = match[2]?.length ?? 0;
  const typeStart = indentLength + repeatedLength;
  const typeEnd = typeStart + match[3].length;
  const nameStart = typeEnd + match[4].length;
  const nameEnd = nameStart + match[5].length;
  const tagStart = nameEnd + match[6].length;
  const tagEnd = tagStart + match[7].length;
  return {
    repeated: !!match[2],
    type: match[3],
    name: match[5],
    tag: parseInt(match[7], 10),
    typeStart,
    typeEnd,
    nameStart,
    nameEnd,
    tagStart,
    tagEnd,
    headEnd: match[0].length
  };
}

export function matchFieldDeclaration(line: string): FieldDeclMatch | null {
  const head = matchFieldHead(line);
  if (!head) return null;
  let cursor = head.headEnd;
  while (/\s/.test(line[cursor] ?? '')) cursor++;
  if (line[cursor] !== '[') {
    return line[cursor] === ';' && !line.substring(cursor + 1).trim()
      ? { ...head, optionsRaw: '', optionsStart: cursor, bracketStart: -1, bracketEnd: -1 }
      : null;
  }

  const bracketStart = cursor;
  let inString = false;
  let escaped = false;
  let bracketEnd = -1;
  for (cursor++; cursor < line.length; cursor++) {
    const ch = line[cursor];
    if (inString) {
      if (escaped) {
        escaped = false;
      } else if (ch === '\\') {
        escaped = true;
      } else if (ch === '"') {
        inString = false;
      }
    } else if (ch === '"') {
      inString = true;
    } else if (ch === ']') {
      bracketEnd = cursor;
      break;
    }
  }
  if (bracketEnd < 0) return null;
  cursor = bracketEnd + 1;
  while (/\s/.test(line[cursor] ?? '')) cursor++;
  if (line[cursor] !== ';' || line.substring(cursor + 1).trim()) return null;
  return {
    ...head,
    optionsRaw: line.substring(bracketStart + 1, bracketEnd),
    optionsStart: bracketStart + 1,
    bracketStart,
    bracketEnd
  };
}

export function tokenizeFieldOptions(optionsRaw: string, baseColumn: number): FieldOptionToken[] {
  if (!optionsRaw) return [];
  const segments: Array<{ start: number; end: number }> = [];
  let segmentStart = 0;
  let inString = false;
  let escaped = false;
  for (let i = 0; i < optionsRaw.length; i++) {
    const ch = optionsRaw[i];
    if (inString) {
      if (escaped) {
        escaped = false;
      } else if (ch === '\\') {
        escaped = true;
      } else if (ch === '"') {
        inString = false;
      }
    } else if (ch === '"') {
      inString = true;
    } else if (ch === ',') {
      segments.push({ start: segmentStart, end: i });
      segmentStart = i + 1;
    }
  }
  segments.push({ start: segmentStart, end: optionsRaw.length });

  return segments.map(({ start, end }) => {
    const segment = optionsRaw.substring(start, end);
    const match = segment.match(FIELD_OPTION_RE);
    if (!match) {
      const trimmed = segment.trim();
      const keyStart = baseColumn + start + (segment.indexOf(trimmed) >= 0 ? segment.indexOf(trimmed) : 0);
      return {
        key: normalizeFieldOptionKey(trimmed),
        rawKey: trimmed,
        value: '',
        malformed: true,
        keyStart,
        keyEnd: keyStart + trimmed.length,
        valueStart: baseColumn + end,
        valueEnd: baseColumn + end,
        tokenStart: baseColumn + start,
        tokenEnd: baseColumn + end
      };
    }
    const rawKey = match[2];
    const keyStart = baseColumn + start + match[1].length;
    const keyEnd = keyStart + rawKey.length;
    const valueStart = keyEnd + match[3].length;
    const valueEnd = valueStart + match[4].length;
    return {
      key: normalizeFieldOptionKey(rawKey),
      rawKey,
      value: match[4],
      malformed: false,
      keyStart,
      keyEnd,
      valueStart,
      valueEnd,
      tokenStart: baseColumn + start,
      tokenEnd: baseColumn + end
    };
  });
}

export function parseFieldOptions(optionsRaw: string): Record<string, string> {
  const options: Record<string, string> = {};
  for (const token of tokenizeFieldOptions(optionsRaw, 0)) {
    if (!token.malformed && token.key) options[token.key] = token.value;
  }
  return options;
}

export function parseDocument(uri: string, content: string): ParsedDocument {
  const lines = content.split('\n');
  const doc: ParsedDocument = {
    uri,
    packageName: '',
    imports: [],
    importLines: {},
    messages: [],
    enums: [],
    fileOptions: {},
    fileOptionLines: {}
  };

  let currentMessage: MessageDefinition | null = null;
  let currentNestedMessage: MessageDefinition | null = null;
  let currentEnum: EnumDefinition | null = null;
  let currentNestedEnum: EnumDefinition | null = null;
  let currentOneof: OneofDefinition | null = null;
  let braceDepth = 0;

  for (let i = 0; i < lines.length; i++) {
    const line = stripLineComment(lines[i]);
    const trimmed = line.trim();
    if (!trimmed) continue;

    if (braceDepth === 0) {
      const pkgMatch = trimmed.match(/^package\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*;/);
      if (pkgMatch) {
        doc.packageName = pkgMatch[1];
        continue;
      }
      const importMatch = trimmed.match(/^import\s+"([^"]+)"\s*;/);
      if (importMatch) {
        doc.imports.push(importMatch[1]);
        doc.importLines[importMatch[1]] = i;
        continue;
      }
      const fileOptMatch = trimmed.match(/^option\s+(\w+)\s*=\s*(.+?)\s*;/);
      if (fileOptMatch) {
        doc.fileOptions[fileOptMatch[1]] = fileOptMatch[2];
        doc.fileOptionLines[fileOptMatch[1]] = i;
        continue;
      }
      const msgMatch = trimmed.match(/^message\s+([A-Z][a-zA-Z0-9_]*)\s*\{/);
      if (msgMatch) {
        currentMessage = {
          name: msgMatch[1],
          line: i,
          endLine: i,
          fields: [],
          oneofs: [],
          nestedMessages: [],
          options: {},
          optionLines: {}
        };
        braceDepth = 1;
        continue;
      }
      const enumMatch = trimmed.match(/^enum\s+([A-Z][a-zA-Z0-9_]*)\s*\{/);
      if (enumMatch) {
        currentEnum = {
          name: enumMatch[1],
          line: i,
          endLine: i,
          values: [],
          options: {},
          optionLines: {}
        };
        braceDepth = 1;
        continue;
      }
    }

    if (braceDepth > 0) {
      if (currentMessage && !currentNestedMessage && !currentNestedEnum && !currentOneof && braceDepth === 1) {
        const nestedEnumMatch = trimmed.match(/^enum\s+([A-Z][a-zA-Z0-9_]*)\s*\{/);
        if (nestedEnumMatch) {
          currentNestedEnum = {
            name: nestedEnumMatch[1],
            parentMessage: currentMessage.name,
            line: i,
            endLine: i,
            values: [],
            options: {},
            optionLines: {}
          };
          braceDepth = 2;
          continue;
        }
      }

      if (currentMessage && !currentNestedMessage && !currentNestedEnum && !currentOneof && braceDepth === 1) {
        const nestedMsgMatch = trimmed.match(/^message\s+([A-Z][a-zA-Z0-9_]*)\s*\{/);
        if (nestedMsgMatch) {
          currentNestedMessage = {
            name: nestedMsgMatch[1],
            line: i,
            endLine: i,
            fields: [],
            oneofs: [],
            nestedMessages: [],
            options: {},
            optionLines: {}
          };
          braceDepth = 2;
          continue;
        }
      }

      if (currentMessage && !currentNestedMessage && !currentNestedEnum && !currentOneof && braceDepth === 1) {
        const oneofMatch = trimmed.match(/^oneof\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\{/);
        if (oneofMatch) {
          currentOneof = {
            name: oneofMatch[1],
            line: i,
            endLine: i,
            fields: [],
            options: {},
            optionLines: {}
          };
          braceDepth = 2;
          continue;
        }
      }

      for (const ch of trimmed) {
        if (ch === '{') braceDepth++;
        else if (ch === '}') braceDepth--;
      }

      if (braceDepth === 0) {
        if (currentMessage) {
          currentMessage.endLine = i;
          doc.messages.push(currentMessage);
          currentMessage = null;
        }
        if (currentEnum) {
          currentEnum.endLine = i;
          doc.enums.push(currentEnum);
          currentEnum = null;
        }
        continue;
      }

      if (currentNestedEnum && braceDepth === 1) {
        currentNestedEnum.endLine = i;
        doc.enums.push(currentNestedEnum);
        currentNestedEnum = null;
        continue;
      }

      if (currentNestedMessage && braceDepth === 1) {
        currentNestedMessage.endLine = i;
        currentMessage!.nestedMessages.push(currentNestedMessage);
        doc.messages.push(currentNestedMessage);
        currentNestedMessage = null;
        continue;
      }

      if (currentOneof && braceDepth === 1) {
        currentOneof.endLine = i;
        currentMessage!.oneofs.push(currentOneof);
        currentOneof = null;
        continue;
      }

      if (currentNestedMessage) {
        const optMatch = trimmed.match(/^option\s+(\w+)\s*=\s*(.+?)\s*;/);
        if (optMatch) {
          currentNestedMessage.options[optMatch[1]] = optMatch[2];
          currentNestedMessage.optionLines[optMatch[1]] = i;
          continue;
        }
        const fieldMatch = matchFieldDeclaration(line);
        if (fieldMatch) {
          currentNestedMessage.fields.push({
            name: fieldMatch.name,
            type: fieldMatch.type,
            tag: fieldMatch.tag,
            repeated: fieldMatch.repeated,
            options: parseFieldOptions(fieldMatch.optionsRaw),
            optionTokens: tokenizeFieldOptions(fieldMatch.optionsRaw, fieldMatch.optionsStart),
            optionsRaw: fieldMatch.optionsRaw,
            inOneof: false,
            bracketStart: fieldMatch.bracketStart,
            bracketEnd: fieldMatch.bracketEnd,
            line: i
          });
        }
        continue;
      }

      if (currentNestedEnum) {
        const optMatch = trimmed.match(/^option\s+(\w+)\s*=\s*(.+?)\s*;/);
        if (optMatch) {
          currentNestedEnum.options[optMatch[1]] = optMatch[2];
          currentNestedEnum.optionLines[optMatch[1]] = i;
          continue;
        }
        const enumValMatch = trimmed.match(/^([A-Za-z][A-Za-z0-9_]*)\s*=\s*([0-9]+)\s*;/);
        if (enumValMatch) {
          currentNestedEnum.values.push({
            name: enumValMatch[1],
            value: parseInt(enumValMatch[2], 10),
            line: i
          });
        }
        continue;
      }

      if (currentOneof) {
        const optMatch = trimmed.match(/^option\s+(\w+)\s*=\s*(.+?)\s*;/);
        if (optMatch) {
          currentOneof.options[optMatch[1]] = optMatch[2];
          currentOneof.optionLines[optMatch[1]] = i;
          continue;
        }
        const fieldMatch = matchFieldDeclaration(line);
        if (fieldMatch) {
          currentOneof.fields.push({
            name: fieldMatch.name,
            type: fieldMatch.type,
            tag: fieldMatch.tag,
            repeated: fieldMatch.repeated,
            options: parseFieldOptions(fieldMatch.optionsRaw),
            optionTokens: tokenizeFieldOptions(fieldMatch.optionsRaw, fieldMatch.optionsStart),
            optionsRaw: fieldMatch.optionsRaw,
            inOneof: true,
            oneofName: currentOneof.name,
            bracketStart: fieldMatch.bracketStart,
            bracketEnd: fieldMatch.bracketEnd,
            line: i
          });
        }
        continue;
      }

      if (currentEnum) {
        const optMatch = trimmed.match(/^option\s+(\w+)\s*=\s*(.+?)\s*;/);
        if (optMatch) {
          currentEnum.options[optMatch[1]] = optMatch[2];
          currentEnum.optionLines[optMatch[1]] = i;
          continue;
        }
        const enumValMatch = trimmed.match(/^([A-Za-z][A-Za-z0-9_]*)\s*=\s*([0-9]+)\s*;/);
        if (enumValMatch) {
          currentEnum.values.push({
            name: enumValMatch[1],
            value: parseInt(enumValMatch[2], 10),
            line: i
          });
        }
        continue;
      }

      if (currentMessage) {
        const optMatch = trimmed.match(/^option\s+(\w+)\s*=\s*(.+?)\s*;/);
        if (optMatch) {
          currentMessage.options[optMatch[1]] = optMatch[2];
          currentMessage.optionLines[optMatch[1]] = i;
          continue;
        }
        const fieldMatch = matchFieldDeclaration(line);
        if (fieldMatch) {
          currentMessage.fields.push({
            name: fieldMatch.name,
            type: fieldMatch.type,
            tag: fieldMatch.tag,
            repeated: fieldMatch.repeated,
            options: parseFieldOptions(fieldMatch.optionsRaw),
            optionTokens: tokenizeFieldOptions(fieldMatch.optionsRaw, fieldMatch.optionsStart),
            optionsRaw: fieldMatch.optionsRaw,
            inOneof: false,
            bracketStart: fieldMatch.bracketStart,
            bracketEnd: fieldMatch.bracketEnd,
            line: i
          });
        }
      }
    }
  }

  return doc;
}
