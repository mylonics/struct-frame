// Minimal JSON-RPC client that drives the built language server over stdio.
// Not a test file itself (no .test suffix), shared by the *.test.ts files.
import assert = require('node:assert/strict');
import { spawn, ChildProcessWithoutNullStreams } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

export interface Diagnostic {
  message: string;
  severity?: number;
  range: { start: { line: number; character: number }; end: { line: number; character: number } };
}

type JsonRpcMessage = {
  id?: number;
  method?: string;
  result?: unknown;
  params?: { uri?: string; diagnostics?: Diagnostic[] };
};

/** editors/vscode */
export const EXTENSION_ROOT = resolve(__dirname, '..', '..', '..');
/** The struct-frame repository root. */
export const REPO_ROOT = resolve(EXTENSION_ROOT, '..', '..');

export interface LspClient {
  process: ChildProcessWithoutNullStreams;
  request: (method: string, params: unknown) => Promise<JsonRpcMessage>;
  notify: (method: string, params: unknown) => void;
  /** Open a file and resolve with the first diagnostics published for it. */
  open: (filePath: string) => Promise<{ uri: string; diagnostics: Diagnostic[] }>;
  close: () => void;
}

export async function startServer(rootPath: string = EXTENSION_ROOT): Promise<LspClient> {
  const serverPath = resolve(__dirname, '..', 'server.js');
  assert.equal(existsSync(serverPath), true, `server not built: ${serverPath}`);
  const server = spawn(process.execPath, [serverPath, '--stdio']);
  let buffer = Buffer.alloc(0);
  let nextId = 1;
  const responses = new Map<number, (message: JsonRpcMessage) => void>();
  const diagnosticWaiters = new Map<string, (diagnostics: Diagnostic[]) => void>();

  server.stdout.on('data', chunk => {
    buffer = Buffer.concat([buffer, chunk]);
    for (;;) {
      const separator = buffer.indexOf(Buffer.from('\r\n\r\n'));
      if (separator < 0) break;
      const header = buffer.subarray(0, separator).toString();
      const match = header.match(/Content-Length: (\d+)/);
      if (!match) break;
      const length = Number(match[1]);
      const bodyStart = separator + 4;
      if (buffer.length - bodyStart < length) break;
      const message = JSON.parse(buffer.subarray(bodyStart, bodyStart + length).toString()) as JsonRpcMessage;
      buffer = buffer.subarray(bodyStart + length);
      if (message.id !== undefined && message.method === undefined) {
        responses.get(message.id)?.(message);
        responses.delete(message.id);
      } else if (message.method === 'textDocument/publishDiagnostics' && message.params?.uri) {
        diagnosticWaiters.get(message.params.uri)?.(message.params.diagnostics ?? []);
        diagnosticWaiters.delete(message.params.uri);
      }
    }
  });

  const write = (message: unknown): void => {
    const body = Buffer.from(JSON.stringify(message));
    server.stdin.write(Buffer.concat([Buffer.from(`Content-Length: ${body.length}\r\n\r\n`), body]));
  };
  const request = (method: string, params: unknown): Promise<JsonRpcMessage> => new Promise(resolveResponse => {
    const id = nextId++;
    responses.set(id, resolveResponse);
    write({ jsonrpc: '2.0', id, method, params });
  });
  const notify = (method: string, params: unknown): void => write({ jsonrpc: '2.0', method, params });
  const open = (filePath: string): Promise<{ uri: string; diagnostics: Diagnostic[] }> => {
    const uri = pathToFileURL(filePath).href;
    const text = readFileSync(filePath, 'utf8');
    const published = new Promise<Diagnostic[]>(resolveDiagnostics => diagnosticWaiters.set(uri, resolveDiagnostics));
    notify('textDocument/didOpen', { textDocument: { uri, languageId: 'struct-frame', version: 1, text } });
    return published.then(diagnostics => ({ uri, diagnostics }));
  };

  const rootUri = pathToFileURL(rootPath).href;
  const initialize = await request('initialize', {
    processId: null,
    rootUri,
    capabilities: { workspace: { configuration: false, workspaceFolders: false } },
    workspaceFolders: [{ uri: rootUri, name: 'struct-frame' }]
  });
  assert.ok(initialize.result);
  notify('initialized', {});

  return { process: server, request, notify, open, close: () => server.kill() };
}
