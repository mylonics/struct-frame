/**
 * Shared MockTransport used by the C# SDK test suites.
 *
 * Extracted from TestSdkSubscribe.cs so multiple test files can share a single
 * implementation (the test project compiles all .cs files into a single exe;
 * defining MockTransport in more than one file would cause a duplicate-symbol
 * build error).
 */

#nullable enable

using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using StructFrame.Sdk;

/// <summary>
/// A minimal ITransport implementation for tests. Supports:
///   - Recording every byte[] handed to SendAsync (SentData)
///   - Injecting "received" data via InjectData (raises DataReceived)
///   - Optional gating: hold SendAsync until a manual reset event is signaled
///     (used by strict-ordering tests to force concurrent interleaving).
/// </summary>
class MockTransport : ITransport
{
  public bool IsConnected { get; private set; }

  public event EventHandler<byte[]>? DataReceived;
  public event EventHandler<Exception>? ErrorOccurred;
  public event EventHandler? ConnectionClosed;

  public List<byte[]> SentData { get; } = new();

  /// <summary>
  /// Optional gate: when set to a ManualResetEventSlim, every SendAsync call
  /// will wait until the gate is signaled. Useful to force overlapping sends.
  /// </summary>
  public ManualResetEventSlim? SendGate { get; set; }

  /// <summary>
  /// Optional exception to throw from SendAsync (next call only, then cleared).
  /// </summary>
  public Exception? NextSendThrows { get; set; }

  /// <summary>
  /// Optional callback invoked just before each SendAsync records the data.
  /// Useful to count how many sends are in flight at the same time.
  /// </summary>
  public Action<byte[]>? OnSend { get; set; }

  public Task ConnectAsync()
  {
    IsConnected = true;
    return Task.CompletedTask;
  }

  public Task DisconnectAsync()
  {
    IsConnected = false;
    ConnectionClosed?.Invoke(this, EventArgs.Empty);
    return Task.CompletedTask;
  }

  public async Task SendAsync(byte[] data)
  {
    if (SendGate != null)
    {
      // Yield first so callers can race up to this point before we block.
      await Task.Yield();
      SendGate.Wait();
    }

    if (NextSendThrows != null)
    {
      var ex = NextSendThrows;
      NextSendThrows = null;
      throw ex;
    }

    var copy = (byte[])data.Clone();
    OnSend?.Invoke(copy);
    lock (SentData)
    {
      SentData.Add(copy);
    }
  }

  public Task SendAsync(ReadOnlyMemory<byte> data) => SendAsync(data.ToArray());

  /// <summary>Simulates arriving data (e.g., received over the network).</summary>
  public void InjectData(byte[] data) => DataReceived?.Invoke(this, data);

  /// <summary>Raises the ErrorOccurred event with the given exception.</summary>
  public void InjectError(Exception ex) => ErrorOccurred?.Invoke(this, ex);

  /// <summary>Raises the ConnectionClosed event without changing IsConnected.</summary>
  public void InjectClose() => ConnectionClosed?.Invoke(this, EventArgs.Empty);
}
