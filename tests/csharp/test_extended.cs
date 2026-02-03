/**
 * Test entry point for extended message tests (C#).
 */

using System;
using StructFrame.ExtendedTest;
using StructFrameTests;

class TestExtended
{
    private const string TEST_NAME = "ExtendedMessages";
    private const string PROFILES = "bulk, network";

    public static int Main(string[] args)
    {
        return TestHarness.Run(
            args,
            ExtendedMessages.MESSAGE_COUNT,
            ExtendedMessages.GetMessage,
            ExtendedMessages.CheckMessage,
            (msgId) => MessageDefinitions.GetMessageInfo(msgId),
            TEST_NAME,
            PROFILES
        );
    }
}
