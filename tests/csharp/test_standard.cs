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
