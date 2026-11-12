import * as path from 'path';
import * as fs from 'fs';
import {
  workspace, ExtensionContext, ConfigurationTarget,
  Uri, commands, window, Location, Position,
  MarkdownString, Hover, Range, ViewColumn, Selection
} from 'vscode';
import {
  LanguageClient,
  LanguageClientOptions,
  ServerOptions,
  TransportKind,
  Middleware
} from 'vscode-languageclient/node';

let client: LanguageClient;

interface SfCompileGeneratedFileEntry {
  path: string;
  namespace: string | null;
  element: string;
  qualified_element: string;
}

interface SfCompileEntry {
  name: string;
  package: string;
  source_file: string;
  generated_files: Record<string, SfCompileGeneratedFileEntry>;
  parent_message?: string;
  msgid?: number | null;
  max_size?: number;
  base_size?: number;
  min_size?: number;
  is_variable?: boolean;
  is_envelope?: boolean;
  extensions_start?: number | null;
  magic_bytes?: [number, number] | null;
  oneofs?: Array<{
    name: string;
    size: number;
    base_size?: number;
    variable?: boolean;
    auto_discriminator?: boolean;
    discriminator_type?: string | null;
    min_size_override?: number | null;
    max_size_override?: number | null;
    variants?: Array<{ disc_val: number; field_name: string; field_size: number }>;
  }> | null;
}

interface SfCompileConfig {
  messages: SfCompileEntry[];
  nested_messages?: SfCompileEntry[];
  enums: SfCompileEntry[];
}

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
  const generatedFiles: Record<string, SfCompileGeneratedFileEntry> = {};
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

function getCompileConfigFsPath(): string | null {
  const config = workspace.getConfiguration('structFrameLs');
  const configPath = config.get<string>('compileConfigPath') || 'sf_compile.json';
  if (path.isAbsolute(configPath)) return configPath;
  const folders = workspace.workspaceFolders;
  if (folders && folders.length > 0) {
    return path.join(folders[0].uri.fsPath, configPath);
  }
  return null;
}

function readCompileConfig(fsPath: string): SfCompileConfig | null {
  try {
    return normalizeSfCompileConfig(JSON.parse(fs.readFileSync(fsPath, 'utf-8')));
  } catch {
    return null;
  }
}

function findLineInFile(fsPath: string, name: string): number {
  try {
    const re = new RegExp(`\\b${name}\\b`);
    const lines = fs.readFileSync(fsPath, 'utf-8').split('\n');
    const idx = lines.findIndex(l => re.test(l));
    return idx >= 0 ? idx : 0;
  } catch {
    return 0;
  }
}

function tryAutoSetCompileConfigPath(docUri: string): void {
  if (!path.basename(docUri).toLowerCase().endsWith('sf_compile.json')) return;

  const config = workspace.getConfiguration('structFrameLs');
  const current = config.inspect<string>('compileConfigPath');

  // Only auto-set if the user hasn't explicitly configured the path
  const hasUserValue =
    (current?.workspaceValue !== undefined && current.workspaceValue !== '') ||
    (current?.workspaceFolderValue !== undefined && current.workspaceFolderValue !== '');
  if (hasUserValue) return;

  // Compute a workspace-relative path if possible, otherwise store absolute
  const folders = workspace.workspaceFolders;
  let configPath = docUri.startsWith('file://') ? decodeURIComponent(docUri.replace(/^file:\/\/\/?/, '').replace(/\//g, path.sep)) : docUri;
  if (folders && folders.length > 0) {
    const root = folders[0].uri.fsPath;
    if (configPath.startsWith(root)) {
      configPath = path.relative(root, configPath);
    }
  }

  config.update('compileConfigPath', configPath, ConfigurationTarget.Workspace);
}

export function activate(context: ExtensionContext): void {
  const serverModule = context.asAbsolutePath(
    path.join('server', 'out', 'server.js')
  );

  const serverOptions: ServerOptions = {
    run: { module: serverModule, transport: TransportKind.ipc },
    debug: {
      module: serverModule,
      transport: TransportKind.ipc,
      options: { execArgv: ['--nolazy', '--inspect=6009'] }
    }
  };

  const middleware: Middleware = {
    provideHover: async (document, position, token, next) => {
      const hover = await next(document, position, token);
      if (!hover) return hover;
      const hasOurCommand = hover.contents.some(c => {
        const val = c instanceof MarkdownString ? c.value : typeof c === 'string' ? c : '';
        return val.includes('command:structFrameLs.');
      });
      if (!hasOurCommand) return hover;
      return new Hover(
        hover.contents.map(c => {
          const value = c instanceof MarkdownString ? c.value
            : typeof c === 'string' ? c
            : (c as { language: string; value: string }).value ?? '';
          const md = new MarkdownString(value);
          md.isTrusted = true;
          return md;
        }),
        hover.range
      );
    }
  };

  const clientOptions: LanguageClientOptions = {
    documentSelector: [{ scheme: 'file', language: 'struct-frame' }],
    synchronize: {
      fileEvents: [
        workspace.createFileSystemWatcher('**/*.sf'),
        workspace.createFileSystemWatcher('**/sf_compile.json')
      ],
      configurationSection: 'structFrameLs'
    },
    outputChannel: window.createOutputChannel('Struct Frame LS'),
    middleware
  };

  client = new LanguageClient(
    'struct-frame-ls',
    'Struct Frame LS',
    serverOptions,
    clientOptions
  );

  client.start();

  context.subscriptions.push(
    commands.registerCommand('structFrameLs.showGeneratedFiles', async (args: { name: string }) => {
      const configFsPath = getCompileConfigFsPath();
      if (!configFsPath) {
        window.showWarningMessage('Struct Frame: compile config path not configured.');
        return;
      }
      const config = readCompileConfig(configFsPath);
      if (!config) {
        window.showWarningMessage(`Struct Frame: could not read ${configFsPath}`);
        return;
      }
      const entry =
        config.messages.find(m => m.name === args.name) ||
        (config.nested_messages ?? []).find(m => m.name === args.name) ||
        config.enums.find(e => e.name === args.name);
      if (!entry) {
        window.showWarningMessage(`Struct Frame: no generated files found for ${args.name}`);
        return;
      }
      const configDir = path.dirname(configFsPath);

      interface LangItem {
        label: string;
        description: string;
        detail: string;
        absPath: string;
        element: string;
      }

      const items: LangItem[] = [];
      const seen = new Set<string>();
      for (const [lang, fileEntry] of Object.entries(entry.generated_files)) {
        if (!fileEntry?.path) continue;
        const absPath = path.isAbsolute(fileEntry.path) ? fileEntry.path : path.resolve(configDir, fileEntry.path);
        if (seen.has(absPath) || !fs.existsSync(absPath)) continue;
        seen.add(absPath);
        const nsLabel = fileEntry.namespace ? ` (${fileEntry.namespace})` : '';
        items.push({
          label: `$(symbol-class) ${lang.toUpperCase()}`,
          description: fileEntry.qualified_element,
          detail: `${fileEntry.path}${nsLabel}`,
          absPath,
          element: fileEntry.element
        });
      }

      if (items.length === 0) {
        window.showInformationMessage(`Struct Frame: no generated files exist on disk for ${args.name}`);
        return;
      }

      const picked = await window.showQuickPick(items, {
        title: `Generated files for ${args.name}`,
        placeHolder: 'Select language target to open'
      });
      if (!picked) return;

      const line = findLineInFile(picked.absPath, picked.element);
      const doc = await workspace.openTextDocument(Uri.file(picked.absPath));
      const editor = await window.showTextDocument(doc, ViewColumn.Beside);
      const pos = new Position(line, 0);
      editor.selection = new Selection(pos, pos);
      editor.revealRange(new Range(pos, pos));
    })
  );

  context.subscriptions.push(
    workspace.onDidOpenTextDocument(doc => {
      tryAutoSetCompileConfigPath(doc.uri.toString());
    })
  );
}

export function deactivate(): Thenable<void> | undefined {
  if (!client) {
    return undefined;
  }
  return client.stop();
}
