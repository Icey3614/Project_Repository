using System;
using System.IO;
using System.Text;
using System.Web.Script.Serialization;

namespace LitePoem
{
    public class AppSettings
    {
        public int IntervalMinutes { get; set; }
        public double FontSize { get; set; }
        public bool UseNetwork { get; set; }
        public int BackgroundStyle { get; set; }   // 0=半透明卡片 1=纯白 2=无背景(仅文字)
        public double CornerRadius { get; set; }
        public string FontFamilyName { get; set; }
        public string FontColor { get; set; }
        public bool AutoStart { get; set; }
        public double Margin { get; set; }

        public static AppSettings Default()
        {
            AppSettings s = new AppSettings();
            s.IntervalMinutes = 10;
            s.FontSize = 22;
            s.UseNetwork = true;
            s.BackgroundStyle = 2;
            s.CornerRadius = 10;
            s.FontFamilyName = "KaiTi";
            s.FontColor = "#FFFFFF";
            s.AutoStart = false;
            s.Margin = 16;
            return s;
        }

        public static AppSettings Load(string path)
        {
            try
            {
                if (File.Exists(path))
                {
                    JavaScriptSerializer js = new JavaScriptSerializer();
                    AppSettings s = js.Deserialize<AppSettings>(File.ReadAllText(path));
                    if (s != null) return s;
                }
            }
            catch
            {
            }
            return AppSettings.Default();
        }

        public void Save(string path)
        {
            try
            {
                JavaScriptSerializer js = new JavaScriptSerializer();
                File.WriteAllText(path, js.Serialize(this), new UTF8Encoding(false));
            }
            catch
            {
            }
        }
    }
}
