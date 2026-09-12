using System;
using Microsoft.Win32;

namespace LitePoem
{
    public static class AutoStartManager
    {
        private const string RunKey = @"Software\Microsoft\Windows\CurrentVersion\Run";
        private const string ValueName = "LitePoem";

        public static void Apply(bool enabled)
        {
            try
            {
                using (RegistryKey key = Registry.CurrentUser.OpenSubKey(RunKey, true))
                {
                    if (key == null) return;
                    string[] names = key.GetValueNames();
                    bool exists = Array.IndexOf(names, ValueName) >= 0;
                    if (enabled)
                    {
                        if (!exists)
                        {
                            string exe = System.Reflection.Assembly.GetEntryAssembly().Location;
                            key.SetValue(ValueName, "\"" + exe + "\"");
                        }
                    }
                    else
                    {
                        if (exists) key.DeleteValue(ValueName, false);
                    }
                }
            }
            catch
            {
            }
        }
    }
}
