import {
  createConnection,
  TextDocuments,
  ProposedFeatures,
  InitializeParams,
  DidChangeConfigurationNotification,
  CompletionItem,
  CompletionItemKind,
  InsertTextFormat,
  TextDocumentPositionParams,
  TextDocumentSyncKind,
  InitializeResult,
  Location,
  Range,
  Position,
  Hover,
  MarkupKind,
  DocumentSymbol,
  SymbolKind,
  SymbolInformation,
  Definition,
  FileChangeType,
  Diagnostic,
  DiagnosticSeverity,
  CodeAction,
  CodeActionKind,
  CodeActionParams,
  TextEdit,
  WorkspaceEdit,
  FoldingRange,
  FoldingRangeKind,
  RenameParams,
} from 'vscode-languageserver/node';
import { TextDocument } from 'vscode-languageserver-textdocument';
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath, pathToFileURL } from 'url';
import * as parser from './parser';
import {
  PRIMITIVE_TYPES, FIXED_SIZE_PRIMITIVES, isPrimitive, isStringLike, INT_RANGES, FLOAT_MAX, ENUM_VALUE_RANGE,
  OPTION_NAMES, OptionScope, OPTION_QUALIFIERS, acceptedOptionNames, isKnownOption, getOption, DISCRIMINATOR_MODES,
  normalizeDiscriminator, isTrueValue, isFalseValue, LIMITS
} from './facts';
import { PRIMITIVE_TYPE_DOCS, DISCRIMINATOR_DOCS, KEYWORD_DOCS, optionDoc, optionHover } from './docs';

const connection = createConnection(ProposedFeatures.all);
const documents: TextDocuments<TextDocument> = new TextDocuments(TextDocument);

interface FieldDefinition {
  name: string;
  type: string;
  tag: number;
  repeated: boolean;
  options: Record<string, string>;
  optionTokens?: parser.FieldOptionToken[];
  optionsRaw?: string;
  inOneof?: boolean;
  oneofName?: string;
  bracketStart?: number;
  bracketEnd?: number;
  line: number;
}

interface OneofDefinition {
  name: string;
  line: number;
  endLine: number;
  fields: FieldDefinition[];
  options: Record<string, string>;
  optionLines: Record<string, number>;
}

interface MessageDefinition {
  name: string;
  line: number;
  endLine: number;
  fields: FieldDefinition[];
  oneofs: OneofDefinition[];
  nestedMessages: MessageDefinition[];
  options: Record<string, string>;
  optionLines: Record<string, number>;
}

interface EnumValue {
  name: string;
  value: number;
  line: number;
}

interface EnumDefinition {
  name: string;
  line: number;
  endLine: number;
  values: EnumValue[];
  options?: Record<string, string>;
  optionLines?: Record<string, number>;
  parentMessage?: string;
}

interface ParsedDocument {
  uri: string;
  packageName: string;
  imports: string[];
  importLines: Record<string, number>;
  messages: MessageDefinition[];
  enums: EnumDefinition[];
  fileOptions: Record<string, string>;
  fileOptionLines: Record<string, number>;
}

const parsedDocuments = new Map<string, ParsedDocument>();
// Cache for import-path completions: key=directory -> items
// Cleared whenever a .sf file in that directory changes.
const importScanCache = new Map<string, CompletionItem[]>();

// --- sf_compile.json support ---

interface SfCompileGeneratedFileEntry {
  path: string;
  namespace: string | null;
  element: string;
  qualified_element: string;
}

interface SfCompileGeneratedFiles {
  [key: string]: SfCompileGeneratedFileEntry | undefined;
}

interface SfCompileOneofEntry {
  name: string;
  size: number;
  base_size?: number;
  variable?: boolean;
  auto_discriminator?: boolean;
  discriminator_type?: string | null;
  min_size_override?: number | null;
  max_size_override?: number | null;
  variants?: Array<{ disc_val: number; field_name: string; field_size: number }>;
}

interface SfCompileEntry {
  name: string;
  package: string;
  source_file: string;
  generated_files: SfCompileGeneratedFiles;
  parent_message?: string;
  // New fields (struct-frame latest release)
  msgid?: number | null;
  max_size?: number;
  base_size?: number;
  min_size?: number;
  is_variable?: boolean;
  is_envelope?: boolean;
  extensions_start?: number | null;
  magic_bytes?: [number, number] | null;
  oneofs?: SfCompileOneofEntry[] | null;
}

interface SfCompileConfig {
  messages: SfCompileEntry[];
  nested_messages?: SfCompileEntry[];
  enums: SfCompileEntry[];
}

let sfCompileConfig: SfCompileConfig | null = null;
let sfCompileConfigPath = 'sf_compile.json';
let workspaceRoot = '';

type RawGeneratedFile = string | Partial<SfCompileGeneratedFileEntry> | null | undefined;

function normalizeGeneratedFileEntry(raw: RawGeneratedFile, fallbackElement: string): SfCompileGeneratedFileEntry | undefined {
  if (typeof raw === 'string') {
    return {
      path: raw,
      namespace: null,
      element: fallbackElement,
      qualified_element: fallbackElement
    };
  }
  if (!raw || typeof raw.path !== 'string') return undefined;
  return {
    path: raw.path,
    namespace: typeof raw.namespace === 'string' ? raw.namespace : null,
    element: typeof raw.element === 'string' ? raw.element : fallbackElement,
    qualified_element: typeof raw.qualified_element === 'string' ? raw.qualified_element : fallbackElement
  };
}

function normalizeSfCompileEntry(raw: unknown): SfCompileEntry | undefined {
  if (!raw || typeof raw !== 'object') return undefined;
  const entry = raw as Partial<SfCompileEntry> & { generated_files?: unknown };
  if (typeof entry.name !== 'string') return undefined;

  const generatedFiles: SfCompileGeneratedFiles = {};
  if (entry.generated_files && typeof entry.generated_files === 'object') {
    for (const [language, generatedFile] of Object.entries(entry.generated_files as Record<string, RawGeneratedFile>)) {
      const normalized = normalizeGeneratedFileEntry(generatedFile, entry.name);
      if (normalized) generatedFiles[language] = normalized;
    }
  }

  return {
    name: entry.name,
    package: typeof entry.package === 'string' ? entry.package : '',
    source_file: typeof entry.source_file === 'string' ? entry.source_file : '',
    generated_files: generatedFiles,
    ...(typeof entry.parent_message === 'string' ? { parent_message: entry.parent_message } : {}),
    ...(typeof entry.msgid === 'number' || entry.msgid === null ? { msgid: entry.msgid } : {}),
    ...(typeof entry.max_size === 'number' ? { max_size: entry.max_size } : {}),
    ...(typeof entry.base_size === 'number' ? { base_size: entry.base_size } : {}),
    ...(typeof entry.min_size === 'number' ? { min_size: entry.min_size } : {}),
    ...(typeof entry.is_variable === 'boolean' ? { is_variable: entry.is_variable } : {}),
    ...(typeof entry.is_envelope === 'boolean' ? { is_envelope: entry.is_envelope } : {}),
    ...(typeof entry.extensions_start === 'number' || entry.extensions_start === null ? { extensions_start: entry.extensions_start } : {}),
    ...(Array.isArray(entry.magic_bytes) ? { magic_bytes: entry.magic_bytes as [number, number] } : {}),
    ...(Array.isArray(entry.oneofs) ? { oneofs: entry.oneofs } : {})
  };
}

function normalizeSfCompileConfig(raw: unknown): SfCompileConfig {
  if (!raw || typeof raw !== 'object') {
    return { messages: [], nested_messages: [], enums: [] };
  }
  const config = raw as { messages?: unknown; nested_messages?: unknown; enums?: unknown };
  const normalizeEntries = (entries: unknown): SfCompileEntry[] =>
    Array.isArray(entries)
      ? entries.map(normalizeSfCompileEntry).filter((entry): entry is SfCompileEntry => entry !== undefined)
      : [];
  return {
    messages: normalizeEntries(config.messages),
    nested_messages: normalizeEntries(config.nested_messages),
    enums: normalizeEntries(config.enums)
  };
}

function loadSfCompileConfig(): void {
  if (!workspaceRoot) {
    connection.console.warn('loadSfCompileConfig: workspaceRoot is not set, skipping.');
    return;
  }
  let configPath = sfCompileConfigPath;
  if (!path.isAbsolute(configPath)) {
    configPath = path.join(workspaceRoot, configPath);
  }
  connection.console.log(`loadSfCompileConfig: reading '${configPath}'`);
  try {
    const content = fs.readFileSync(configPath, 'utf-8');
    sfCompileConfig = normalizeSfCompileConfig(JSON.parse(content));
    const msgCount = sfCompileConfig.messages.length + (sfCompileConfig.nested_messages?.length ?? 0);
    const enumCount = sfCompileConfig.enums.length;
    connection.console.log(`loadSfCompileConfig: loaded ${msgCount} message(s) and ${enumCount} enum(s) from '${configPath}'`);
  } catch (err) {
    sfCompileConfig = null;
    connection.console.error(`loadSfCompileConfig: failed to read/parse '${configPath}': ${err}`);
  }
}

function findInCompileConfig(name: string): SfCompileEntry | null {
  if (!sfCompileConfig) return null;
  return (
    sfCompileConfig.messages.find(m => m.name === name) ||
    (sfCompileConfig.nested_messages ?? []).find(m => m.name === name) ||
    sfCompileConfig.enums.find(e => e.name === name) ||
    null
  );
}

function isEnumInCompileConfig(name: string): boolean {
  if (!sfCompileConfig) return false;
  return sfCompileConfig.enums.some(e => e.name === name);
}

function getCompileConfigSourceDir(): string {
  if (!workspaceRoot) return '';
  let configPath = sfCompileConfigPath;
  if (!path.isAbsolute(configPath)) {
    configPath = path.join(workspaceRoot, configPath);
  }
  return path.dirname(configPath);
}

async function refreshConfiguration(): Promise<void> {
  if (!hasConfigurationCapability) {
    connection.console.warn('refreshConfiguration: client does not support workspace configuration; using defaults.');
    loadSfCompileConfig();
    return;
  }
  const config = await connection.workspace.getConfiguration('structFrameLs');
  sfCompileConfigPath = (config?.compileConfigPath as string) || 'sf_compile.json';
  connection.console.log(`refreshConfiguration: compileConfigPath = '${sfCompileConfigPath}'`);
  loadSfCompileConfig();
}

function parseFieldOptions(optionsStr: string): Record<string, string> {
  return parser.parseFieldOptions(optionsStr);
}

function makeDiagnostic(line: number, message: string, severity: DiagnosticSeverity = DiagnosticSeverity.Error, data?: unknown): Diagnostic {
  return {
    severity,
    range: Range.create(line, 0, line, 10000),
    message,
    source: 'struct-frame',
    data
  };
}

function makeRangeDiagnostic(range: Range, message: string, severity: DiagnosticSeverity = DiagnosticSeverity.Error, data?: unknown): Diagnostic {
  return {
    severity,
    range,
    message,
    source: 'struct-frame',
    data
  };
}

const VALID_FIELD_OPTIONS = new Set(OPTION_NAMES.field);
const SIZE_RANGE_TEXT = `${LIMITS.sizeOption.min}–${LIMITS.sizeOption.max}`;
/** Regex source for an optional `(sf.` / `(struct_frame.` prefix while a field option name is being typed. */
const OPTION_KEY_PREFIX = `(?:\\((?:${OPTION_QUALIFIERS.join('|')})\\.)?`;

/** Which option scope an `option` statement at the cursor belongs to (innermost block wins). */
function optionScopeAt(inMessage: boolean, inOneof: boolean, inEnum: boolean): OptionScope {
  if (inEnum) return 'enum';
  if (inOneof) return 'oneof';
  if (inMessage) return 'message';
  return 'file';
}

/** Diagnostic for a bool-valued option: the compiler treats unrecognized spellings as false. */
function checkBoolOption(value: string | undefined, label: string, line: number, diagnostics: Diagnostic[]): void {
  if (value === undefined || isTrueValue(value) || isFalseValue(value)) return;
  diagnostics.push(makeDiagnostic(line,
    `${label} is not a recognized boolean ('${value}'); the compiler treats it as false. Use true or false.`,
    DiagnosticSeverity.Warning));
}

function parseIntegerLiteral(value: string): bigint | null {
  const trimmed = value.trim();
  if (!/^[+-]?(?:0[xX][0-9a-fA-F]+|[0-9]+)$/.test(trimmed)) return null;
  const negative = trimmed.startsWith('-');
  const unsigned = trimmed.replace(/^[+-]/, '');
  try {
    const parsed = BigInt(unsigned);
    return negative ? -parsed : parsed;
  } catch {
    return null;
  }
}

function levenshteinDistance(left: string, right: string): number {
  const previous = Array.from({ length: right.length + 1 }, (_, index) => index);
  for (let leftIndex = 0; leftIndex < left.length; leftIndex++) {
    const current = [leftIndex + 1];
    for (let rightIndex = 0; rightIndex < right.length; rightIndex++) {
      current.push(Math.min(
        current[rightIndex] + 1,
        previous[rightIndex + 1] + 1,
        previous[rightIndex] + (left[leftIndex] === right[rightIndex] ? 0 : 1)
      ));
    }
    previous.splice(0, previous.length, ...current);
  }
  return previous[right.length];
}

function unescapeDefaultString(value: string): string {
  return value.substring(1, value.length - 1).replace(/\\([ntr0"\\])/g, (_match, escaped: string) => ({
    n: '\n',
    t: '\t',
    r: '\r',
    '0': '\0',
    '"': '"',
    '\\': '\\'
  }[escaped] ?? escaped));
}

function validateField(
  field: FieldDefinition,
  ctx: {
    msg: MessageDefinition;
    oneof: OneofDefinition | null;
    messageNames: Set<string>;
    allDefs: { messages: MessageDefinition[]; enums: EnumDefinition[] };
    siblingFieldNames: FieldDefinition[];
  },
  diagnostics: Diagnostic[]
): void {
  const tokens = field.optionTokens ?? parser.tokenizeFieldOptions(field.optionsRaw ?? '', 0);
  const seenOptions = new Set<string>();
  for (const token of tokens) {
    const displayKey = token.rawKey || token.key || field.optionsRaw || '';
    const optionRange = Range.create(field.line, token.keyStart, field.line, token.keyEnd);
    if (token.malformed) {
      diagnostics.push(makeRangeDiagnostic(optionRange, `Malformed field option '${displayKey}'; expected name = value`, DiagnosticSeverity.Warning));
      continue;
    }
    if (!VALID_FIELD_OPTIONS.has(token.key)) {
      const suggestion = [...VALID_FIELD_OPTIONS].find(option => levenshteinDistance(token.key, option) <= 2);
      diagnostics.push(makeRangeDiagnostic(
        optionRange,
        `Unknown field option '${token.key}'. Valid options: ${[...VALID_FIELD_OPTIONS].join(', ')}.` + (suggestion ? ` Did you mean '${suggestion}'?` : ''),
        DiagnosticSeverity.Warning
      ));
    }
    if (seenOptions.has(token.key)) {
      diagnostics.push(makeRangeDiagnostic(optionRange, `Duplicate field option '${token.key}'`, DiagnosticSeverity.Warning));
    }
    seenOptions.add(token.key);
  }

  const defaultToken = tokens.find(token => token.key === 'default' && !token.malformed);
  if (defaultToken) {
    const defaultData = {
      fix: 'remove_default',
      tokenStart: defaultToken.tokenStart,
      tokenEnd: defaultToken.tokenEnd,
      bracketStart: field.bracketStart ?? defaultToken.tokenStart,
      bracketEnd: field.bracketEnd ?? defaultToken.tokenEnd,
      onlyOption: tokens.length === 1
    };
    const defaultDiagnostic = (range: Range, message: string): void => {
      diagnostics.push(makeRangeDiagnostic(range, message, DiagnosticSeverity.Error, defaultData));
    };
    if (field.repeated) {
      defaultDiagnostic(Range.create(field.line, defaultToken.tokenStart, field.line, defaultToken.tokenEnd), `default is not supported on repeated field '${field.name}'`);
    } else if (ctx.oneof) {
      defaultDiagnostic(Range.create(field.line, defaultToken.tokenStart, field.line, defaultToken.tokenEnd), `default is not supported inside oneof '${ctx.oneof.name}'`);
    } else if (ctx.messageNames.has(field.type)) {
      defaultDiagnostic(Range.create(field.line, defaultToken.tokenStart, field.line, defaultToken.tokenEnd), `default is not supported on message-typed field '${field.name}'`);
    } else if (field.type === 'bool') {
      if (defaultToken.value !== 'true' && defaultToken.value !== 'false') {
        defaultDiagnostic(Range.create(field.line, defaultToken.valueStart, field.line, defaultToken.valueEnd), `default for bool must be 'true' or 'false', got '${defaultToken.value}'`);
      }
    } else if (INT_RANGES[field.type]) {
      const parsed = parseIntegerLiteral(defaultToken.value);
      const range = INT_RANGES[field.type];
      if (parsed === null || parsed < range.min || parsed > range.max) {
        defaultDiagnostic(Range.create(field.line, defaultToken.valueStart, field.line, defaultToken.valueEnd), `default for ${field.type} must be an integer in range ${range.min}..${range.max}, got '${defaultToken.value}'`);
      }
    } else if (field.type === 'float' || field.type === 'double') {
      const value = defaultToken.value.trim();
      const numberPattern = /^[+-]?(?:(?:\d+\.?\d*)|(?:\.\d+))(?:[eE][+-]?\d+)?$/;
      const parsed = Number(value);
      if (!numberPattern.test(value) || !Number.isFinite(parsed) || (field.type === 'float' && Math.abs(parsed) > FLOAT_MAX)) {
        defaultDiagnostic(Range.create(field.line, defaultToken.valueStart, field.line, defaultToken.valueEnd), `default for ${field.type} must be a finite floating-point value, got '${defaultToken.value}'`);
      }
    } else if (isStringLike(field.type)) {
      const value = defaultToken.value.trim();
      if (!/^"(?:[^"\\]|\\.)*"$/.test(value)) {
        defaultDiagnostic(Range.create(field.line, defaultToken.valueStart, field.line, defaultToken.valueEnd), `default for ${field.type} must be a quoted literal, got '${defaultToken.value}'`);
      } else {
        const limitOption = field.options['size'] ?? field.options['max_size'];
        const limit = limitOption === undefined ? null : parseIntegerLiteral(limitOption);
        if (limit !== null && Buffer.byteLength(unescapeDefaultString(value), 'utf8') > Number(limit)) {
          defaultDiagnostic(Range.create(field.line, defaultToken.valueStart, field.line, defaultToken.valueEnd), `default string exceeds ${limitOption === field.options['size'] ? 'size' : 'max_size'}=${limitOption}`);
        }
      }
    } else {
      const enumDefinition = ctx.allDefs.enums.find(enm => enm.name === field.type);
      if (enumDefinition) {
        const validMember = enumDefinition.values.some(value => value.name === defaultToken.value);
        if (!/^[A-Za-z_]\w*$/.test(defaultToken.value) || !validMember) {
          defaultDiagnostic(Range.create(field.line, defaultToken.valueStart, field.line, defaultToken.valueEnd), `default for enum '${field.type}' must be one of: ${enumDefinition.values.map(value => value.name).join(', ')}`);
        }
      }
    }
  }

  const hasSize = 'size' in field.options;
  const hasMaxSize = 'max_size' in field.options;
  const hasElementSize = 'element_size' in field.options;
  const stringLabel = field.type === 'bytes' ? 'Bytes' : 'String';
  const elementSizeOnly = `element_size is only valid on repeated string or bytes fields`;
  if (isStringLike(field.type) && !field.repeated) {
    if (!hasSize && !hasMaxSize) diagnostics.push(makeDiagnostic(field.line, `${stringLabel} field '${field.name}' requires [size=N] or [max_size=N]`, DiagnosticSeverity.Error, { fix: 'add_size', fieldLine: field.line }));
    else if (hasSize && hasMaxSize) diagnostics.push(makeDiagnostic(field.line, `${stringLabel} field '${field.name}' cannot have both size and max_size`));
    if (hasElementSize) diagnostics.push(makeDiagnostic(field.line, elementSizeOnly));
  } else if (isStringLike(field.type) && field.repeated) {
    if (!hasSize && !hasMaxSize) diagnostics.push(makeDiagnostic(field.line, `Repeated ${field.type} field '${field.name}' requires [size=N] or [max_size=N]`, DiagnosticSeverity.Error, { fix: 'add_size', fieldLine: field.line }));
    else if (hasSize && hasMaxSize) diagnostics.push(makeDiagnostic(field.line, `Repeated ${field.type} field '${field.name}' cannot have both size and max_size`));
    if (!hasElementSize) diagnostics.push(makeDiagnostic(field.line, `Repeated ${field.type} field '${field.name}' requires [element_size=M]`, DiagnosticSeverity.Error, { fix: 'add_element_size', fieldLine: field.line }));
  } else if (field.repeated) {
    // Every array (primitive, enum or message) needs an element count, as in the compiler.
    const label = ctx.messageNames.has(field.type) ? 'Repeated message field' : 'Repeated field';
    if (!hasSize && !hasMaxSize) diagnostics.push(makeDiagnostic(field.line, `${label} '${field.name}' requires [size=N] or [max_size=N]`, DiagnosticSeverity.Error, { fix: 'add_size', fieldLine: field.line }));
    else if (hasSize && hasMaxSize) diagnostics.push(makeDiagnostic(field.line, `${label} '${field.name}' cannot have both size and max_size`));
    if (hasElementSize) diagnostics.push(makeDiagnostic(field.line, elementSizeOnly));
  } else if (isPrimitive(field.type) && (hasSize || hasMaxSize || hasElementSize)) {
    diagnostics.push(makeDiagnostic(field.line, `size, max_size and element_size are not valid on scalar field '${field.name}' (${field.type})`));
  }

  const minSize = BigInt(LIMITS.sizeOption.min);
  const maxSize = BigInt(LIMITS.sizeOption.max);
  for (const option of ['size', 'max_size', 'element_size']) {
    if (!(option in field.options)) continue;
    const value = parseIntegerLiteral(field.options[option]);
    if (value === null || value < minSize || value > maxSize) {
      diagnostics.push(makeDiagnostic(field.line, `'${option}' must be ${SIZE_RANGE_TEXT}, got '${field.options[option]}'`));
    } else if (option === 'max_size' && value > BigInt(LIMITS.oneBytePrefixMax)) {
      diagnostics.push(makeDiagnostic(field.line, `max_size=${value} > ${LIMITS.oneBytePrefixMax}: count/length prefix will be uint16 (2 bytes) instead of uint8 (1 byte)`, DiagnosticSeverity.Information));
    }
  }

  if (isTrueValue(field.options['flatten'])) {
    if (!ctx.messageNames.has(field.type)) diagnostics.push(makeDiagnostic(field.line, `flatten is only valid on message-type fields ('${field.type}' is not a known message)`));
    else {
      diagnostics.push(makeDiagnostic(field.line, `flatten=true only affects Python and GraphQL output; has no effect on C, C++, C#, TypeScript, or Rust`, DiagnosticSeverity.Information));
      const nestedMsg = ctx.allDefs.messages.find(message => message.name === field.type);
      if (nestedMsg) {
        const parentFieldNames = new Set(ctx.siblingFieldNames.filter(sibling => sibling.name !== field.name).map(sibling => sibling.name));
        for (const nestedField of nestedMsg.fields) {
          if (parentFieldNames.has(nestedField.name)) diagnostics.push(makeDiagnostic(field.line, `flatten: field '${nestedField.name}' from '${field.type}' collides with existing field in '${ctx.msg.name}'`));
        }
      }
    }
  }
}

function validateDocument(uri: string): void {
  const parsed = getOrParseDocument(uri);
  const diagnostics: Diagnostic[] = [];

  // All known message names (including imports) for type resolution
  const allDefs = getAllDefinitions(uri);
  const messageNames = new Set(allDefs.messages.map(m => m.name));

  // Within-file: duplicate message names (includes nested messages flattened into doc.messages)
  {
    const seenMsgNames = new Map<string, number>(); // name → first definition line
    for (const msg of parsed.messages) {
      if (seenMsgNames.has(msg.name)) {
        diagnostics.push(makeDiagnostic(msg.line,
          `Duplicate message name '${msg.name}' (already defined at line ${seenMsgNames.get(msg.name)! + 1})`));
      } else {
        seenMsgNames.set(msg.name, msg.line);
      }
    }
  }

  // Within-file: duplicate enum names. Nested enums are scoped to their parent message
  // (two messages may each nest an enum called Status), as in the compiler.
  {
    const seenEnumNames = new Map<string, number>(); // scope::name → first definition line
    for (const enm of parsed.enums) {
      const key = `${enm.parentMessage ?? ''}::${enm.name}`;
      if (seenEnumNames.has(key)) {
        diagnostics.push(makeDiagnostic(enm.line,
          `Duplicate enum name '${enm.name}' (already defined at line ${seenEnumNames.get(key)! + 1})`));
      } else {
        seenEnumNames.set(key, enm.line);
      }
    }
  }

  // Within-file: message name conflicts with a package-level enum name
  {
    const enumNameLines = new Map(parsed.enums.filter(e => !e.parentMessage).map(e => [e.name, e.line]));
    for (const msg of parsed.messages) {
      if (enumNameLines.has(msg.name)) {
        diagnostics.push(makeDiagnostic(msg.line,
          `Name conflict: '${msg.name}' is declared as both a message and an enum in this file`));
      }
    }
  }

  // File-level: pkgid range
  const pkgidStr = parsed.fileOptions['pkgid'];
  const ownPkgid = parsePkgid(pkgidStr);
  if (pkgidStr !== undefined && ownPkgid === null) {
    diagnostics.push(makeDiagnostic(
      parsed.fileOptionLines['pkgid'] ?? 0,
      `pkgid must be an integer ${LIMITS.pkgid.min}–${LIMITS.pkgid.max}, got '${pkgidStr}'`
    ));
  }
  const hasPkgid = ownPkgid !== null;

  // Build cross-file imported def maps for msgid and name conflict checks. Messages are
  // compared by wire id: (pkgid << 8) | msgid with a pkgid, plain msgid without one. A
  // file without its own pkgid inherits its importer's, as the compiler does.
  const importedMsgidMap = new Map<number, { name: string; file: string }>();
  const importedMsgNames = new Map<string, string>(); // name → short filename
  const importedEnumNames = new Map<string, string>();
  {
    for (const { msg, sourceUri, pkgid } of getImportedMessagesWithPkgid(uri, ownPkgid)) {
      const shortFile = shortFileName(sourceUri);
      if (!importedMsgNames.has(msg.name)) {
        importedMsgNames.set(msg.name, shortFile);
      }
      const mid = parseIntegerLiteral(msg.options['msgid'] ?? '');
      if (mid !== null && mid >= 0n) {
        const wireId = wireMessageId(pkgid, Number(mid));
        if (!importedMsgidMap.has(wireId)) importedMsgidMap.set(wireId, { name: msg.name, file: shortFile });
      }
    }
    const allDefsWithSource = getAllDefsWithSource(uri);
    for (const { enm, sourceUri } of allDefsWithSource.enums) {
      if (sourceUri === uri || enm.parentMessage) continue;
      const shortFile = shortFileName(sourceUri);
      if (!importedEnumNames.has(enm.name)) {
        importedEnumNames.set(enm.name, shortFile);
      }
    }
  }

  // File-level: unknown option names
  for (const optName of Object.keys(parsed.fileOptions)) {
    if (!isKnownOption('file', optName)) {
      diagnostics.push(makeDiagnostic(
        parsed.fileOptionLines[optName] ?? 0,
        `Unknown file-level option '${optName}'. Valid options: ${acceptedOptionNames('file').join(', ')}`,
        DiagnosticSeverity.Warning
      ));
    }
  }

  const msgidRange = hasPkgid ? LIMITS.msgidWithPkgid : LIMITS.msgid;
  const msgidMap = new Map<number, string>(); // msgid value → message name

  for (const msg of parsed.messages) {
    // msgid range and uniqueness
    const msgidStr = msg.options['msgid'];
    if (msgidStr !== undefined) {
      const parsedMsgid = parseIntegerLiteral(msgidStr);
      const optLine = msg.optionLines['msgid'] ?? msg.line;
      if (parsedMsgid === null || parsedMsgid < BigInt(msgidRange.min) || parsedMsgid > BigInt(msgidRange.max)) {
        diagnostics.push(makeDiagnostic(optLine, hasPkgid
          ? `msgid must be ${msgidRange.min}–${msgidRange.max} when the file sets 'option pkgid' (the wire id is (pkgid << 8) | msgid), got '${msgidStr}'`
          : `msgid must be ${msgidRange.min}–${msgidRange.max}, got '${msgidStr}'`));
      } else {
        const msgid = Number(parsedMsgid);
        const wireId = wireMessageId(ownPkgid, msgid);
        if (msgidMap.has(msgid)) {
          diagnostics.push(makeDiagnostic(optLine,
            `Duplicate msgid ${msgid} (already used by '${msgidMap.get(msgid)}')`));
        } else if (importedMsgidMap.has(wireId)) {
          const imp = importedMsgidMap.get(wireId)!;
          diagnostics.push(makeDiagnostic(optLine,
            `Duplicate message id ${wireId} (already used by '${imp.name}' in '${imp.file}')`));
        } else {
          msgidMap.set(msgid, msg.name);
        }
      }
    }

    // is_envelope (alias: envelope): requires exactly 1 oneof; all oneof variants must be message types
    const isEnvelopeValue = getOption(msg.options, 'message', 'is_envelope');
    const envelopeLine = msg.optionLines['is_envelope'] ?? msg.optionLines['envelope'] ?? msg.line;
    if (isTrueValue(isEnvelopeValue)) {
      if (!msg.options['msgid']) {
        diagnostics.push(makeDiagnostic(envelopeLine,
          `is_envelope message '${msg.name}' should have option msgid for routing`,
          DiagnosticSeverity.Warning));
      }
      if (msg.oneofs.length !== 1) {
        diagnostics.push(makeDiagnostic(envelopeLine,
          `is_envelope requires exactly one oneof field (found ${msg.oneofs.length})`));
      } else {
        for (const field of msg.oneofs[0].fields) {
          if (!messageNames.has(field.type)) {
            diagnostics.push(makeDiagnostic(field.line,
              `is_envelope: oneof variant '${field.name}' must be a message type (got '${field.type}')`));
          }
        }
      }
    }

    // Unknown message-level option names
    for (const optName of Object.keys(msg.options)) {
      if (!isKnownOption('message', optName)) {
        diagnostics.push(makeDiagnostic(
          msg.optionLines[optName] ?? msg.line,
          `Unknown message option '${optName}'. Valid options: ${acceptedOptionNames('message').join(', ')}`,
          DiagnosticSeverity.Warning
        ));
      }
    }

    // variable / is_envelope value validation
    checkBoolOption(msg.options['variable'], 'option variable', msg.optionLines['variable'] ?? msg.line, diagnostics);
    checkBoolOption(isEnvelopeValue, 'option is_envelope', envelopeLine, diagnostics);
    const msgVariable = isTrueValue(msg.options['variable']);

    // variable=true with nothing variable-length is pointless. Oneofs count: in a variable
    // message they are trimmed to the active variant.
    if (msgVariable) {
      const allFields = [...msg.fields, ...msg.oneofs.flatMap(o => o.fields)];
      const hasMaxSizeField = allFields.some(f => 'max_size' in f.options);
      if (!hasMaxSizeField && msg.oneofs.length === 0) {
        diagnostics.push(makeDiagnostic(
          msg.optionLines['variable'] ?? msg.line,
          `option variable=true has no effect: no fields use [max_size=N] and there is no oneof in '${msg.name}'`,
          DiagnosticSeverity.Warning
        ));
      }
    }
    // Suggest variable=true when max_size fields are present but the option is not set
    if (msg.options['variable'] === undefined) {
      const allFields = [...msg.fields, ...msg.oneofs.flatMap(o => o.fields)];
      const hasMaxSizeField = allFields.some(f => 'max_size' in f.options);
      if (hasMaxSizeField) {
        diagnostics.push(makeDiagnostic(
          msg.line,
          `Message '${msg.name}' has max_size field(s); add 'option variable = true' to enable variable-length encoding`,
          DiagnosticSeverity.Information,
          { fix: 'add_variable_true', msgLine: msg.line }
        ));
      }
    }

    // magic_bytes validation: "0xAB, 0xCD" or "171, 205"
    if (msg.options['magic_bytes'] !== undefined) {
      const mbRaw = msg.options['magic_bytes'].replace(/^"|"$/g, '').trim();
      const mbParts = mbRaw.split(',').map(s => s.trim());
      const optLine = msg.optionLines['magic_bytes'] ?? msg.line;
      const { min, max } = LIMITS.magicByte;
      if (mbParts.length !== LIMITS.magicBytesCount) {
        diagnostics.push(makeDiagnostic(optLine,
          `option magic_bytes requires exactly ${LIMITS.magicBytesCount} comma-separated values, e.g. "0xA3, 0x7F"`));
      } else {
        for (const part of mbParts) {
          const isHex = /^0[xX][0-9a-fA-F]+$/.test(part);
          const isDec = /^\d+$/.test(part);
          const val = isHex ? parseInt(part, 16) : isDec ? parseInt(part, 10) : NaN;
          if (!isHex && !isDec || isNaN(val) || val < min || val > max) {
            diagnostics.push(makeDiagnostic(optLine,
              `option magic_bytes: each value must be ${min}–${max} (hex or decimal), got '${part}'`));
          }
        }
      }
    }

    // message-level discriminator: a default for the message's single oneof
    const msgDiscriminator = msg.options['discriminator'];
    if (msgDiscriminator !== undefined && normalizeDiscriminator(msgDiscriminator) === null) {
      diagnostics.push(makeDiagnostic(msg.optionLines['discriminator'] ?? msg.line,
        `Unknown discriminator value '${msgDiscriminator}'. Valid values: ${DISCRIMINATOR_MODES.join(', ')}`));
    }

    // message-level extensions_start validation
    const extMin = LIMITS.extensionsStartMin;
    if (msg.options['extensions_start'] !== undefined) {
      const extStartStr = msg.options['extensions_start'];
      const optLine = msg.optionLines['extensions_start'] ?? msg.line;
      if (!/^\d+$/.test(extStartStr)) {
        diagnostics.push(makeDiagnostic(optLine,
          `option extensions_start must be an integer ≥ ${extMin}, got '${extStartStr}'`));
      } else {
        const extStart = parseInt(extStartStr, 10);
        if (msg.oneofs.length > 0) {
          diagnostics.push(makeDiagnostic(optLine,
            `message-level extensions_start cannot be combined with oneof fields; use oneof-level extensions_start`));
        } else if (extStart < extMin) {
          diagnostics.push(makeDiagnostic(optLine,
            `option extensions_start must be an integer ≥ ${extMin}, got '${extStartStr}'`));
        } else {
          const allFieldTags = new Set([
            ...msg.fields.map(f => f.tag)
          ]);
          if (!allFieldTags.has(extStart)) {
            diagnostics.push(makeDiagnostic(optLine,
              `option extensions_start=${extStart} must equal an existing field number in '${msg.name}'`));
          }
        }
      }
    }

    // Unknown oneof-level option names
    for (const oneof of msg.oneofs) {
      for (const optName of Object.keys(oneof.options)) {
        if (!isKnownOption('oneof', optName)) {
          diagnostics.push(makeDiagnostic(
            oneof.optionLines[optName] ?? oneof.line,
            `Unknown oneof option '${optName}'. Valid options: ${acceptedOptionNames('oneof').join(', ')}`,
            DiagnosticSeverity.Warning
          ));
        }
      }
    }

    const oneofSizeMin = BigInt(LIMITS.oneofSizeMin);
    for (const oneof of msg.oneofs) {
      const variable = oneof.options['variable'];
      const variableLine = oneof.optionLines['variable'] ?? oneof.line;
      checkBoolOption(variable, 'oneof option variable', variableLine, diagnostics);
      const oneofVariable = isTrueValue(variable);
      if (oneofVariable && !msgVariable) {
        diagnostics.push(makeDiagnostic(variableLine,
          `oneof variable=true requires parent message '${msg.name}' to use option variable = true`,
          DiagnosticSeverity.Error,
          { fix: 'add_msg_variable', msgName: msg.name }));
      }

      const maxSize = oneof.options['max_size'];
      const maxSizeLine = oneof.optionLines['max_size'] ?? oneof.line;
      const parsedMaxSize = maxSize === undefined ? null : parseIntegerLiteral(maxSize);
      if (maxSize !== undefined && (parsedMaxSize === null || parsedMaxSize < oneofSizeMin)) {
        diagnostics.push(makeDiagnostic(maxSizeLine,
          `oneof max_size must be a positive integer, got '${maxSize}'`));
      }
      if (maxSize !== undefined && oneofVariable) {
        diagnostics.push(makeDiagnostic(maxSizeLine,
          `oneof max_size is only valid on non-variable oneofs`));
      }

      const minSize = oneof.options['min_size'];
      const minSizeLine = oneof.optionLines['min_size'] ?? oneof.line;
      const parsedMinSize = minSize === undefined ? null : parseIntegerLiteral(minSize);
      if (minSize !== undefined && (parsedMinSize === null || parsedMinSize < oneofSizeMin)) {
        diagnostics.push(makeDiagnostic(minSizeLine,
          `oneof min_size must be a positive integer, got '${minSize}'`));
      }
      const minSizeApplicable = oneofVariable
        || (msg.fields.every(field => !('max_size' in field.options)) && msg.oneofs.length === 1);
      if (minSize !== undefined && !minSizeApplicable) {
        diagnostics.push(makeDiagnostic(minSizeLine,
          `oneof min_size only applies to a variable oneof or to the sole variable-length field`,
          DiagnosticSeverity.Warning));
      }
      if (parsedMinSize !== null && parsedMaxSize !== null && parsedMinSize > parsedMaxSize) {
        diagnostics.push(makeDiagnostic(minSizeLine,
          `oneof min_size must not exceed max_size`));
      }
    }

    // oneof extensions_start validation
    for (const oneof of msg.oneofs) {
      if (oneof.options['extensions_start'] !== undefined) {
        const extStartStr = oneof.options['extensions_start'];
        const optLine = oneof.optionLines['extensions_start'] ?? oneof.line;
        if (!/^\d+$/.test(extStartStr)) {
          diagnostics.push(makeDiagnostic(optLine,
            `option extensions_start must be an integer ≥ ${extMin}, got '${extStartStr}'`));
        } else {
          const extStart = parseInt(extStartStr, 10);
          if (extStart < extMin) {
            diagnostics.push(makeDiagnostic(optLine,
              `option extensions_start must be an integer ≥ ${extMin}, got '${extStartStr}'`));
          } else {
            const oneofTags = new Set(oneof.fields.map(f => f.tag));
            if (!oneofTags.has(extStart)) {
              diagnostics.push(makeDiagnostic(optLine,
                `option extensions_start=${extStart} must equal an existing field number in oneof '${oneof.name}'`));
            }
          }
        }
      }
    }

    // oneof discriminator validation
    for (const oneof of msg.oneofs) {
      const discRaw = oneof.options['discriminator'];
      let mode = 'auto';
      if (discRaw !== undefined) {
        const normalized = normalizeDiscriminator(discRaw);
        if (normalized === null) {
          diagnostics.push(makeDiagnostic(
            oneof.optionLines['discriminator'] ?? oneof.line,
            `Unknown discriminator value '${discRaw.replace(/"/g, '').trim()}'. Valid values: ${DISCRIMINATOR_MODES.join(', ')}`,
            DiagnosticSeverity.Error
          ));
          continue;
        }
        mode = normalized;
      }
      // The compiler applies a message-level discriminator to a sole oneof left on auto.
      if (mode === 'auto' && msg.oneofs.length === 1 && msgDiscriminator !== undefined) {
        mode = normalizeDiscriminator(msgDiscriminator) ?? 'auto';
      }
      const variants = oneof.fields.map(field => ({ field, message: allDefs.messages.find(m => m.name === field.type) }));
      if (mode === 'auto') {
        mode = variants.length > 0 && variants.every(v => v.message?.options['msgid'] !== undefined) ? 'msgid' : 'field_order';
      }
      if (mode !== 'msgid') continue;
      const seenIds = new Map<string, string>(); // msgid → variant name
      for (const { field, message: variantMsg } of variants) {
        if (!variantMsg) {
          diagnostics.push(makeDiagnostic(field.line,
            `discriminator=msgid: variant '${field.name}' type '${field.type}' is not a known message`));
        } else if (!variantMsg.options['msgid']) {
          diagnostics.push(makeDiagnostic(field.line,
            `discriminator=msgid: variant '${field.name}' (type '${field.type}') does not have msgid`,
            DiagnosticSeverity.Error,
            { fix: 'add_msgid', fieldLine: field.line, msgName: field.type }));
        } else {
          const id = variantMsg.options['msgid'].trim();
          const previous = seenIds.get(id);
          if (previous !== undefined) {
            diagnostics.push(makeDiagnostic(field.line,
              `oneof '${oneof.name}': variants '${previous}' and '${field.name}' have the same discriminator (msgid ${id}); use distinct message types`));
          } else {
            seenIds.set(id, field.name);
          }
        }
      }
    }

    // Field number uniqueness and sequential validation (1..N, no gaps, no duplicates)
    // Oneof fields are numbered independently from message fields — each oneof
    // maintains its own 1..N sequence separate from the parent message.
    {
      const msgTags = new Map<number, string>();
      for (const field of msg.fields) {
        if (msgTags.has(field.tag)) {
          diagnostics.push(makeDiagnostic(field.line,
            `Duplicate field number ${field.tag} in '${msg.name}' (already used by '${msgTags.get(field.tag)}')`));
        } else {
          msgTags.set(field.tag, field.name);
        }
      }
      // Check that message-level field numbers form a contiguous sequence starting at 1
      if (msgTags.size > 0) {
        const maxTag = Math.max(...msgTags.keys());
        for (let n = 1; n <= maxTag; n++) {
          if (!msgTags.has(n)) {
            diagnostics.push(makeDiagnostic(msg.line,
              `Field numbers in '${msg.name}' must be sequential starting at 1; field number ${n} is missing`));
          }
        }
      }
      // Validate each oneof's field numbers independently (separate 1..N sequence)
      for (const oneof of msg.oneofs) {
        const oneofTags = new Map<number, string>();
        for (const field of oneof.fields) {
          if (oneofTags.has(field.tag)) {
            diagnostics.push(makeDiagnostic(field.line,
              `Duplicate field number ${field.tag} in oneof '${oneof.name}' (already used by '${oneofTags.get(field.tag)}')`));
          } else {
            oneofTags.set(field.tag, field.name);
          }
        }
        if (oneofTags.size > 0) {
          const maxOneofTag = Math.max(...oneofTags.keys());
          for (let n = 1; n <= maxOneofTag; n++) {
            if (!oneofTags.has(n)) {
              diagnostics.push(makeDiagnostic(oneof.line,
                `Field numbers in oneof '${oneof.name}' must be sequential starting at 1; field number ${n} is missing`));
            }
          }
        }
      }
    }

    for (const field of msg.fields) {
      validateField(field, {
        msg,
        oneof: null,
        messageNames,
        allDefs,
        siblingFieldNames: msg.fields
      }, diagnostics);
    }
    for (const oneof of msg.oneofs) {
      for (const field of oneof.fields) {
        validateField(field, {
          msg,
          oneof,
          messageNames,
          allDefs,
          siblingFieldNames: [...msg.fields, ...oneof.fields]
        }, diagnostics);
      }
    }
  }

  // Cross-file: name conflicts between current file and imported files
  for (const msg of parsed.messages) {
    if (importedMsgNames.has(msg.name)) {
      diagnostics.push(makeDiagnostic(msg.line,
        `Name conflict: message '${msg.name}' is also defined in '${importedMsgNames.get(msg.name)}'`,
        DiagnosticSeverity.Warning));
    }
    if (importedEnumNames.has(msg.name)) {
      diagnostics.push(makeDiagnostic(msg.line,
        `Name conflict: '${msg.name}' is declared as a message here but as an enum in '${importedEnumNames.get(msg.name)}'`));
    }
  }
  for (const enm of parsed.enums) {
    if (importedEnumNames.has(enm.name)) {
      diagnostics.push(makeDiagnostic(enm.line,
        `Name conflict: enum '${enm.name}' is also defined in '${importedEnumNames.get(enm.name)}'`,
        DiagnosticSeverity.Warning));
    }
    if (importedMsgNames.has(enm.name)) {
      diagnostics.push(makeDiagnostic(enm.line,
        `Name conflict: '${enm.name}' is declared as an enum here but as a message in '${importedMsgNames.get(enm.name)}'`));
    }
  }

  // Enum value range (stored in one byte) and uniqueness
  for (const enm of parsed.enums) {
    const valueNumMap = new Map<number, string>();
    for (const val of enm.values) {
      if (val.value < ENUM_VALUE_RANGE.min || val.value > ENUM_VALUE_RANGE.max) {
        diagnostics.push(makeDiagnostic(val.line,
          `Enum value ${val.value} for '${val.name}' is out of range (enums are stored in 1 byte: ${ENUM_VALUE_RANGE.min}–${ENUM_VALUE_RANGE.max})`));
      }
      if (valueNumMap.has(val.value)) {
        diagnostics.push(makeDiagnostic(val.line,
          `Duplicate enum value ${val.value} in '${enm.name}' (already used by '${valueNumMap.get(val.value)}')`));
      } else {
        valueNumMap.set(val.value, val.name);
      }
    }
  }

  // Import file existence
  for (const imp of parsed.imports) {
    const importUri = resolveImportUri(imp, uri);
    const importPath = importUri.startsWith('file://') ? fileURLToPath(importUri) : importUri;
    if (!fs.existsSync(importPath)) {
      const impLine = parsed.importLines[imp] ?? 0;
      diagnostics.push(makeDiagnostic(impLine, `Cannot resolve import: '${imp}' not found`));
    }
  }

  connection.sendDiagnostics({ uri, diagnostics });
}

function getOrParseDocument(uri: string): ParsedDocument {
  if (parsedDocuments.has(uri)) {
    return parsedDocuments.get(uri)!;
  }

  const doc = documents.get(uri);
  let content: string;
  if (doc) {
    content = doc.getText();
  } else {
    // Try reading from filesystem
    try {
      const filePath = uri.startsWith('file://') ? fileURLToPath(uri) : uri;
      content = fs.readFileSync(filePath, 'utf-8');
      connection.console.log(`getOrParseDocument: read from filesystem '${filePath}'`);
    } catch (err) {
      connection.console.error(`getOrParseDocument: could not read '${uri}': ${err}`);
      return { uri, packageName: '', imports: [], importLines: {}, messages: [], enums: [], fileOptions: {}, fileOptionLines: {} };
    }
  }

  const parsed = parser.parseDocument(uri, content);
  parsedDocuments.set(uri, parsed);
  return parsed;
}

function resolveImportUri(importPath: string, currentUri: string): string {
  const currentFilePath = currentUri.startsWith('file://') ? fileURLToPath(currentUri) : currentUri;
  const currentDir = path.dirname(currentFilePath);
  const resolvedPath = path.resolve(currentDir, importPath);
  const resolved = pathToFileURL(resolvedPath).toString();
  connection.console.log(`resolveImportUri: '${importPath}' from '${currentFilePath}' -> '${resolvedPath}'`);
  if (!fs.existsSync(resolvedPath)) {
    connection.console.warn(`resolveImportUri: resolved path does not exist: '${resolvedPath}'`);
  }
  return resolved;
}

function getAllDefinitions(uri: string, visited = new Set<string>()): { messages: MessageDefinition[]; enums: EnumDefinition[] } {
  if (visited.has(uri)) return { messages: [], enums: [] };
  visited.add(uri);

  const parsed = getOrParseDocument(uri);
  const result = { messages: [...parsed.messages], enums: [...parsed.enums] };

  for (const imp of parsed.imports) {
    const importUri = resolveImportUri(imp, uri);
    const imported = getAllDefinitions(importUri, visited);
    result.messages.push(...imported.messages);
    result.enums.push(...imported.enums);
  }

  return result;
}

function getAllDefsWithSource(uri: string, visited = new Set<string>()): {
  messages: { msg: MessageDefinition; sourceUri: string }[];
  enums: { enm: EnumDefinition; sourceUri: string }[];
} {
  if (visited.has(uri)) return { messages: [], enums: [] };
  visited.add(uri);
  const parsed = getOrParseDocument(uri);
  const result = {
    messages: parsed.messages.map(msg => ({ msg, sourceUri: uri })),
    enums: parsed.enums.map(enm => ({ enm, sourceUri: uri }))
  };
  for (const imp of parsed.imports) {
    const importUri = resolveImportUri(imp, uri);
    const imported = getAllDefsWithSource(importUri, visited);
    result.messages.push(...imported.messages);
    result.enums.push(...imported.enums);
  }
  return result;
}

function shortFileName(uri: string): string {
  return path.basename(uri.startsWith('file://') ? fileURLToPath(uri) : uri);
}

/** A file's `option pkgid`, or null when absent or out of range. */
function parsePkgid(value: string | undefined): number | null {
  if (value === undefined) return null;
  const parsed = parseIntegerLiteral(value);
  if (parsed === null || parsed < BigInt(LIMITS.pkgid.min) || parsed > BigInt(LIMITS.pkgid.max)) return null;
  return Number(parsed);
}

/** The id a message carries on the wire: (pkgid << 8) | msgid with a package id, else msgid. */
function wireMessageId(pkgid: number | null, msgid: number): number {
  return pkgid === null ? msgid : pkgid * 256 + msgid;
}

/** Messages from imported files with their effective pkgid (own, else inherited from the importer). */
function getImportedMessagesWithPkgid(uri: string, inheritedPkgid: number | null): { msg: MessageDefinition; sourceUri: string; pkgid: number | null }[] {
  const result: { msg: MessageDefinition; sourceUri: string; pkgid: number | null }[] = [];
  const visited = new Set<string>([uri]);
  const visit = (fileUri: string, importerPkgid: number | null): void => {
    for (const imp of getOrParseDocument(fileUri).imports) {
      const importUri = resolveImportUri(imp, fileUri);
      if (visited.has(importUri)) continue;
      visited.add(importUri);
      const imported = getOrParseDocument(importUri);
      const pkgid = parsePkgid(imported.fileOptions['pkgid']) ?? importerPkgid;
      for (const msg of imported.messages) result.push({ msg, sourceUri: importUri, pkgid });
      visit(importUri, pkgid);
    }
  };
  visit(uri, inheritedPkgid);
  return result;
}

function getWordAtPosition(text: string, position: Position): { word: string; start: number; end: number } | null {
  const lines = text.split('\n');
  if (position.line >= lines.length) return null;
  const line = lines[position.line];
  let start = position.character;
  let end = position.character;
  while (start > 0 && /[a-zA-Z0-9_]/.test(line[start - 1])) start--;
  while (end < line.length && /[a-zA-Z0-9_]/.test(line[end])) end++;
  const word = line.substring(start, end);
  if (!word) return null;
  return { word, start, end };
}

/**
 * Text-scan based context detection. Works even when blocks are unclosed (actively being typed).
 * Uses a keyword-labelled brace stack so it handles oneof/enum/message nesting correctly.
 */
function getContextAtLine(text: string, lineNum: number): { inMessage: boolean; inOneof: boolean; inEnum: boolean } {
  const lines = text.split('\n');
  const stack: Array<'message' | 'oneof' | 'enum' | 'other'> = [];

  for (let i = 0; i <= lineNum && i < lines.length; i++) {
    const rawLine = lines[i];
    const line = parser.stripLineComment(rawLine);
    const trimmed = line.trim();
    if (!trimmed) continue;

    // Determine the keyword for the first `{` on this line
    let lineKind: 'message' | 'oneof' | 'enum' | 'other' = 'other';
    if (/^message\s+/.test(trimmed)) lineKind = 'message';
    else if (/^oneof\s+/.test(trimmed)) lineKind = 'oneof';
    else if (/^enum\s+/.test(trimmed)) lineKind = 'enum';

    let lineKindUsed = false;
    for (const ch of trimmed) {
      if (ch === '{') {
        stack.push(!lineKindUsed ? lineKind : 'other');
        lineKindUsed = true;
      } else if (ch === '}') {
        stack.pop();
      }
    }
  }

  // Find the innermost named context
  const lastSignificant = [...stack].reverse().find(k => k !== 'other');
  return {
    inMessage: lastSignificant === 'message',
    inOneof: lastSignificant === 'oneof',
    inEnum: lastSignificant === 'enum'
  };
}

let hasConfigurationCapability = false;
let hasWorkspaceFolderCapability = false;

connection.onInitialize((params: InitializeParams) => {
  const capabilities = params.capabilities;
  hasConfigurationCapability = !!(capabilities.workspace && !!capabilities.workspace.configuration);
  hasWorkspaceFolderCapability = !!(capabilities.workspace && !!capabilities.workspace.workspaceFolders);
  connection.console.log(`onInitialize: hasConfigurationCapability=${hasConfigurationCapability}, hasWorkspaceFolderCapability=${hasWorkspaceFolderCapability}`);

  const result: InitializeResult = {
    capabilities: {
      textDocumentSync: TextDocumentSyncKind.Incremental,
      completionProvider: {
        resolveProvider: false,
        triggerCharacters: [' ', '[', '=', '"']
      },
      definitionProvider: true,
      hoverProvider: true,
      documentSymbolProvider: true,
      codeActionProvider: { codeActionKinds: [CodeActionKind.QuickFix] },
      foldingRangeProvider: true,
      referencesProvider: true,
      workspaceSymbolProvider: true,
      renameProvider: { prepareProvider: true },
    }
  };

  if (hasWorkspaceFolderCapability) {
    result.capabilities.workspace = {
      workspaceFolders: { supported: true }
    };
  }

  // Capture workspace root for sf_compile.json resolution
  if (params.workspaceFolders && params.workspaceFolders.length > 0) {
    const folderUri = params.workspaceFolders[0].uri;
    workspaceRoot = folderUri.startsWith('file://') ? fileURLToPath(folderUri) : folderUri;
    connection.console.log(`onInitialize: workspaceRoot='${workspaceRoot}'`);
  } else {
    connection.console.warn('onInitialize: no workspace folders provided; sf_compile.json resolution may fail.');
  }

  return result;
});

connection.onInitialized(async () => {
  connection.console.log('Struct Frame LS initialized.');
  if (hasConfigurationCapability) {
    connection.client.register(DidChangeConfigurationNotification.type, undefined);
  }
  await refreshConfiguration();
});

connection.onDidChangeConfiguration(async () => {
  await refreshConfiguration();
});

connection.onDidChangeWatchedFiles(params => {
  for (const change of params.changes) {
    if (change.uri.endsWith('sf_compile.json')) {
      loadSfCompileConfig();
    }
    if (change.uri.endsWith('.sf')) {
      const changedPath = change.uri.startsWith('file://') ? fileURLToPath(change.uri) : change.uri;
      importScanCache.delete(path.dirname(changedPath));
    }
    parsedDocuments.delete(change.uri);
  }
});

documents.onDidChangeContent(change => {
  const changedPath = change.document.uri.startsWith('file://') ? fileURLToPath(change.document.uri) : change.document.uri;
  importScanCache.delete(path.dirname(changedPath));
  parsedDocuments.delete(change.document.uri);
  validateDocument(change.document.uri);
});

documents.onDidClose(e => {
  parsedDocuments.delete(e.document.uri);
  connection.sendDiagnostics({ uri: e.document.uri, diagnostics: [] });
});

// Completion
function getCompileConfigCompletionItems(existingDefs: { messages: MessageDefinition[]; enums: EnumDefinition[] }): CompletionItem[] {
  if (!sfCompileConfig) return [];
  const existingNames = new Set([
    ...existingDefs.messages.map(m => m.name),
    ...existingDefs.enums.map(e => e.name)
  ]);
  const items: CompletionItem[] = [];
  for (const entry of sfCompileConfig.messages) {
    if (!existingNames.has(entry.name)) {
      items.push({ label: entry.name, kind: CompletionItemKind.Class, detail: `Message (${entry.package})` });
    }
  }
  for (const entry of (sfCompileConfig.nested_messages ?? [])) {
    if (!existingNames.has(entry.name)) {
      items.push({ label: entry.name, kind: CompletionItemKind.Class, detail: `Nested message (${entry.package})` });
    }
  }
  for (const entry of sfCompileConfig.enums) {
    if (!existingNames.has(entry.name)) {
      const detail = entry.parent_message
        ? `Nested enum (${entry.package}, in ${entry.parent_message})`
        : `Enum (${entry.package})`;
      items.push({ label: entry.name, kind: CompletionItemKind.Enum, detail });
    }
  }
  return items;
}

function getImportPathCompletions(currentUri: string, _typedPath: string): CompletionItem[] {
  if (!workspaceRoot) return [];
  const currentFilePath = currentUri.startsWith('file://') ? fileURLToPath(currentUri) : currentUri;
  const currentDir = path.dirname(currentFilePath);
  const currentBasename = path.basename(currentFilePath);

  if (!importScanCache.has(currentDir)) {
    const items: CompletionItem[] = [];
    const scan = (dir: string, prefix: string) => {
      try {
        const entries = fs.readdirSync(dir, { withFileTypes: true });
        for (const entry of entries) {
          if (entry.isDirectory() && !entry.name.startsWith('.') && entry.name !== 'node_modules') {
            scan(path.join(dir, entry.name), prefix + entry.name + '/');
          } else if (entry.isFile() && entry.name.endsWith('.sf')) {
            const relPath = prefix + entry.name;
            items.push({
              label: relPath,
              kind: CompletionItemKind.File,
              detail: '.sf import',
              insertText: relPath + '"',
            });
          }
        }
      } catch { /* ignore unreadable dirs */ }
    };
    scan(currentDir, '');
    importScanCache.set(currentDir, items);
  }

  const cached = importScanCache.get(currentDir)!;
  return cached.filter(item => item.insertText !== currentBasename + '"');
}

connection.onCompletion((params: TextDocumentPositionParams): CompletionItem[] => {
  const doc = documents.get(params.textDocument.uri);
  if (!doc) return [];

  const text = doc.getText();
  const lines = text.split('\n');
  const lineText = lines[params.position.line] || '';
  const lineUpToCursor = lineText.substring(0, params.position.character);
  const { inMessage, inOneof, inEnum } = getContextAtLine(text, params.position.line);

  // ── 0. Inside import "..." string ─────────────────────────────────────
  const importPathMatch = lineUpToCursor.match(/^\s*import\s+"([^"]*)$/);
  if (importPathMatch) {
    return getImportPathCompletions(params.textDocument.uri, importPathMatch[1]);
  }

  // ── 1. Inside [ ] — field options ───────────────────────────────────────
  const bracketStart = lineUpToCursor.lastIndexOf('[');
  const bracketEnd = lineUpToCursor.lastIndexOf(']');
  if (bracketStart > bracketEnd && bracketStart >= 0) {
    const afterBracket = lineUpToCursor.substring(bracketStart + 1);
    const beforeBracket = lineText.substring(0, bracketStart).trimEnd();
    const isRepeated = /^\s*repeated\b/.test(lineText);
    const fieldTypeMatch = beforeBracket.match(/(?:repeated\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s+[a-zA-Z_][a-zA-Z0-9_]*\s*=\s*\d+\s*$/);
    const fieldType = fieldTypeMatch ? fieldTypeMatch[1] : '';
    const allDefs = getAllDefinitions(params.textDocument.uri);
    const isPrimitiveType = isPrimitive(fieldType);
    const isEnumType = allDefs.enums.some(enm => enm.name === fieldType) || isEnumInCompileConfig(fieldType);
    const isStringType = isStringLike(fieldType);
    const isMsgType = !isPrimitiveType && !isEnumType && /^[A-Z]/.test(fieldType);

    if (!isRepeated && !isMsgType && !inOneof && fieldType !== '' &&
      new RegExp(`(?:^|,)\\s*${OPTION_KEY_PREFIX}default\\s*=\\s*$`).test(afterBracket)) {
      if (fieldType === 'bool') {
        return [
          { label: 'true', kind: CompletionItemKind.Value },
          { label: 'false', kind: CompletionItemKind.Value }
        ];
      }
      const enumDefinition = allDefs.enums.find(enm => enm.name === fieldType);
      if (enumDefinition) {
        return enumDefinition.values.map(value => ({
          label: value.name,
          kind: CompletionItemKind.EnumMember,
          detail: `= ${value.value}`
        }));
      }
      if (isStringType) {
        return [{
          label: '"value"',
          kind: CompletionItemKind.Snippet,
          insertText: '"${1:value}"',
          insertTextFormat: InsertTextFormat.Snippet
        }];
      }
      if (INT_RANGES[fieldType]) return [{ label: '0', kind: CompletionItemKind.Value }];
      if (fieldType === 'float' || fieldType === 'double') return [{ label: '0.0', kind: CompletionItemKind.Value }];
    }

    // Value completion for flatten=
    if (new RegExp(`(?:^|,)\\s*${OPTION_KEY_PREFIX}flatten\\s*=\\s*$`).test(afterBracket)) {
      return [
        { label: 'true', kind: CompletionItemKind.Value },
        { label: 'false', kind: CompletionItemKind.Value }
      ];
    }
    // Suggest keys only at start of bracket content or after a comma (not after =)
    if (new RegExp(`(?:^|,)\\s*${OPTION_KEY_PREFIX}[a-zA-Z_]*$`).test(afterBracket)) {
      // Parse the field declaration before the [ to determine what options are applicable
      const applicableOpts = OPTION_NAMES.field.filter(opt => {
        if (opt === 'element_size') return isRepeated && isStringType;
        if (opt === 'flatten') return !isRepeated && isMsgType;
        if (opt === 'default') return !isRepeated && !isMsgType && !inOneof && fieldType !== '';
        return true; // size and max_size always applicable
      });

      const optItems: CompletionItem[] = applicableOpts.map(opt => ({
        label: `${opt}=`,
        kind: CompletionItemKind.Property,
        detail: 'Field option',
        documentation: { kind: MarkupKind.Markdown, value: optionDoc('field', opt) ?? '' },
      }));

      // For repeated string fields, offer combined snippets at the top
      if (isRepeated && isStringType) {
        optItems.unshift(
          {
            label: 'max_size=, element_size=',
            kind: CompletionItemKind.Snippet,
            detail: 'Bounded repeated string (combined)',
            insertText: 'max_size=${1:10}, element_size=${2:32}',
            insertTextFormat: InsertTextFormat.Snippet,
            documentation: 'Bounded array of strings: up to N strings (with 1-byte count prefix), each up to M bytes.',
          },
          {
            label: 'size=, element_size=',
            kind: CompletionItemKind.Snippet,
            detail: 'Fixed repeated string (combined)',
            insertText: 'size=${1:10}, element_size=${2:32}',
            insertTextFormat: InsertTextFormat.Snippet,
            documentation: 'Fixed array of strings: exactly N strings, each up to M bytes.',
          }
        );
      }
      return optItems;
    }
    return [];
  }

  // ── 2. option <name> ── suggest context-appropriate option names ─────────
  if (/^\s*option\s+$/.test(lineUpToCursor)) {
    const scope = optionScopeAt(inMessage, inOneof, inEnum);
    return OPTION_NAMES[scope].map(opt => ({
      label: opt,
      kind: CompletionItemKind.Property,
      detail: `${scope === 'file' ? 'File' : scope.charAt(0).toUpperCase() + scope.slice(1)} option`,
      documentation: { kind: MarkupKind.Markdown, value: optionDoc(scope, opt) ?? '' }
    }));
  }

  // ── 4. option value completions ─────────────────────────────────────────
  if (/^\s*option\s+discriminator\s*=\s*$/.test(lineUpToCursor)) {
    return DISCRIMINATOR_MODES.map(v => ({
      label: v,
      kind: CompletionItemKind.EnumMember,
      detail: 'Discriminator mode',
      documentation: { kind: MarkupKind.Markdown, value: DISCRIMINATOR_DOCS[v] ?? '' },
      insertText: v
    }));
  }
  if (/^\s*option\s+(variable|is_envelope|envelope)\s*=\s*$/.test(lineUpToCursor)) {
    return [
      { label: 'true', kind: CompletionItemKind.Value },
      { label: 'false', kind: CompletionItemKind.Value }
    ];
  }
  if (/^\s*option\s+(msgid|pkgid)\s*=\s*$/.test(lineUpToCursor)) {
    const isMsgid = /msgid/.test(lineUpToCursor);
    if (isMsgid) {
      const parsedDoc = getOrParseDocument(params.textDocument.uri);
      const usedIds = new Set(parsedDoc.messages.map(m => parseInt(m.options['msgid'] ?? '-1', 10)).filter(n => !isNaN(n) && n >= 0));
      let nextFree = 1;
      while (usedIds.has(nextFree)) nextFree++;
      return [{ label: String(nextFree), kind: CompletionItemKind.Value, detail: 'Next available msgid' }];
    }
    return [{ label: '1', kind: CompletionItemKind.Value, detail: 'Enter a numeric ID' }];
  }
  if (/^\s*option\s+extensions_start\s*=\s*$/.test(lineUpToCursor)) {
    const parsedDoc = getOrParseDocument(params.textDocument.uri);
    const currentLine = params.position.line;
    const containingMsg = parsedDoc.messages
      .filter(m => m.line <= currentLine && currentLine <= (m.endLine ?? Infinity))
      .sort((a, b) => b.line - a.line)[0];
    if (containingMsg) {
      // Check if we're inside a oneof
      const containingOneof = containingMsg.oneofs.find(
        o => o.line <= currentLine && currentLine <= (o.endLine ?? Infinity)
      );
      const scopeTags = containingOneof
        ? containingOneof.fields.map(f => f.tag)
        : containingMsg.fields.map(f => f.tag);
      const extensionTags = scopeTags.filter(tag => tag >= 2);
      if (extensionTags.length > 0) {
        return extensionTags.map(tag => ({ label: String(tag), kind: CompletionItemKind.Value, detail: 'Existing extension field number' }));
      }
    }
    return [{ label: '2', kind: CompletionItemKind.Value, detail: 'Existing field number required' }];
  }
  if (/^\s*option\s+magic_bytes\s*=\s*$/.test(lineUpToCursor)) {
    return [
      {
        label: '"0xA3, 0x7F"',
        kind: CompletionItemKind.Value,
        detail: `Two hex bytes (${LIMITS.magicByte.min}–${LIMITS.magicByte.max} each)`,
        insertText: '"0x${1:A3}, 0x${2:7F}"',
        insertTextFormat: InsertTextFormat.Snippet,
      }
    ];
  }

  // ── 5. Suppress completions while naming a oneof block ──────────────────
  if (/^\s*oneof\s+/.test(lineUpToCursor)) {
    return [];
  }

  // ── 6. Field number suggestion (field declaration `Type name = `) ────────
  if ((inMessage || inOneof) && !inEnum && !/^\s*option\s+/.test(lineUpToCursor)) {
    if (/^\s*(repeated\s+)?[a-zA-Z_]\w*\s+[a-zA-Z_]\w*\s*=\s*$/.test(lineUpToCursor)) {
      const parsedDoc = getOrParseDocument(params.textDocument.uri);
      const currentLine = params.position.line;
      const containingMsg = parsedDoc.messages
        .filter(m => m.line <= currentLine && currentLine <= (m.endLine ?? Infinity))
        .sort((a, b) => b.line - a.line)[0]; // innermost (latest start)
      if (containingMsg) {
        const containingOneof = containingMsg.oneofs.find(
          oneof => oneof.line <= currentLine && currentLine <= (oneof.endLine ?? Infinity)
        );
        const usedTags = new Set<number>(containingOneof
          ? containingOneof.fields.map(f => f.tag)
          : containingMsg.fields.map(f => f.tag));
        let nextTag = 1;
        while (usedTags.has(nextTag)) nextTag++;
        return [{ label: String(nextTag), kind: CompletionItemKind.Value, detail: 'Next available field number', sortText: '0' }];
      }
    }
  }

  // ── 7. Inside enum ──────────────────────────────────────────────────────
  if (inEnum) {
    if (/^\s*[A-Za-z_]*$/.test(lineUpToCursor)) {
      const parsedDoc = getOrParseDocument(params.textDocument.uri);
      const currentLine = params.position.line;
      const containingEnum = parsedDoc.enums.find(
        e => e.line <= currentLine && currentLine <= (e.endLine ?? Infinity)
      );
      let nextVal = 0;
      if (containingEnum && containingEnum.values.length > 0) {
        nextVal = Math.max(...containingEnum.values.map(v => v.value)) + 1;
      }
      return [
        {
          label: `VALUE_NAME = ${nextVal};`,
          kind: CompletionItemKind.Snippet,
          detail: nextVal === 0 ? 'First enum value' : `Next enum value (${nextVal})`,
          insertText: `\${1:VALUE_NAME} = \${2:${nextVal}};`,
          insertTextFormat: InsertTextFormat.Snippet,
        }
      ];
    }
    return [];
  }

  // ── 7. Inside oneof ──────────────────────────────────────────────────────
  if (inOneof && !inEnum) {
    if (/^\s*(repeated\s+)?[a-zA-Z_]*$/.test(lineUpToCursor)) {
      const allDefs = getAllDefinitions(params.textDocument.uri);
      return [
        { label: 'option', kind: CompletionItemKind.Keyword },
        {
          label: 'string (fixed)',
          kind: CompletionItemKind.Snippet,
          detail: 'Fixed-size string field',
          insertText: 'string ${1:field_name} = ${2:1} [size=${3:16}];',
          insertTextFormat: InsertTextFormat.Snippet,
          documentation: 'Fixed-size UTF-8 string. Always uses exactly N bytes (padded with nulls).',
        },
        {
          label: 'string (variable)',
          kind: CompletionItemKind.Snippet,
          detail: 'Variable-size string field',
          insertText: 'string ${1:field_name} = ${2:1} [max_size=${3:64}];',
          insertTextFormat: InsertTextFormat.Snippet,
          documentation: 'Variable-length UTF-8 string. Stores up to N chars plus a 1-byte length prefix.',
        },
        ...PRIMITIVE_TYPES.map(t => ({
          label: t, kind: CompletionItemKind.TypeParameter,
          detail: 'Primitive type', documentation: PRIMITIVE_TYPE_DOCS[t]
        })),
        ...allDefs.messages.map(m => ({ label: m.name, kind: CompletionItemKind.Class, detail: 'Message type' })),
        ...allDefs.enums.map(e => ({ label: e.name, kind: CompletionItemKind.Enum, detail: 'Enum type' })),
        ...getCompileConfigCompletionItems(allDefs)
      ];
    }
    return [];
  }

  // ── 8. Inside message (not in oneof) ────────────────────────────────────
  if (inMessage && !inEnum) {
    if (/^\s*(repeated\s+)?[a-zA-Z_]*$/.test(lineUpToCursor)) {
      const allDefs = getAllDefinitions(params.textDocument.uri);
      return [
        { label: 'option', kind: CompletionItemKind.Keyword },
        {
          label: 'repeated <primitive>',
          kind: CompletionItemKind.Snippet,
          detail: 'Repeated primitive field (fixed or bounded array)',
          insertText: `repeated \${1|${FIXED_SIZE_PRIMITIVES.join(',')}|} \${2:field_name} = \${3:1} [\${4|size=4,max_size=16|}];`,
          insertTextFormat: InsertTextFormat.Snippet,
          documentation: `Array of primitive values. Use size= for a fixed count, or max_size= for a variable count (1-byte count prefix up to ${LIMITS.oneBytePrefixMax} elements, 2 bytes above).`,
        },
        {
          label: 'repeated string',
          kind: CompletionItemKind.Snippet,
          detail: 'Repeated string field (string array)',
          insertText: 'repeated string ${1:field_name} = ${2:1} [${3|max_size=10,size=10|}, element_size=${4:32}];',
          insertTextFormat: InsertTextFormat.Snippet,
          documentation: 'Array of strings. Requires size/max_size for the array count and element_size for each string byte limit.',
        },
        {
          label: 'repeated <message>',
          kind: CompletionItemKind.Snippet,
          detail: 'Repeated message field (message array)',
          insertText: 'repeated ${1:MessageType} ${2:field_name} = ${3:1} [${4|size=4,max_size=8|}];',
          insertTextFormat: InsertTextFormat.Snippet,
          documentation: `Array of nested message values. Use size= for a fixed count, or max_size= for a variable count (1-byte count prefix up to ${LIMITS.oneBytePrefixMax} elements, 2 bytes above).`,
        },
        {
          label: 'string (fixed)',
          kind: CompletionItemKind.Snippet,
          detail: 'Fixed-size string field',
          insertText: 'string ${1:field_name} = ${2:1} [size=${3:16}];',
          insertTextFormat: InsertTextFormat.Snippet,
          documentation: 'Fixed-size UTF-8 string. Always uses exactly N bytes (padded with nulls).',
        },
        {
          label: 'string (variable)',
          kind: CompletionItemKind.Snippet,
          detail: 'Variable-size string field',
          insertText: 'string ${1:field_name} = ${2:1} [max_size=${3:64}];',
          insertTextFormat: InsertTextFormat.Snippet,
          documentation: 'Variable-length UTF-8 string. Stores up to N chars plus a 1-byte length prefix.',
        },
        {
          label: 'oneof',
          kind: CompletionItemKind.Snippet,
          detail: 'Oneof union field',
          insertText: 'oneof ${1:name} {\n  ${2:TypeA} ${3:field_a} = ${4:1};\n  ${5:TypeB} ${6:field_b} = ${7:2};\n}',
          insertTextFormat: InsertTextFormat.Snippet,
        },
        {
          label: 'oneof (with discriminator)',
          kind: CompletionItemKind.Snippet,
          detail: 'Oneof union field with explicit discriminator option',
          insertText: `oneof \${1:name} {\n  option discriminator = \${2|${DISCRIMINATOR_MODES.join(',')}|};\n  \${3:TypeA} \${4:field_a} = \${5:1};\n  \${6:TypeB} \${7:field_b} = \${8:2};\n}`,
          insertTextFormat: InsertTextFormat.Snippet,
          documentation: 'auto: msgid if all variants have one, else field_order.\nmsgid: uint16 by message ID.\nfield_order: uint8 1-based index + companion enum.\nnone: no discriminator stored.',
        },
        {
          label: 'enum',
          kind: CompletionItemKind.Snippet,
          detail: 'Nested enum definition',
          insertText: 'enum ${1:EnumName} {\n  ${2:VALUE_A} = 0;\n  ${3:VALUE_B} = 1;\n}',
          insertTextFormat: InsertTextFormat.Snippet,
        },
        {
          label: 'message',
          kind: CompletionItemKind.Snippet,
          detail: 'Nested message definition',
          insertText: 'message ${1:NestedName} {\n  ${2:uint32} ${3:field_name} = 1;\n}',
          insertTextFormat: InsertTextFormat.Snippet,
        },
        {
          label: 'flatten field',
          kind: CompletionItemKind.Snippet,
          detail: 'Inline nested message fields into parent (flatten=true)',
          insertText: '${1:MessageType} ${2:field_name} = ${3:1} [flatten=true];',
          insertTextFormat: InsertTextFormat.Snippet,
          documentation: 'Inlines the fields of a nested message directly into this message. Field names must not collide with existing parent fields.\n\nNote: affects Python and GraphQL output only; no effect on C, C++, C#, TypeScript, or Rust.',
        },
        ...PRIMITIVE_TYPES.map(t => ({
          label: t, kind: CompletionItemKind.TypeParameter,
          detail: 'Primitive type', documentation: PRIMITIVE_TYPE_DOCS[t]
        })),
        ...allDefs.messages.map(m => ({ label: m.name, kind: CompletionItemKind.Class, detail: 'Message type' })),
        ...allDefs.enums.map(e => ({ label: e.name, kind: CompletionItemKind.Enum, detail: 'Enum type' })),
        ...getCompileConfigCompletionItems(allDefs)
      ];
    }
    return [];
  }

  // ── 9. File level ────────────────────────────────────────────────────────
  if (/^\s*[a-zA-Z_]*$/.test(lineUpToCursor)) {
    return [
      {
        label: 'package',
        kind: CompletionItemKind.Snippet,
        detail: 'Package declaration',
        insertText: 'package ${1:name};',
        insertTextFormat: InsertTextFormat.Snippet,
      },
      {
        label: 'import',
        kind: CompletionItemKind.Snippet,
        detail: 'Import statement',
        insertText: 'import "${1:path.sf}";',
        insertTextFormat: InsertTextFormat.Snippet,
      },
      {
        label: 'message',
        kind: CompletionItemKind.Snippet,
        detail: 'Message definition',
        insertText: 'message ${1:MessageName} {\n  option msgid = ${2:1};\n\n  ${3:uint32} ${4:field_name} = ${5:1};\n}',
        insertTextFormat: InsertTextFormat.Snippet,
      },
      {
        label: 'message (variable)',
        kind: CompletionItemKind.Snippet,
        detail: 'Variable-length message definition',
        insertText: 'message ${1:MessageName} {\n  option msgid = ${2:1};\n  option variable = true;\n\n  string ${3:name} = 1 [max_size=${4:64}];\n  repeated uint8 ${5:data} = 2 [max_size=${6:128}];\n}',
        insertTextFormat: InsertTextFormat.Snippet,
        documentation: 'Message with variable=true: arrays and strings only transmit used bytes (max_size fields), reducing bandwidth.',
      },
      {
        label: 'enum',
        kind: CompletionItemKind.Snippet,
        detail: 'Enum definition',
        insertText: 'enum ${1:EnumName} {\n  ${2:VALUE_A} = 0;\n  ${3:VALUE_B} = 1;\n}',
        insertTextFormat: InsertTextFormat.Snippet,
      },
      {
        label: 'envelope',
        kind: CompletionItemKind.Snippet,
        detail: 'Envelope message pattern',
        insertText: 'message ${1:PayloadA} {\n  option msgid = ${2:100};\n\n  ${3:uint8} ${4:field} = 1;\n}\n\nmessage ${5:Envelope} {\n  option msgid = ${6:200};\n  option is_envelope = true;\n\n  oneof command {\n    ${1:PayloadA} ${7:payload_a} = 1;\n  }\n}',
        insertTextFormat: InsertTextFormat.Snippet,
      },
      {
        label: 'option',
        kind: CompletionItemKind.Snippet,
        detail: 'File-level option (pkgid)',
        insertText: 'option pkgid = ${1:1};',
        insertTextFormat: InsertTextFormat.Snippet,
      },
    ];
  }

  return [];
});

// Go-to-Definition
connection.onDefinition((params: TextDocumentPositionParams): Definition | null => {
  const doc = documents.get(params.textDocument.uri);
  if (!doc) {
    connection.console.warn(`onDefinition: document not found: '${params.textDocument.uri}'`);
    return null;
  }

  const text = doc.getText();
  const lineText = text.split('\n')[params.position.line] || '';

  // Import path go-to-definition: click inside `import "path.sf"` string
  {
    const importMatch = lineText.match(/^\s*import\s+"([^"]+)"/);
    if (importMatch) {
      const quoteStart = lineText.indexOf('"');
      const quoteEnd = lineText.lastIndexOf('"');
      if (params.position.character > quoteStart && params.position.character <= quoteEnd) {
        const importUri = resolveImportUri(importMatch[1], params.textDocument.uri);
        return Location.create(importUri, Range.create(0, 0, 0, 0));
      }
    }
  }

  const wordInfo = getWordAtPosition(doc.getText(), params.position);
  if (!wordInfo) return null;

  const { word } = wordInfo;

  // Oneof name go-to-definition → navigate to generated companion enum files
  {
    const parsed = getOrParseDocument(params.textDocument.uri);
    for (const msg of parsed.messages) {
      const oneof = msg.oneofs.find(o => o.name === word);
      if (oneof) {
        const rawDisc = (oneof.options['discriminator'] ?? 'auto').replace(/"/g, '');
        if (rawDisc !== 'none') {
          const enumName = word.charAt(0).toUpperCase() + word.slice(1);
          const enumEntry = sfCompileConfig?.enums.find(e => e.name === enumName) ?? null;
          if (enumEntry) {
            const locs = findGeneratedFileLocations(enumName);
            if (locs.length === 1) return locs[0];
            if (locs.length > 1) return locs;
          }
        }
        return null;
      }
    }
  }

  // Only look up PascalCase identifiers (user-defined types)
  if (!/^[A-Z]/.test(word)) return null;

  connection.console.log(`onDefinition: looking up '${word}' in '${params.textDocument.uri}'`);

  function findDefinition(uri: string, visited = new Set<string>()): Location | null {
    if (visited.has(uri)) return null;
    visited.add(uri);

    const parsed = getOrParseDocument(uri);

    const msg = parsed.messages.find(m => m.name === word);
    if (msg) {
      return Location.create(uri, Range.create(msg.line, 0, msg.line, word.length + 8));
    }

    const enm = parsed.enums.find(e => e.name === word);
    if (enm) {
      return Location.create(uri, Range.create(enm.line, 0, enm.line, word.length + 5));
    }

    // Search enum values (e.g. SCREAMING_SNAKE_CASE members)
    for (const e of parsed.enums) {
      const val = e.values.find(v => v.name === word);
      if (val) {
        return Location.create(uri, Range.create(val.line, 0, val.line, word.length));
      }
    }

    for (const imp of parsed.imports) {
      const importUri = resolveImportUri(imp, uri);
      const result = findDefinition(importUri, visited);
      if (result) return result;
    }

    return null;
  }

  const sfLocation = findDefinition(params.textDocument.uri);

  // Determine context: are we on the declaration line itself, or referencing a type in a field?
  const isDeclaration = new RegExp(`^\\s*(message|enum)\\s+${word}\\b`).test(lineText);

  if (isDeclaration) {
    // On the declaration → peek all generated files (no .sf)
    const generatedLocations = findGeneratedFileLocations(word);
    if (generatedLocations.length === 0) {
      connection.console.warn(`onDefinition: no generated file locations found for declaration '${word}'.`);
      return null;
    }
    if (generatedLocations.length === 1) return generatedLocations[0];
    return generatedLocations;
  } else {
    // Field type reference → navigate to .sf definition only
    const result = sfLocation || findSfSourceLocation(word) || findEnumValueInCompileConfigSources(word);
    if (!result) {
      connection.console.warn(`onDefinition: could not resolve definition for '${word}' (not found in .sf files or compile config).`);
    }
    return result;
  }
});

function findElementLineInFile(filePath: string, elementName: string): number {
  try {
    const content = fs.readFileSync(filePath, 'utf-8');
    const lines = content.split('\n');

    // Use the unqualified name (strip leading namespace qualifiers like "ns::Name")
    const unqualified = elementName.includes('::')
      ? elementName.substring(elementName.lastIndexOf('::') + 2)
      : elementName;
    const escaped = unqualified.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

    // Prefer a line that looks like a definition (struct/class/enum/typedef/using)
    const defRe = new RegExp(`\\b(?:struct|class|enum(?:\\s+class)?|typedef|using)\\s+${escaped}\\b`);
    const defIdx = lines.findIndex(l => defRe.test(l));
    if (defIdx >= 0) return defIdx;

    // Fall back to any line containing the unqualified name as a whole word
    const re = new RegExp(`\\b${escaped}\\b`);
    const idx = lines.findIndex(l => re.test(l));
    return idx >= 0 ? idx : 0;
  } catch {
    return 0;
  }
}

function findSfSourceLocation(word: string): Location | null {
  if (!sfCompileConfig) {
    connection.console.warn(`findSfSourceLocation('${word}'): sfCompileConfig is not loaded.`);
    return null;
  }
  const entry = findInCompileConfig(word);
  if (!entry || !entry.source_file) {
    connection.console.log(`findSfSourceLocation('${word}'): no compile config entry found.`);
    return null;
  }
  const sourceDir = getCompileConfigSourceDir();
  if (!sourceDir) {
    connection.console.warn(`findSfSourceLocation('${word}'): could not determine source directory.`);
    return null;
  }
  const sourceFilePath = path.resolve(sourceDir, entry.source_file);
  try {
    if (!fs.statSync(sourceFilePath).isFile()) {
      connection.console.warn(`findSfSourceLocation('${word}'): '${sourceFilePath}' is not a file.`);
      return null;
    }
  } catch (err) {
    connection.console.error(`findSfSourceLocation('${word}'): cannot stat '${sourceFilePath}': ${err}`);
    return null;
  }
  const sourceUri = pathToFileURL(sourceFilePath).toString();
  const parsed = getOrParseDocument(sourceUri);
  const msg = parsed.messages.find(m => m.name === word);
  if (msg) return Location.create(sourceUri, Range.create(msg.line, 0, msg.line, word.length + 8));
  const enm = parsed.enums.find(e => e.name === word);
  if (enm) return Location.create(sourceUri, Range.create(enm.line, 0, enm.line, word.length + 5));
  connection.console.warn(`findSfSourceLocation('${word}'): definition not found in '${sourceFilePath}'.`);
  return null;
}

function findEnumValueInCompileConfigSources(word: string): Location | null {
  if (!sfCompileConfig) return null;
  const sourceDir = getCompileConfigSourceDir();
  if (!sourceDir) return null;
  const seenFiles = new Set<string>();
  for (const enumEntry of sfCompileConfig.enums) {
    if (!enumEntry.source_file) continue;
    const sourceFilePath = path.resolve(sourceDir, enumEntry.source_file);
    if (seenFiles.has(sourceFilePath)) continue;
    seenFiles.add(sourceFilePath);
    try {
      if (!fs.statSync(sourceFilePath).isFile()) continue;
    } catch {
      continue;
    }
    const sourceUri = pathToFileURL(sourceFilePath).toString();
    const parsed = getOrParseDocument(sourceUri);
    for (const e of parsed.enums) {
      const val = e.values.find(v => v.name === word);
      if (val) {
        return Location.create(sourceUri, Range.create(val.line, 0, val.line, word.length));
      }
    }
  }
  return null;
}

function findGeneratedFileLocations(word: string): Location[] {
  if (!sfCompileConfig) {
    connection.console.warn(`findGeneratedFileLocations('${word}'): sfCompileConfig is not loaded.`);
    return [];
  }
  const entry = findInCompileConfig(word);
  if (!entry) {
    connection.console.log(`findGeneratedFileLocations('${word}'): no compile config entry found.`);
    return [];
  }
  const sourceDir = getCompileConfigSourceDir();
  if (!sourceDir) {
    connection.console.warn(`findGeneratedFileLocations('${word}'): could not determine source directory.`);
    return [];
  }
  const locations: Location[] = [];
  const seen = new Set<string>();
  for (const fileEntry of Object.values(entry.generated_files)) {
    if (!fileEntry?.path) continue;
    const absPath = path.resolve(sourceDir, fileEntry.path);
    if (seen.has(absPath)) continue;
    seen.add(absPath);
    try {
      if (!fs.statSync(absPath).isFile()) {
        connection.console.warn(`findGeneratedFileLocations('${word}'): '${absPath}' is not a file, skipping.`);
        continue;
      }
    } catch (err) {
      connection.console.error(`findGeneratedFileLocations('${word}'): cannot stat '${absPath}': ${err}`);
      continue;
    }
    const fileUri = pathToFileURL(absPath).toString();
    const line = findElementLineInFile(absPath, fileEntry.element);
    locations.push(Location.create(fileUri, Range.create(line, 0, line, fileEntry.element.length)));
  }
  if (locations.length === 0) {
    connection.console.warn(`findGeneratedFileLocations('${word}'): no generated files found on disk.`);
  }
  return locations;
}

function buildCompileInfoMarkdown(entry: SfCompileEntry): string {
  const toHex = (b: number) => `0x${b.toString(16).toUpperCase().padStart(2, '0')}`;
  const lines: string[] = [];
  if (entry.magic_bytes) {
    const [b1, b2] = entry.magic_bytes;
    lines.push(`**Checksum seed (magic bytes):** \`${toHex(b1)}, ${toHex(b2)}\``);
  }
  if (entry.max_size !== undefined) {
    if (entry.is_variable) {
      const minStr = entry.min_size !== undefined ? `${entry.min_size}` : '?';
      lines.push(`**Size:** ${minStr}–${entry.max_size} bytes (variable)`);
    } else if (entry.base_size !== undefined && entry.base_size !== entry.max_size) {
      lines.push(`**Size:** ${entry.base_size} bytes (base), ${entry.max_size} bytes (with extensions)`);
    } else {
      lines.push(`**Size:** ${entry.max_size} bytes`);
    }
  }
  if (lines.length === 0) return '';
  return `\n\n${lines.join('\n\n')}`;
}

function buildGeneratedFilesMarkdown(entry: SfCompileEntry): string {
  const files = entry.generated_files;
  const lines = Object.entries(files)
    .filter(([, v]) => v)
    .map(([lang, info]) => {
      const detail = info!.namespace
        ? `\`${info!.element}\` (ns: \`${info!.namespace}\`)`
        : `\`${info!.element}\``;
      return `- **${lang}**: \`${info!.path}\` — ${detail}`;
    });
  if (lines.length === 0) return '';
  const encodedArgs = encodeURIComponent(JSON.stringify([{ name: entry.name }]));
  const peekLink = `[Peek generated files](command:structFrameLs.showGeneratedFiles?${encodedArgs})`;
  return `\n\n---\n**Generated files** (source: \`${entry.source_file}\`) — ${peekLink}\n${lines.join('\n')}`;
}

// Hover
connection.onHover((params: TextDocumentPositionParams): Hover | null => {
  const doc = documents.get(params.textDocument.uri);
  if (!doc) return null;

  const wordInfo = getWordAtPosition(doc.getText(), params.position);
  if (!wordInfo) return null;

  const { word } = wordInfo;

  // Import path hover: hovering inside `import "path.sf"` string
  {
    const lineText = doc.getText().split('\n')[params.position.line] || '';
    const importMatch = lineText.match(/^\s*import\s+"([^"]+)"/);
    if (importMatch) {
      const quoteStart = lineText.indexOf('"');
      const quoteEnd = lineText.lastIndexOf('"');
      if (params.position.character > quoteStart && params.position.character <= quoteEnd) {
        const importPath = importMatch[1];
        const importUri = resolveImportUri(importPath, params.textDocument.uri);
        try {
          const importedDoc = getOrParseDocument(importUri);
          const msgList = importedDoc.messages.map(m => `- **message** \`${m.name}\``).join('\n');
          const enumList = importedDoc.enums.map(e => `- **enum** \`${e.name}\``).join('\n');
          const pkgLine = importedDoc.packageName ? `**package** \`${importedDoc.packageName}\`\n\n` : '';
          const body = [msgList, enumList].filter(Boolean).join('\n') || '*No top-level messages or enums*';
          return { contents: { kind: MarkupKind.Markdown, value: `${pkgLine}**\`${importPath}\`**\n\n${body}` } };
        } catch {
          return { contents: { kind: MarkupKind.Markdown, value: `Import: \`${importPath}\`` } };
        }
      }
    }
  }

  // Option name hover (e.g. hovering over `msgid` in `option msgid = 1;`)
  {
    const lineText = doc.getText().split('\n')[params.position.line] || '';
    const optMatch = lineText.match(/^\s*option\s+(\w+)\s*=/);
    if (optMatch && word === optMatch[1]) {
      const { inMessage, inOneof, inEnum } = getContextAtLine(doc.getText(), params.position.line);
      const hover = optionHover(optionScopeAt(inMessage, inOneof, inEnum), word);
      if (hover) {
        return { contents: { kind: MarkupKind.Markdown, value: hover } };
      }
    }
  }

  // Discriminator value hover (e.g. hovering over "auto" in `option discriminator = "auto";`)
  {
    const lineText = doc.getText().split('\n')[params.position.line] || '';
    if (/option\s+discriminator\s*=/.test(lineText)) {
      const mode = normalizeDiscriminator(word);
      if (mode && DISCRIMINATOR_DOCS[mode]) {
        const alias = mode !== word ? ` — same as \`${mode}\`` : '';
        return { contents: { kind: MarkupKind.Markdown, value: `**${word}** *(discriminator mode)*${alias}\n\n${DISCRIMINATOR_DOCS[mode]}` } };
      }
    }
  }

  // Field option name hover (e.g. hovering over `size` inside `[size=16]`)
  {
    const lineText = doc.getText().split('\n')[params.position.line] || '';
    const bracketStart = lineText.lastIndexOf('[', params.position.character);
    const bracketEnd = lineText.indexOf(']', params.position.character);
    if (bracketStart >= 0 && (bracketEnd < 0 || bracketEnd > bracketStart)) {
      const hover = optionHover('field', word);
      if (hover) {
        return { contents: { kind: MarkupKind.Markdown, value: hover } };
      }
    }
  }

  // Field tag number or enum value number hover
  if (/^\d+$/.test(word)) {
    const lineText = doc.getText().split('\n')[params.position.line] || '';
    // Field tag: `Type fieldname = N;` or `repeated Type fieldname = N [opts];`
    const fieldTagMatch = parser.matchFieldDeclaration(lineText);
    if (fieldTagMatch && params.position.character >= fieldTagMatch.tagStart && params.position.character < fieldTagMatch.tagEnd) {
      const tag = fieldTagMatch.tag;
      return {
        contents: {
          kind: MarkupKind.Markdown,
          value: `**Field number ${tag}**\n\nField numbers run 1..N in declaration order within a message; each oneof numbers its variants 1..M on its own. The wire layout follows declaration order.`
        }
      };
    }
    // Enum value: `VALUE_NAME = N;`
    const enumValMatch = lineText.match(/^\s*[A-Za-z][A-Za-z0-9_]*\s*=\s*(\d+)\s*;/);
    if (enumValMatch && enumValMatch[1] === word) {
      const val = parseInt(word, 10);
      return {
        contents: {
          kind: MarkupKind.Markdown,
          value: `**Enum value ${val}** (0x${val.toString(16).toUpperCase().padStart(2, '0')})\n\nStored as \`uint8\` (1 byte). Valid range: ${ENUM_VALUE_RANGE.min}–${ENUM_VALUE_RANGE.max}.`
        }
      };
    }
  }

  // Primitive type hover
  if (isPrimitive(word)) {
    return {
      contents: {
        kind: MarkupKind.Markdown,
        value: `**${word}** (primitive type)\n\n${PRIMITIVE_TYPE_DOCS[word] ?? ''}`
      }
    };
  }

  // User-defined type hover
  if (/^[A-Z]/.test(word)) {
    const text = doc.getText();
    const lineText = text.split('\n')[params.position.line] || '';
    const isDeclaration = new RegExp(`^\\s*(message|enum)\\s+${word}\\b`).test(lineText);
    const allDefs = getAllDefinitions(params.textDocument.uri);

    const msg = allDefs.messages.find(m => m.name === word);
    if (msg) {
      const compileEntry = findInCompileConfig(word);
      const compileInfo = compileEntry ? buildCompileInfoMarkdown(compileEntry) : '';
      const generatedSection = compileEntry ? buildGeneratedFilesMarkdown(compileEntry) : '';
      if (isDeclaration) {
        // On the declaration line — just show compile info and generated files, no redundant struct body
        return {
          contents: {
            kind: MarkupKind.Markdown,
            value: `**message ${word}**${compileInfo}${generatedSection}`
          }
        };
      }
      const fieldLines = msg.fields.map(f => `  ${f.repeated ? 'repeated ' : ''}${f.type} ${f.name} = ${f.tag}${f.optionsRaw ? ` [${f.optionsRaw}]` : ''};`).join('\n');
      const optLines = Object.entries(msg.options).map(([k, v]) => `  option ${k} = ${v};`).join('\n');
      const body = [optLines, fieldLines].filter(Boolean).join('\n');
      return {
        contents: {
          kind: MarkupKind.Markdown,
          value: `**message ${word}**\n\`\`\`sf\nmessage ${word} {\n${body}\n}\n\`\`\`${compileInfo}${generatedSection}`
        }
      };
    }

    const enm = allDefs.enums.find(e => e.name === word);
    if (enm) {
      const compileEntry = findInCompileConfig(word);
      const generatedSection = compileEntry ? buildGeneratedFilesMarkdown(compileEntry) : '';
      if (isDeclaration) {
        return {
          contents: {
            kind: MarkupKind.Markdown,
            value: `**enum ${word}**${enm.parentMessage ? ` (nested in \`${enm.parentMessage}\`)` : ''}${generatedSection}`
          }
        };
      }
      const enumOptionLines = Object.entries(enm.options ?? {}).map(([key, value]) => `  option ${key} = ${value};`).join('\n');
      const valueLines = enm.values.map(v => `  ${v.name} = ${v.value};`).join('\n');
      const enumBody = [enumOptionLines, valueLines].filter(Boolean).join('\n');
      return {
        contents: {
          kind: MarkupKind.Markdown,
          value: `**enum ${word}**${enm.parentMessage ? ` (nested in \`${enm.parentMessage}\`)` : ''}\n\`\`\`sf\nenum ${word} {\n${enumBody}\n}\n\`\`\`${generatedSection}`
        }
      };
    }

    // Not found via imports - check compile config for cross-file types
    const compileEntry = findInCompileConfig(word);
    if (compileEntry) {
      const compileInfo = buildCompileInfoMarkdown(compileEntry);
      const generatedSection = buildGeneratedFilesMarkdown(compileEntry);
      const kind = isEnumInCompileConfig(word) ? 'enum' : 'message';
      const parentNote = compileEntry.parent_message ? ` (nested in \`${compileEntry.parent_message}\`)` : '';
      return {
        contents: {
          kind: MarkupKind.Markdown,
          value: `**${kind} ${word}** (package: \`${compileEntry.package}\`)${parentNote}${compileInfo}${generatedSection}`
        }
      };
    }
  }

  // Oneof name hover — show generated discriminator enum
  {
    const parsed = getOrParseDocument(params.textDocument.uri);
    for (const msg of parsed.messages) {
      const oneof = msg.oneofs.find(o => o.name === word);
      if (!oneof) continue;

      const rawDisc = (oneof.options['discriminator'] ?? 'auto').replace(/"/g, '');
      const enumName = word.charAt(0).toUpperCase() + word.slice(1);

      // Look up the companion enum in the compile config (generated for field_order/auto)
      const compileEntry = sfCompileConfig?.enums.find(e => e.name === enumName) ?? null;
      const generatedSection = compileEntry ? buildGeneratedFilesMarkdown(compileEntry) : '';

      // Look up oneof info from the parent message compile entry
      const msgCompileEntry = sfCompileConfig?.messages.find(m => m.name === msg.name) ?? null;
      const oneofInfo = msgCompileEntry?.oneofs?.find(o => o.name === word) ?? null;
      const oneofInfoLines: string[] = [];
      if (oneofInfo) {
        if (oneofInfo.variable) oneofInfoLines.push('variable: `true`');
        if (oneofInfo.size !== undefined) {
          const hasMinOverride = oneofInfo.min_size_override != null;
          if (oneofInfo.variable && hasMinOverride) {
            oneofInfoLines.push(`size: ${oneofInfo.min_size_override}–${oneofInfo.size} bytes`);
          } else {
            oneofInfoLines.push(`size: ${oneofInfo.size} bytes`);
          }
        }
        if (oneofInfo.min_size_override != null)
          oneofInfoLines.push(`min_size: ${oneofInfo.min_size_override}`);
        if (oneofInfo.max_size_override != null)
          oneofInfoLines.push(`max_size: ${oneofInfo.max_size_override}`);
      }
      const oneofInfoSection = oneofInfoLines.length ? `\n\n${oneofInfoLines.map(l => `- ${l}`).join('\n')}` : '';

      if (rawDisc === 'none') {
        return {
          contents: {
            kind: MarkupKind.Markdown,
            value: `**oneof ${word}** (in \`${msg.name}\`)\n\ndiscriminator: \`none\` — no companion enum generated${oneofInfoSection}`
          }
        };
      }

      if (rawDisc === 'msgid') {
        const allDefs = getAllDefinitions(params.textDocument.uri);
        const variantLines = oneof.fields.map(f => {
          const variantMsg = allDefs.messages.find(m => m.name === f.type);
          const id = variantMsg?.options['msgid'] ?? '?';
          return `  // msgid ${id}\n  ${f.type} ${f.name};`;
        }).join('\n');
        return {
          contents: {
            kind: MarkupKind.Markdown,
            value: `**oneof ${word}** (in \`${msg.name}\`)\n\ndiscriminator: \`msgid\` (uint16)\n\n\`\`\`sf\noneof ${word} {\n${variantLines}\n}\n\`\`\`${oneofInfoSection}${generatedSection}`
          }
        };
      }

      // field_order or auto — build 1-based companion enum
      let effectiveMode = rawDisc;
      if (rawDisc === 'auto') {
        const allDefs = getAllDefinitions(params.textDocument.uri);
        const allHaveMsgid = oneof.fields.every(f => {
          const vm = allDefs.messages.find(m => m.name === f.type);
          return !!vm?.options['msgid'];
        });
        effectiveMode = allHaveMsgid ? 'msgid' : 'field_order';
        // If auto resolves to msgid, re-render as msgid
        if (effectiveMode === 'msgid') {
          const variantLines = oneof.fields.map(f => {
            const variantMsg = allDefs.messages.find(m => m.name === f.type);
            const id = variantMsg?.options['msgid'] ?? '?';
            return `  // msgid ${id}\n  ${f.type} ${f.name};`;
          }).join('\n');
          return {
            contents: {
              kind: MarkupKind.Markdown,
              value: `**oneof ${word}** (in \`${msg.name}\`)\n\ndiscriminator: \`auto\` → \`msgid\` (uint16)\n\n\`\`\`sf\noneof ${word} {\n${variantLines}\n}\n\`\`\`${oneofInfoSection}${generatedSection}`
            }
          };
        }
      }

      // field_order: generate 1-based companion enum
      const valueLines = oneof.fields.map((f, idx) =>
        `  ${f.name.replace(/([a-z])([A-Z])/g, '$1_$2').toUpperCase()} = ${idx + 1};`
      ).join('\n');
      return {
        contents: {
          kind: MarkupKind.Markdown,
          value: `**oneof ${word}** (in \`${msg.name}\`)\n\ndiscriminator: \`${rawDisc}\`${rawDisc === 'auto' ? ' → `field_order`' : ''} (uint8)\n\n**Generated companion enum:**\n\`\`\`sf\nenum ${enumName} {\n${valueLines}\n}\n\`\`\`${oneofInfoSection}${generatedSection}`
        }
      };
    }
  }

  // Field name hover — show type, tag, and options inline
  {
    const lineText = doc.getText().split('\n')[params.position.line] || '';
    const fieldMatch = parser.matchFieldDeclaration(lineText);
    if (fieldMatch && word === fieldMatch.name && params.position.character >= fieldMatch.nameStart && params.position.character < fieldMatch.nameEnd) {
      const repeated = fieldMatch.repeated;
      const type = fieldMatch.type;
      const tag = String(fieldMatch.tag);
      const opts = fieldMatch.optionsRaw ? `  // [${fieldMatch.optionsRaw}]` : '';
      const typeLabel = repeated ? `repeated ${type}` : type;
      const sizeNotes: string[] = [];
      if (fieldMatch.optionsRaw) {
        const parsedOpts = parseFieldOptions(fieldMatch.optionsRaw);
        if (parsedOpts['size']) sizeNotes.push(`fixed size: **${parsedOpts['size']}** bytes/elements`);
        if (parsedOpts['max_size']) sizeNotes.push(`max size: **${parsedOpts['max_size']}** (+ count prefix)`);
        if (parsedOpts['element_size']) sizeNotes.push(`element size: **${parsedOpts['element_size']}** bytes each`);
        if (isTrueValue(parsedOpts['flatten'])) sizeNotes.push('fields flattened into parent');
        if (parsedOpts['default']) sizeNotes.push(`default: **${parsedOpts['default']}**`);
      }
      const notes = sizeNotes.length ? `\n\n${sizeNotes.map(n => `- ${n}`).join('\n')}` : '';
      return {
        contents: {
          kind: MarkupKind.Markdown,
          value: `**${word}** *(field)*\n\`\`\`sf\n${typeLabel} ${word} = ${tag};${opts}\n\`\`\`${notes}`
        }
      };
    }
  }

  // Keyword hover — brief docs for language keywords
  if (KEYWORD_DOCS[word]) {
    return { contents: { kind: MarkupKind.Markdown, value: KEYWORD_DOCS[word] } };
  }

  return null;
});

// Document Symbols
connection.onDocumentSymbol((params): DocumentSymbol[] => {
  const doc = documents.get(params.textDocument.uri);
  if (!doc) return [];

  const parsed = getOrParseDocument(params.textDocument.uri);
  const symbols: DocumentSymbol[] = [];

  const msgSymbolMap = new Map<string, DocumentSymbol>();
  for (const msg of parsed.messages) {
    const msgRange = Range.create(msg.line, 0, msg.endLine + 1, 0);
    const fieldSymbols: DocumentSymbol[] = msg.fields.map(f => ({
      name: f.name,
      detail: `${f.repeated ? 'repeated ' : ''}${f.type}`,
      kind: SymbolKind.Field,
      range: Range.create(f.line, 0, f.line + 1, 0),
      selectionRange: Range.create(f.line, 0, f.line, f.name.length)
    }));
    const oneofSymbols: DocumentSymbol[] = msg.oneofs.map(o => ({
      name: o.name,
      detail: 'oneof',
      kind: SymbolKind.Namespace,
      range: Range.create(o.line, 0, o.endLine + 1, 0),
      selectionRange: Range.create(o.line, 0, o.line, o.name.length),
      children: o.fields.map(f => ({
        name: f.name,
        detail: f.type,
        kind: SymbolKind.Field,
        range: Range.create(f.line, 0, f.line + 1, 0),
        selectionRange: Range.create(f.line, 0, f.line, f.name.length)
      }))
    }));
    const msgSymbol: DocumentSymbol = {
      name: msg.name,
      kind: SymbolKind.Class,
      range: msgRange,
      selectionRange: Range.create(msg.line, 0, msg.line, msg.name.length + 8),
      children: [...fieldSymbols, ...oneofSymbols]
    };
    msgSymbolMap.set(msg.name, msgSymbol);
    symbols.push(msgSymbol);
  }

  for (const enm of parsed.enums) {
    const enumRange = Range.create(enm.line, 0, enm.endLine + 1, 0);
    const enumSymbol: DocumentSymbol = {
      name: enm.name,
      kind: SymbolKind.Enum,
      range: enumRange,
      selectionRange: Range.create(enm.line, 0, enm.line, enm.name.length + 5),
      children: enm.values.map(v => ({
        name: v.name,
        detail: `= ${v.value}`,
        kind: SymbolKind.EnumMember,
        range: Range.create(v.line, 0, v.line + 1, 0),
        selectionRange: Range.create(v.line, 0, v.line, v.name.length)
      }))
    };
    if (enm.parentMessage) {
      const parentSymbol = msgSymbolMap.get(enm.parentMessage);
      if (parentSymbol) {
        parentSymbol.children!.push(enumSymbol);
        continue;
      }
    }
    symbols.push(enumSymbol);
  }

  return symbols;
});

// ── Code Actions (Quick-Fixes) ─────────────────────────────────────────────
connection.onCodeAction((params: CodeActionParams): CodeAction[] => {
  const doc = documents.get(params.textDocument.uri);
  if (!doc) return [];

  const actions: CodeAction[] = [];

  for (const diag of params.context.diagnostics) {
    if (diag.source !== 'struct-frame') continue;
    const data = diag.data as Record<string, unknown> | undefined;
    if (!data) continue;

    const lineNum = diag.range.start.line;
    const lineText = doc.getText().split('\n')[lineNum] ?? '';

    if (data.fix === 'remove_default') {
      const tokenStart = typeof data.tokenStart === 'number' ? data.tokenStart : diag.range.start.character;
      const tokenEnd = typeof data.tokenEnd === 'number' ? data.tokenEnd : diag.range.end.character;
      const onlyOption = data.onlyOption === true;
      const bracketStart = typeof data.bracketStart === 'number' ? data.bracketStart : tokenStart;
      const bracketEnd = typeof data.bracketEnd === 'number' ? data.bracketEnd : tokenEnd;
      let editRange: Range;
      if (onlyOption) {
        const start = bracketStart > 0 && lineText[bracketStart - 1] === ' ' ? bracketStart - 1 : bracketStart;
        editRange = Range.create(lineNum, start, lineNum, bracketEnd + 1);
      } else if (lineText[tokenEnd] === ',') {
        editRange = Range.create(lineNum, tokenStart, lineNum, tokenEnd + 1);
      } else if (tokenStart > 0 && lineText[tokenStart - 1] === ',') {
        editRange = Range.create(lineNum, tokenStart - 1, lineNum, tokenEnd);
      } else {
        editRange = Range.create(lineNum, tokenStart, lineNum, tokenEnd);
      }
      actions.push({
        title: 'Remove [default = ...]',
        kind: CodeActionKind.QuickFix,
        diagnostics: [diag],
        edit: {
          changes: {
            [params.textDocument.uri]: [TextEdit.del(editRange)]
          }
        }
      });
    }

    if (data.fix === 'add_size') {
      // Strip semicolon from end so we can append before it
      const trimmedLine = lineText.trimEnd();
      const hasSemicolon = trimmedLine.endsWith(';');
      const insertPos = hasSemicolon
        ? Position.create(lineNum, trimmedLine.length - 1)
        : Position.create(lineNum, trimmedLine.length);

      for (const [label, snippet] of [
        ['Add [size=16]', ' [size=16]'],
        ['Add [max_size=64]', ' [max_size=64]'],
      ] as [string, string][]) {
        const edit: WorkspaceEdit = {
          changes: {
            [params.textDocument.uri]: [
              TextEdit.insert(insertPos, snippet)
            ]
          }
        };
        actions.push({
          title: label,
          kind: CodeActionKind.QuickFix,
          diagnostics: [diag],
          edit,
        });
      }
    }

    if (data.fix === 'add_element_size') {
      // Field already has [size=...] or [max_size=...]; insert element_size after it
      const closingBracket = lineText.lastIndexOf(']');
      if (closingBracket >= 0) {
        const insertPos = Position.create(lineNum, closingBracket);
        const edit: WorkspaceEdit = {
          changes: {
            [params.textDocument.uri]: [
              TextEdit.insert(insertPos, ', element_size=32')
            ]
          }
        };
        actions.push({
          title: 'Add [element_size=32]',
          kind: CodeActionKind.QuickFix,
          diagnostics: [diag],
          edit,
        });
      } else {
        // No bracket at all — append before semicolon
        const trimmedLine = lineText.trimEnd();
        const insertPos = trimmedLine.endsWith(';')
          ? Position.create(lineNum, trimmedLine.length - 1)
          : Position.create(lineNum, trimmedLine.length);
        const edit: WorkspaceEdit = {
          changes: {
            [params.textDocument.uri]: [
              TextEdit.insert(insertPos, ' [element_size=32]')
            ]
          }
        };
        actions.push({
          title: 'Add [element_size=32]',
          kind: CodeActionKind.QuickFix,
          diagnostics: [diag],
          edit,
        });
      }
    }

    if (data.fix === 'add_msgid') {
      const targetMsgName = (data as Record<string, unknown>).msgName as string | undefined;
      if (targetMsgName) {
        const parsedDoc = getOrParseDocument(params.textDocument.uri);
        const targetMsg = parsedDoc.messages.find(m => m.name === targetMsgName);
        if (targetMsg) {
          const usedIds = new Set(parsedDoc.messages
            .map(m => parseInt(m.options['msgid'] ?? '-1', 10))
            .filter(n => !isNaN(n) && n >= 0));
          let nextFree = 1;
          while (usedIds.has(nextFree)) nextFree++;
          const insertLine = targetMsg.line + 1;
          const edit: WorkspaceEdit = {
            changes: {
              [params.textDocument.uri]: [
                TextEdit.insert(Position.create(insertLine, 0), `  option msgid = ${nextFree};\n`)
              ]
            }
          };
          actions.push({
            title: `Add 'option msgid = ${nextFree}' to '${targetMsgName}'`,
            kind: CodeActionKind.QuickFix,
            diagnostics: [diag],
            edit,
          });
        }
      }
    }

    if (data.fix === 'add_msg_variable') {
      const targetMsgName = data.msgName as string | undefined;
      if (targetMsgName) {
        const parsedDoc = getOrParseDocument(params.textDocument.uri);
        const targetMsg = parsedDoc.messages.find(m => m.name === targetMsgName);
        if (targetMsg) {
          actions.push({
            title: `Add 'option variable = true' to '${targetMsgName}'`,
            kind: CodeActionKind.QuickFix,
            diagnostics: [diag],
            edit: {
              changes: {
                [params.textDocument.uri]: [
                  TextEdit.insert(Position.create(targetMsg.line + 1, 0), '  option variable = true;\n')
                ]
              }
            }
          });
        }
      }
    }

    if (data.fix === 'add_variable_true') {
      // Insert `option variable = true;` inside the message block — after the last
      // existing option line, or right after the opening brace if none.
      const msgLineNum = data.msgLine as number;
      const lines = doc.getText().split('\n');
      let insertAfter = msgLineNum;
      for (let i = msgLineNum + 1; i < lines.length; i++) {
        const t = lines[i].trimStart();
        if (t.startsWith('}')) break;
        if (t.startsWith('option ')) insertAfter = i;
        else if (t.length > 0 && !t.startsWith('//') && insertAfter === msgLineNum) break;
      }
      const edit: WorkspaceEdit = {
        changes: {
          [params.textDocument.uri]: [
            TextEdit.insert(Position.create(insertAfter + 1, 0), '  option variable = true;\n')
          ]
        }
      };
      actions.push({
        title: "Add 'option variable = true'",
        kind: CodeActionKind.QuickFix,
        diagnostics: [diag],
        edit,
      });
    }
  }

  return actions;
});

// ── Folding Ranges ─────────────────────────────────────────────────────────
connection.onFoldingRanges((params) => {
  const doc = documents.get(params.textDocument.uri);
  if (!doc) return [];

  const parsed = getOrParseDocument(params.textDocument.uri);
  const ranges: FoldingRange[] = [];

  for (const msg of parsed.messages) {
    if (msg.endLine > msg.line) {
      ranges.push(FoldingRange.create(msg.line, msg.endLine, undefined, undefined, FoldingRangeKind.Region));
    }
    for (const oneof of msg.oneofs) {
      if (oneof.endLine > oneof.line) {
        ranges.push(FoldingRange.create(oneof.line, oneof.endLine, undefined, undefined, FoldingRangeKind.Region));
      }
    }
    for (const nm of msg.nestedMessages) {
      if (nm.endLine > nm.line) {
        ranges.push(FoldingRange.create(nm.line, nm.endLine, undefined, undefined, FoldingRangeKind.Region));
      }
    }
  }

  for (const enm of parsed.enums) {
    if (enm.endLine > enm.line) {
      ranges.push(FoldingRange.create(enm.line, enm.endLine, undefined, undefined, FoldingRangeKind.Region));
    }
  }

  // Block comments
  const text = doc.getText();
  const blockCommentRe = /\/\*[\s\S]*?\*\//g;
  let match: RegExpExecArray | null;
  while ((match = blockCommentRe.exec(text)) !== null) {
    const startLine = doc.positionAt(match.index).line;
    const endLine = doc.positionAt(match.index + match[0].length).line;
    if (endLine > startLine) {
      ranges.push(FoldingRange.create(startLine, endLine, undefined, undefined, FoldingRangeKind.Comment));
    }
  }

  return ranges;
});

// ── Find References ────────────────────────────────────────────────────────
connection.onReferences((params) => {
  const doc = documents.get(params.textDocument.uri);
  if (!doc) return [];

  const wordInfo = getWordAtPosition(doc.getText(), params.position);
  if (!wordInfo || !/^[A-Z]/.test(wordInfo.word)) return [];
  const targetName = wordInfo.word;

  // Collect all open .sf documents + any referenced via compile config
  const urisToSearch = new Set<string>([params.textDocument.uri]);
  for (const [uri] of parsedDocuments) {
    if (uri.endsWith('.sf')) urisToSearch.add(uri);
  }
  if (sfCompileConfig) {
    const sourceDir = getCompileConfigSourceDir();
    const allEntries = [...sfCompileConfig.messages, ...(sfCompileConfig.nested_messages ?? []), ...sfCompileConfig.enums];
    for (const entry of allEntries) {
      if (entry.source_file) {
        const absPath = path.resolve(sourceDir, entry.source_file);
        if (fs.existsSync(absPath)) urisToSearch.add(pathToFileURL(absPath).toString());
      }
    }
  }

  const locations: Location[] = [];
  const fieldTypeRe = new RegExp(`\\b${targetName}\\b`);

  for (const uri of urisToSearch) {
    const parsed = getOrParseDocument(uri);
    for (const msg of parsed.messages) {
      for (const field of msg.fields) {
        if (field.type === targetName) {
          locations.push(Location.create(uri, Range.create(field.line, 0, field.line, 10000)));
        }
      }
      for (const oneof of msg.oneofs) {
        for (const field of oneof.fields) {
          if (field.type === targetName) {
            locations.push(Location.create(uri, Range.create(field.line, 0, field.line, 10000)));
          }
        }
      }
      for (const nm of msg.nestedMessages) {
        for (const field of nm.fields) {
          if (field.type === targetName) {
            locations.push(Location.create(uri, Range.create(field.line, 0, field.line, 10000)));
          }
        }
      }
    }
  }

  return locations;
});

// ── Workspace Symbols ──────────────────────────────────────────────────────
connection.onWorkspaceSymbol((params) => {
  const query = params.query.toLowerCase();
  const results: SymbolInformation[] = [];

  // Collect from all parsed documents + compile config source files
  const urisToSearch = new Set<string>();
  for (const [uri] of parsedDocuments) {
    if (uri.endsWith('.sf')) urisToSearch.add(uri);
  }
  if (sfCompileConfig && workspaceRoot) {
    const sourceDir = getCompileConfigSourceDir();
    const allEntries = [...sfCompileConfig.messages, ...(sfCompileConfig.nested_messages ?? []), ...sfCompileConfig.enums];
    for (const entry of allEntries) {
      if (entry.source_file) {
        const absPath = path.resolve(sourceDir, entry.source_file);
        if (fs.existsSync(absPath)) urisToSearch.add(pathToFileURL(absPath).toString());
      }
    }
  }

  for (const uri of urisToSearch) {
    const parsed = getOrParseDocument(uri);
    for (const msg of parsed.messages) {
      if (!query || msg.name.toLowerCase().includes(query)) {
        results.push({
          name: msg.name,
          kind: SymbolKind.Class,
          location: Location.create(uri, Range.create(msg.line, 0, msg.endLine + 1, 0)),
          containerName: parsed.packageName || undefined,
        });
      }
      for (const nm of msg.nestedMessages) {
        if (!query || nm.name.toLowerCase().includes(query)) {
          results.push({
            name: nm.name,
            kind: SymbolKind.Class,
            location: Location.create(uri, Range.create(nm.line, 0, nm.endLine + 1, 0)),
            containerName: msg.name,
          });
        }
      }
    }
    for (const enm of parsed.enums) {
      if (!query || enm.name.toLowerCase().includes(query)) {
        results.push({
          name: enm.name,
          kind: SymbolKind.Enum,
          location: Location.create(uri, Range.create(enm.line, 0, enm.endLine + 1, 0)),
          containerName: enm.parentMessage ?? parsed.packageName ?? undefined,
        });
      }
    }
  }

  return results;
});

// ── Rename ─────────────────────────────────────────────────────────────────
connection.onPrepareRename((params) => {
  const doc = documents.get(params.textDocument.uri);
  if (!doc) return null;

  const wordInfo = getWordAtPosition(doc.getText(), params.position);
  if (!wordInfo) return null;
  const { word, start, end } = wordInfo;

  // Only PascalCase identifiers (messages and enums can be renamed)
  if (!/^[A-Z]/.test(word)) return null;

  const allDefs = getAllDefinitions(params.textDocument.uri);
  const isKnown = allDefs.messages.some(m => m.name === word) || allDefs.enums.some(e => e.name === word);
  if (!isKnown) return null;

  return Range.create(params.position.line, start, params.position.line, end);
});

connection.onRenameRequest((params: RenameParams): WorkspaceEdit | null => {
  const doc = documents.get(params.textDocument.uri);
  if (!doc) return null;

  const wordInfo = getWordAtPosition(doc.getText(), params.position);
  if (!wordInfo) return null;
  const { word } = wordInfo;
  const newName = params.newName.trim();

  if (!/^[A-Z]/.test(word) || !/^[A-Z]/.test(newName)) return null;

  const urisToSearch = new Set<string>();
  const collectReachableDocuments = (uri: string, visited = new Set<string>()): void => {
    if (visited.has(uri)) return;
    visited.add(uri);
    urisToSearch.add(uri);
    const parsed = getOrParseDocument(uri);
    for (const importPath of parsed.imports) {
      const importUri = resolveImportUri(importPath, uri);
      const importFile = importUri.startsWith('file://') ? fileURLToPath(importUri) : importUri;
      if (fs.existsSync(importFile)) collectReachableDocuments(importUri, visited);
    }
  };
  collectReachableDocuments(params.textDocument.uri);

  const changes: Record<string, TextEdit[]> = {};

  for (const uri of urisToSearch) {
    const parsed = getOrParseDocument(uri);

    // Collect line numbers that reference this type
    const targetLines = new Set<number>();

    // Declaration lines (message/enum definition)
    parsed.messages.forEach(m => { if (m.name === word) targetLines.add(m.line); });
    parsed.enums.forEach(e => { if (e.name === word) targetLines.add(e.line); });

    // Field type references in all message scopes
    for (const msg of parsed.messages) {
      for (const field of msg.fields) {
        if (field.type === word) targetLines.add(field.line);
      }
      for (const oneof of msg.oneofs) {
        for (const field of oneof.fields) {
          if (field.type === word) targetLines.add(field.line);
        }
      }
      for (const nm of msg.nestedMessages) {
        for (const field of nm.fields) {
          if (field.type === word) targetLines.add(field.line);
        }
      }
    }

    if (targetLines.size === 0) continue;

    // Get content for this URI (prefer open document, fall back to disk)
    const content = (() => {
      const openDoc = documents.get(uri);
      if (openDoc) return openDoc.getText();
      try {
        const filePath = uri.startsWith('file://') ? fileURLToPath(uri) : uri;
        return fs.readFileSync(filePath, 'utf-8');
      } catch { return null; }
    })();
    if (!content) continue;

    const lines = content.split('\n');
    const edits: TextEdit[] = [];
    const wordRe = new RegExp(`\\b${word}\\b`, 'g');

    for (const lineNum of targetLines) {
      const lineText = lines[lineNum] ?? '';
      wordRe.lastIndex = 0;
      let match: RegExpExecArray | null;
      while ((match = wordRe.exec(lineText)) !== null) {
        edits.push(TextEdit.replace(
          Range.create(lineNum, match.index, lineNum, match.index + word.length),
          newName
        ));
      }
    }

    if (edits.length > 0) changes[uri] = edits;
  }

  return { changes };
});

documents.listen(connection);
connection.listen();
