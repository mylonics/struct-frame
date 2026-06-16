/**
 * Request / response tests for the C# StructFrameSdk.RequestAsync.
 *
 * Uses MockTransport (defined in MockTransport.cs).  Responses are injected
 * via Task.Delay so they arrive after RequestAsync has parked its
 * TaskCompletionSource.
 *
 * Test matrix
 * -----------
 * - Basic request/response: RequestAsync resolves with the first response.
 * - Timeout: RequestAsync throws TimeoutException when no response arrives.
 * - match predicate: responses filtered by a correlation field.
 * - Concurrent requests: two in-flight requests resolve independently.
 * - Subscription cleanup: handler removed after success and after timeout.
 */

#nullable enable

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using StructFrame;
using StructFrame.Framing;
using StructFrame.Profiles;
using StructFrame.Sdk;
using StructFrame.SerializationTest;

// MockTransport and SdkTestHelpers are defined in MockTransport.cs / TestSdkSubscribe.cs.

static class TestSdkRequestResponse
{
    private static int _passed = 0;
    private static int _failed = 0;

    private static bool Assert(string name, bool condition)
    {
        Console.WriteLine($"  {(condition ? "PASS" : "FAIL")} {name}");
        if (condition) _passed++; else _failed++;
        return condition;
    }

    // -------------------------------------------------------------------------
    // Test 1: Basic request/response
    // -------------------------------------------------------------------------
    static async Task TestBasicRequestResponse()
    {
        var transport = new MockTransport();
        using var sdk = new StructFrameSdk(SdkTestHelpers.MakeConfig(transport));

        // Inject a response after a short delay so RequestAsync has a chance to park.
        var responseMsg = new BasicTypesMessage { RegularInt = 10, Flag = true };
        _ = Task.Run(async () =>
        {
            await Task.Delay(30);
            transport.InjectData(SdkTestHelpers.EncodeStandard(responseMsg));
        });

        var requestMsg = new BasicTypesMessage { RegularInt = 10 };
        var result = await sdk.RequestAsync<BasicTypesMessage, BasicTypesMessage>(requestMsg);

        Assert("basic: RequestAsync resolves", result != null);
        Assert("basic: Flag field correct", result?.Flag == true);
        Assert("basic: request was sent", transport.SentData.Count == 1);
    }

    // -------------------------------------------------------------------------
    // Test 2: Timeout
    // -------------------------------------------------------------------------
    static async Task TestTimeout()
    {
        var transport = new MockTransport();
        using var sdk = new StructFrameSdk(SdkTestHelpers.MakeConfig(transport));

        bool threw = false;
        try
        {
            var requestMsg = new BasicTypesMessage { RegularInt = 99 };
            await sdk.RequestAsync<BasicTypesMessage, BasicTypesMessage>(
                requestMsg, timeoutSeconds: 0.1f);
        }
        catch (TimeoutException)
        {
            threw = true;
        }

        Assert("timeout: TimeoutException thrown", threw);
        Assert("timeout: request was still sent", transport.SentData.Count == 1);
    }

    // -------------------------------------------------------------------------
    // Test 3: match predicate filters responses
    // -------------------------------------------------------------------------
    static async Task TestMatchPredicateFiltersResponses()
    {
        var transport = new MockTransport();
        using var sdk = new StructFrameSdk(SdkTestHelpers.MakeConfig(transport));

        // Inject a wrong response first, then the correct one.
        _ = Task.Run(async () =>
        {
            await Task.Delay(20);
            transport.InjectData(SdkTestHelpers.EncodeStandard(
                new BasicTypesMessage { RegularInt = 99, Flag = false }));
            await Task.Delay(30);
            transport.InjectData(SdkTestHelpers.EncodeStandard(
                new BasicTypesMessage { RegularInt = 7, Flag = true }));
        });

        var requestMsg = new BasicTypesMessage { RegularInt = 7 };
        var result = await sdk.RequestAsync<BasicTypesMessage, BasicTypesMessage>(
            requestMsg,
            match: r => r.RegularInt == 7,
            timeoutSeconds: 2f);

        Assert("match: non-matching response ignored", result != null);
        Assert("match: correct response returned", result?.RegularInt == 7);
        Assert("match: flag from matching response", result?.Flag == true);
    }

    // -------------------------------------------------------------------------
    // Test 4: Concurrent requests with match
    // -------------------------------------------------------------------------
    static async Task TestConcurrentRequestsWithMatch()
    {
        var transport = new MockTransport();
        using var sdk = new StructFrameSdk(SdkTestHelpers.MakeConfig(transport));

        // Start both requests, inject responses in reverse order.
        _ = Task.Run(async () =>
        {
            await Task.Delay(40);
            transport.InjectData(SdkTestHelpers.EncodeStandard(
                new BasicTypesMessage { RegularInt = 2, Flag = false }));
            transport.InjectData(SdkTestHelpers.EncodeStandard(
                new BasicTypesMessage { RegularInt = 1, Flag = true }));
        });

        var taskA = sdk.RequestAsync<BasicTypesMessage, BasicTypesMessage>(
            new BasicTypesMessage { RegularInt = 1 },
            match: r => r.RegularInt == 1,
            timeoutSeconds: 2f);
        var taskB = sdk.RequestAsync<BasicTypesMessage, BasicTypesMessage>(
            new BasicTypesMessage { RegularInt = 2 },
            match: r => r.RegularInt == 2,
            timeoutSeconds: 2f);

        await Task.WhenAll(taskA, taskB);

        Assert("concurrent: request A resolved correctly", taskA.Result.RegularInt == 1);
        Assert("concurrent: request B resolved correctly", taskB.Result.RegularInt == 2);
        Assert("concurrent: A flag correct", taskA.Result.Flag == true);
        Assert("concurrent: B flag correct", taskB.Result.Flag == false);
    }

    // -------------------------------------------------------------------------
    // Test 5: Subscription cleaned up after success
    // -------------------------------------------------------------------------
    static async Task TestSubscriptionRemovedAfterSuccess()
    {
        var transport = new MockTransport();
        using var sdk = new StructFrameSdk(SdkTestHelpers.MakeConfig(transport));

        _ = Task.Run(async () =>
        {
            await Task.Delay(30);
            transport.InjectData(SdkTestHelpers.EncodeStandard(
                new BasicTypesMessage { RegularInt = 3 }));
        });

        await sdk.RequestAsync<BasicTypesMessage, BasicTypesMessage>(
            new BasicTypesMessage { RegularInt = 3 });

        // Access internal handler dictionary via reflection to check cleanup.
        var handlersField = typeof(StructFrameSdk).GetField(
            "_messageHandlers",
            System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
        var handlers = handlersField?.GetValue(sdk)
            as Dictionary<ushort, IMessageHandler[]>;
        var msgId = (ushort)BasicTypesMessage.MsgId;
        bool empty = handlers == null
            || !handlers.TryGetValue(msgId, out var arr)
            || arr.Length == 0;
        Assert("cleanup: subscription removed after success", empty);
    }

    // -------------------------------------------------------------------------
    // Test 6: Subscription cleaned up after timeout
    // -------------------------------------------------------------------------
    static async Task TestSubscriptionRemovedAfterTimeout()
    {
        var transport = new MockTransport();
        using var sdk = new StructFrameSdk(SdkTestHelpers.MakeConfig(transport));

        try
        {
            await sdk.RequestAsync<BasicTypesMessage, BasicTypesMessage>(
                new BasicTypesMessage { RegularInt = 0 },
                timeoutSeconds: 0.05f);
        }
        catch (TimeoutException) { }

        var handlersField = typeof(StructFrameSdk).GetField(
            "_messageHandlers",
            System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
        var handlers = handlersField?.GetValue(sdk)
            as Dictionary<ushort, IMessageHandler[]>;
        var msgId = (ushort)BasicTypesMessage.MsgId;
        bool empty = handlers == null
            || !handlers.TryGetValue(msgId, out var arr)
            || arr.Length == 0;
        Assert("cleanup: subscription removed after timeout", empty);
    }

    // -------------------------------------------------------------------------
    // Test 7: CancellationToken cancels the request
    // -------------------------------------------------------------------------
    static async Task TestCancellationToken()
    {
        var transport = new MockTransport();
        using var sdk = new StructFrameSdk(SdkTestHelpers.MakeConfig(transport));

        using var cts = new CancellationTokenSource();
        cts.CancelAfter(50);

        bool cancelled = false;
        try
        {
            await sdk.RequestAsync<BasicTypesMessage, BasicTypesMessage>(
                new BasicTypesMessage { RegularInt = 0 },
                timeoutSeconds: 10f,
                ct: cts.Token);
        }
        catch (OperationCanceledException)
        {
            cancelled = true;
        }
        catch (TimeoutException)
        {
            // Also acceptable if ct fires before the timeout path does.
            cancelled = true;
        }

        Assert("cancellation: request cancelled via CancellationToken", cancelled);
    }

    // -------------------------------------------------------------------------
    // Entry point
    // -------------------------------------------------------------------------
    public static int Main(string[] args)
    {
        Console.WriteLine();
        Console.WriteLine("========================================");
        Console.WriteLine("REQUEST/RESPONSE TESTS - C#");
        Console.WriteLine("========================================");
        Console.WriteLine();

        TestBasicRequestResponse().GetAwaiter().GetResult();
        TestTimeout().GetAwaiter().GetResult();
        TestMatchPredicateFiltersResponses().GetAwaiter().GetResult();
        TestConcurrentRequestsWithMatch().GetAwaiter().GetResult();
        TestSubscriptionRemovedAfterSuccess().GetAwaiter().GetResult();
        TestSubscriptionRemovedAfterTimeout().GetAwaiter().GetResult();
        TestCancellationToken().GetAwaiter().GetResult();

        Console.WriteLine();
        Console.WriteLine("========================================");
        Console.WriteLine($"Summary: {_passed}/{_passed + _failed} tests passed");
        Console.WriteLine("========================================");
        Console.WriteLine();

        return _failed > 0 ? 1 : 0;
    }
}
