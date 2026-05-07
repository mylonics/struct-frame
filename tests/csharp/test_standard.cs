/**
 * Test entry point for standard message tests (C#).
 */

using System;
using StructFrame.SerializationTest;
using StructFrameTests;

class TestStandard
{
    private const string TEST_NAME = "StandardMessages";
    private const string PROFILES = "standard, sensor, ipc, bulk, network";

    public static int Main(string[] args)
    {
        // Verify enum ToString() before running the main test suite
        if (!StandardMessages.CheckEnumToString())
        {
            Console.Error.WriteLine("[FAIL] C# enum ToString() check failed");
            return 1;
        }

        // Verify discriminator=none oneof round-trip
        if (!StandardMessages.CheckDiscriminatorNone())
        {
            Console.Error.WriteLine("[FAIL] C# discriminator=none oneof check failed");
            return 1;
        }

        // Verify multiple oneof fields in one message
        if (!StandardMessages.CheckMultiOneof())
        {
            Console.Error.WriteLine("[FAIL] C# multi-oneof check failed");
            return 1;
        }

        return TestHarness.Run(
            args,
            StandardMessages.MESSAGE_COUNT,
            StandardMessages.GetMessage,
            StandardMessages.CheckMessage,
            (msgId) => MessageDefinitions.GetMessageInfo(msgId),
            TEST_NAME,
            PROFILES
        );
    }
}
