using System;
using System.Runtime.InteropServices;

namespace StructFrameTests
{
    class TestArrays
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

        static bool TestArrayOperations()
        {
            try
            {
                // Create a new message instance
                var msg = new StructFrame.ComprehensiveArrays.ComprehensiveArraysComprehensiveArrayMessage();

                // Initialize arrays
                msg.FixedInts = new int[3];
                msg.FixedFloats = new float[2];
                msg.FixedBools = new bool[4];

                // Set fixed array values
                msg.FixedInts[0] = 1;
                msg.FixedInts[1] = 2;
                msg.FixedInts[2] = 3;

                msg.FixedFloats[0] = 1.1f;
                msg.FixedFloats[1] = 2.2f;

                msg.FixedBools[0] = true;
                msg.FixedBools[1] = false;
                msg.FixedBools[2] = true;
                msg.FixedBools[3] = false;

                // Set bounded array values
                msg.BoundedUintsCount = 3;
                msg.BoundedUintsData = new ushort[3];
                msg.BoundedUintsData[0] = 100;
                msg.BoundedUintsData[1] = 200;
                msg.BoundedUintsData[2] = 300;

                msg.BoundedDoublesCount = 2;
                msg.BoundedDoublesData = new double[2];
                msg.BoundedDoublesData[0] = 1.5;
                msg.BoundedDoublesData[1] = 2.5;

                // Initialize string arrays as byte arrays
                msg.FixedStrings = new byte[2 * 8]; // 2 strings * 8 chars
                var str1 = System.Text.Encoding.ASCII.GetBytes("Hello");
                var str2 = System.Text.Encoding.ASCII.GetBytes("World");
                Array.Copy(str1, 0, msg.FixedStrings, 0, Math.Min(str1.Length, 8));
                Array.Copy(str2, 0, msg.FixedStrings, 8, Math.Min(str2.Length, 8));

                msg.BoundedStringsCount = 2;
                msg.BoundedStringsData = new byte[2 * 12]; // 2 strings * 12 chars
                var bstr1 = System.Text.Encoding.ASCII.GetBytes("Test1");
                var bstr2 = System.Text.Encoding.ASCII.GetBytes("Test2");
                Array.Copy(bstr1, 0, msg.BoundedStringsData, 0, Math.Min(bstr1.Length, 12));
                Array.Copy(bstr2, 0, msg.BoundedStringsData, 12, Math.Min(bstr2.Length, 12));

                // Initialize enum arrays
                msg.FixedStatuses = new byte[2];
                msg.FixedStatuses[0] = (byte)StructFrame.ComprehensiveArrays.ComprehensiveArraysStatus.ACTIVE;
                msg.FixedStatuses[1] = (byte)StructFrame.ComprehensiveArrays.ComprehensiveArraysStatus.INACTIVE;

                msg.BoundedStatusesCount = 2;
                msg.BoundedStatusesData = new byte[2];
                msg.BoundedStatusesData[0] = (byte)StructFrame.ComprehensiveArrays.ComprehensiveArraysStatus.ERROR;
                msg.BoundedStatusesData[1] = (byte)StructFrame.ComprehensiveArrays.ComprehensiveArraysStatus.MAINTENANCE;

                // Initialize nested message arrays
                msg.FixedSensors = new StructFrame.ComprehensiveArrays.ComprehensiveArraysSensor[1];
                msg.FixedSensors[0] = new StructFrame.ComprehensiveArrays.ComprehensiveArraysSensor();
                msg.FixedSensors[0].Id = 1;
                msg.FixedSensors[0].Value = 25.5f;
                msg.FixedSensors[0].Status = StructFrame.ComprehensiveArrays.ComprehensiveArraysStatus.ACTIVE;
                msg.FixedSensors[0].Name = new byte[16];
                var sensorName = System.Text.Encoding.ASCII.GetBytes("Sensor1");
                Array.Copy(sensorName, msg.FixedSensors[0].Name, Math.Min(sensorName.Length, 16));

                msg.BoundedSensorsCount = 1;
                msg.BoundedSensorsData = new StructFrame.ComprehensiveArrays.ComprehensiveArraysSensor[1];
                msg.BoundedSensorsData[0] = new StructFrame.ComprehensiveArrays.ComprehensiveArraysSensor();
                msg.BoundedSensorsData[0].Id = 2;
                msg.BoundedSensorsData[0].Value = 30.0f;
                msg.BoundedSensorsData[0].Status = StructFrame.ComprehensiveArrays.ComprehensiveArraysStatus.MAINTENANCE;
                msg.BoundedSensorsData[0].Name = new byte[16];
                var sensorName2 = System.Text.Encoding.ASCII.GetBytes("Sensor2");
                Array.Copy(sensorName2, msg.BoundedSensorsData[0].Name, Math.Min(sensorName2.Length, 16));

                // Verify struct size matches expected
                int size = Marshal.SizeOf(typeof(StructFrame.ComprehensiveArrays.ComprehensiveArraysComprehensiveArrayMessage));
                if (size != StructFrame.ComprehensiveArrays.ComprehensiveArraysComprehensiveArrayMessage.MaxSize)
                {
                    PrintFailureDetails("Struct size mismatch",
                        StructFrame.ComprehensiveArrays.ComprehensiveArraysComprehensiveArrayMessage.MaxSize.ToString(),
                        size.ToString());
                    return false;
                }

                // Serialize to bytes
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

                // Deserialize back and verify
                ptr = Marshal.AllocHGlobal(size);
                try
                {
                    Marshal.Copy(buffer, 0, ptr, size);
                    var decoded = Marshal.PtrToStructure<StructFrame.ComprehensiveArrays.ComprehensiveArraysComprehensiveArrayMessage>(ptr);

                    // Verify fixed int array
                    if (decoded.FixedInts[0] != 1 || decoded.FixedInts[1] != 2 || decoded.FixedInts[2] != 3)
                    {
                        PrintFailureDetails("FixedInts mismatch",
                            "1, 2, 3",
                            $"{decoded.FixedInts[0]}, {decoded.FixedInts[1]}, {decoded.FixedInts[2]}");
                        return false;
                    }

                    // Verify fixed float array
                    if (Math.Abs(decoded.FixedFloats[0] - 1.1f) > 0.01f ||
                        Math.Abs(decoded.FixedFloats[1] - 2.2f) > 0.01f)
                    {
                        PrintFailureDetails("FixedFloats mismatch",
                            "1.1, 2.2",
                            $"{decoded.FixedFloats[0]}, {decoded.FixedFloats[1]}");
                        return false;
                    }

                    // Verify bounded uint count
                    if (decoded.BoundedUintsCount != 3)
                    {
                        PrintFailureDetails("BoundedUintsCount mismatch",
                            "3", decoded.BoundedUintsCount.ToString());
                        return false;
                    }

                    // Verify bounded uint values
                    if (decoded.BoundedUintsData[0] != 100 ||
                        decoded.BoundedUintsData[1] != 200 ||
                        decoded.BoundedUintsData[2] != 300)
                    {
                        PrintFailureDetails("BoundedUintsData mismatch",
                            "100, 200, 300",
                            $"{decoded.BoundedUintsData[0]}, {decoded.BoundedUintsData[1]}, {decoded.BoundedUintsData[2]}");
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
                Console.WriteLine(e.StackTrace);
                return false;
            }
        }

        static int Main(string[] args)
        {
            Console.WriteLine("\n[TEST START] C# Array Operations");

            bool success = TestArrayOperations();

            string status = success ? "PASS" : "FAIL";
            Console.WriteLine($"[TEST END] C# Array Operations: {status}\n");

            return success ? 0 : 1;
        }
    }
}
