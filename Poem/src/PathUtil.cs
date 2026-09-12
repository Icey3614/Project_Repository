using System;
using System.IO;

namespace LitePoem
{
    public static class PathUtil
    {
        // 优先写到 exe 同目录；不可写(例如 Program Files)则退回 %APPDATA%\LitePoem
        public static string GetWritableFile(string fileName)
        {
            string exeDir = AppDomain.CurrentDomain.BaseDirectory;
            string candidate = Path.Combine(exeDir, fileName);
            try
            {
                if (string.IsNullOrEmpty(exeDir) || !Directory.Exists(exeDir))
                {
                    throw new IOException("exe dir not exist");
                }
                using (FileStream fs = new FileStream(candidate, FileMode.OpenOrCreate, FileAccess.Write, FileShare.Read))
                {
                    fs.Close();
                }
                return candidate;
            }
            catch
            {
                string appDir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "LitePoem");
                if (!Directory.Exists(appDir)) Directory.CreateDirectory(appDir);
                return Path.Combine(appDir, fileName);
            }
        }
    }
}
