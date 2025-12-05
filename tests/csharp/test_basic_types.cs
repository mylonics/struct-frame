using System;
using System.Runtime.InteropServices;

namespace StructFrameTests
{
    class TestBasicTypes
    {
        static void PrintFailureDetails(string label, string expected = null, string actual = null)
        {
            Console.WriteLine();
            Console.WriteLine("============================================================");
            Console.WriteLine($"FAILURE DETAILS: {label}");
            Console.WriteLine("============================================================");

            if (expected != null)
            {
                Console.WriteLine($"\nExpected: {expected}");
            }
            if (actual != null)
            {
                Console.WriteLine($"Actual: {actual}");
            }

            Console.WriteLine("============================================================");
            Console.WriteLine();
        }

        static bool TestBasicTypesMessage()
        {
            try
            {
                // Create a new message instance
                var msg = new StructFrame.BasicTypes.BasicTypesBasicTypesMessage();

                // Set values
                msg.SmallInt = -42;
                msg.MediumInt = -1000;
                msg.RegularInt = -100000;
                msg.LargeInt = -1000000000L;
                msg.SmallUint = 255;
                msg.MediumUint = 65535;
                msg.RegularUint = 4294967295U;
                msg.LargeUint = 18446744073709551615UL;
                msg.SinglePrecision = 3.14159f;
                msg.DoublePrecision = 2.718281828459045;
                msg.Flag = true;
                msg.DeviceId = new byte[32];
                msg.DescriptionLength = 12;
                msg.DescriptionData = new byte[128];

                // Fill device id
                var deviceIdBytes = System.Text.Encoding.ASCII.GetBytes("TEST_DEVICE_001");
                Array.Copy(deviceIdBytes, msg.DeviceId, Math.Min(deviceIdBytes.Length, 32));

                // Fill description
                var descBytes = System.Text.Encoding.ASCII.GetBytes("Test message");
                Array.Copy(descBytes, msg.DescriptionData, Math.Min(descBytes.Length, 128));

                // Serialize to bytes using Marshal
                int size = Marshal.SizeOf(typeof(StructFrame.BasicTypes.BasicTypesBasicTypesMessage));
                if (size != StructFrame.BasicTypes.BasicTypesBasicTypesMessage.MaxSize)
                {
                    PrintFailureDetails("Struct size mismatch",
                        StructFrame.BasicTypes.BasicTypesBasicTypesMessage.MaxSize.ToString(),
                        size.ToString());
                    return false;
                }

                byte[] buffer = new byte[size];
                IntPtr ptr = Marshal.AllocHGlobal(size);
                try
                {
                    Marshal.StructureToPtr(msg, ptr, false);
                    Marshal.Copy(ptr, buffer, 0, size);
                }
                finally
                {
                    Marshal.FreeHGlobal(ptr);
                }

                // Deserialize back
                ptr = Marshal.AllocHGlobal(size);
                try
                {
                    Marshal.Copy(buffer, 0, ptr, size);
                    var decoded = Marshal.PtrToStructure<StructFrame.BasicTypes.BasicTypesBasicTypesMessage>(ptr);

                    // Verify values
                    if (decoded.SmallInt != msg.SmallInt)
                    {
                        PrintFailureDetails("SmallInt mismatch",
                            msg.SmallInt.ToString(), decoded.SmallInt.ToString());
                        return false;
                    }

                    if (decoded.MediumInt != msg.MediumInt)
                    {
                        PrintFailureDetails("MediumInt mismatch",
                            msg.MediumInt.ToString(), decoded.MediumInt.ToString());
                        return false;
                    }

                    if (decoded.RegularInt != msg.RegularInt)
                    {
                        PrintFailureDetails("RegularInt mismatch",
                            msg.RegularInt.ToString(), decoded.RegularInt.ToString());
                        return false;
                    }

                    if (decoded.Flag != msg.Flag)
                    {
                        PrintFailureDetails("Flag mismatch",
                            msg.Flag.ToString(), decoded.Flag.ToString());
                        return false;
                    }

                    if (Math.Abs(decoded.SinglePrecision - msg.SinglePrecision) > 0.0001f)
                    {
                        PrintFailureDetails("SinglePrecision mismatch",
                            msg.SinglePrecision.ToString(), decoded.SinglePrecision.ToString());
                        return false;
                    }
                }
                finally
                {
                    Marshal.FreeHGlobal(ptr);
                }

                return true;
            }
            catch (Exception e)
            {
                PrintFailureDetails($"Exception: {e.GetType().Name}", "success", e.Message);
                return false;
            }
        }

        static int Main(string[] args)
        {
            Console.WriteLine("\n[TEST START] C# Basic Types");

            bool success = TestBasicTypesMessage();

            string status = success ? "PASS" : "FAIL";
            Console.WriteLine($"[TEST END] C# Basic Types: {status}\n");

            return success ? 0 : 1;
        }
    }
}
