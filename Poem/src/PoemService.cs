using System;
using System.Collections.Generic;
using System.IO;
using System.Net;
using System.Text;
using System.Web.Script.Serialization;

namespace LitePoem
{
    public class PoemService
    {
        private static readonly string[] Apis = new string[]
        {
            "https://v1.hitokoto.cn/?c=i"
        };

        private const int RecentLineCap = 40;
        private const int RecentWorkCap = 20;
        private const int OnlineAttempts = 2;

        private readonly string _historyPath;
        private readonly List<Poem> _pool;
        private readonly Queue<string> _recentLines;
        private readonly Queue<string> _recentWorks;
        private readonly HashSet<string> _recentLineSet;
        private readonly HashSet<string> _recentWorkSet;
        private readonly JavaScriptSerializer _json;
        private readonly Random _rng;
        private int _apiIndex;

        public PoemService(string historyPath)
        {
            _historyPath = historyPath;
            _pool = new List<Poem>();
            _recentLines = new Queue<string>();
            _recentWorks = new Queue<string>();
            _recentLineSet = new HashSet<string>();
            _recentWorkSet = new HashSet<string>();
            _json = new JavaScriptSerializer();
            _rng = new Random(Guid.NewGuid().GetHashCode());
        }

        public void LoadLocal()
        {
            _pool.Clear();
            Poem[] seed = SeedPoems.All;
            for (int i = 0; i < seed.Length; i++)
            {
                if (!ContainsContent(seed[i].Content)) _pool.Add(seed[i]);
            }
            if (File.Exists(_historyPath))
            {
                string[] lines = File.ReadAllLines(_historyPath);
                for (int i = 0; i < lines.Length; i++)
                {
                    Poem p = ParseHistoryPoem(lines[i]);
                    if (p != null && !string.IsNullOrEmpty(p.Content) && !ContainsContent(p.Content)) _pool.Add(p);
                }
            }
        }

        public int LocalCount
        {
            get { return _pool.Count; }
        }

        public Poem PickPoem(string current)
        {
            Poem online = TryOnline();
            if (online != null && !IsWorkRecent(online.From))
            {
                MarkShown(online);
                return online;
            }
            Poem local = PickLocal(current);
            MarkShown(local);
            return local;
        }

        public Poem PickPoemLocal(string current)
        {
            Poem local = PickLocal(current);
            MarkShown(local);
            return local;
        }

        private Poem TryOnline()
        {
            Poem candidate = null;
            for (int i = 0; i < OnlineAttempts; i++)
            {
                try
                {
                    Poem p = FetchOneOnline();
                    if (p == null || string.IsNullOrEmpty(p.Content)) continue;
                    if (!IsWorkRecent(p.From)) return p;
                    if (candidate == null) candidate = p;
                }
                catch
                {
                }
            }
            return candidate;
        }

        private Poem FetchOneOnline()
        {
            string url = Apis[_apiIndex % Apis.Length];
            _apiIndex++;
            if (url.IndexOf('?') >= 0) url = url + "&_=" + _rng.Next(100000, 999999);
            else url = url + "?_=" + _rng.Next(100000, 999999);

            HttpWebRequest req = (HttpWebRequest)WebRequest.Create(url);
            req.Timeout = 4000;
            req.ReadWriteTimeout = 4000;
            req.UserAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)";
            using (HttpWebResponse resp = (HttpWebResponse)req.GetResponse())
            using (Stream s = resp.GetResponseStream())
            using (StreamReader sr = new StreamReader(s, Encoding.UTF8))
            {
                string body = sr.ReadToEnd();
                Poem p = ParseResponse(body);
                if (p != null && !string.IsNullOrEmpty(p.Content))
                {
                    p.IsOnline = true;
                    return p;
                }
            }
            return null;
        }

        private Poem ParseResponse(string json)
        {
            try
            {
                Dictionary<string, object> map = _json.Deserialize<Dictionary<string, object>>(json);
                if (map == null) return null;
                Poem p = new Poem();
                if (map.ContainsKey("hitokoto") && map["hitokoto"] != null)
                {
                    p.Content = map["hitokoto"].ToString();
                    p.From = GetString(map, "from");
                    p.FromWho = GetString(map, "from_who");
                    return p;
                }
                object dataObj = null;
                if (map.ContainsKey("data")) dataObj = map["data"];
                Dictionary<string, object> dataMap = dataObj as Dictionary<string, object>;
                if (dataMap != null && dataMap.ContainsKey("content") && dataMap["content"] != null)
                {
                    p.Content = dataMap["content"].ToString();
                    object originObj = null;
                    if (dataMap.ContainsKey("origin")) originObj = dataMap["origin"];
                    Dictionary<string, object> originMap = originObj as Dictionary<string, object>;
                    if (originMap != null)
                    {
                        p.From = GetString(originMap, "title");
                        p.FromWho = GetString(originMap, "author");
                    }
                    return p;
                }
                if (map.ContainsKey("content") && map["content"] != null)
                {
                    p.Content = map["content"].ToString();
                    p.From = GetString(map, "from");
                    p.FromWho = GetString(map, "from_who");
                    return p;
                }
                return null;
            }
            catch
            {
                return null;
            }
        }

        private string GetString(Dictionary<string, object> map, string key)
        {
            object o = null;
            if (map.TryGetValue(key, out o) && o != null) return o.ToString();
            return "";
        }

        private Poem PickLocal(string current)
        {
            if (_pool.Count == 0)
            {
                return new Poem { Content = "本地暂无诗句，请联网获取。", From = "", FromWho = "", IsOnline = false };
            }
            Poem chosen = null;
            int guard = 0;
            while (guard < 100 && chosen == null)
            {
                guard++;
                int idx = _rng.Next(_pool.Count);
                Poem cp = _pool[idx];
                if (cp.Content == current) continue;
                if (_recentLineSet.Contains(cp.Content)) continue;
                chosen = cp;
            }
            if (chosen == null) chosen = _pool[_rng.Next(_pool.Count)];
            return new Poem { Content = chosen.Content, From = chosen.From, FromWho = chosen.FromWho, IsOnline = false };
        }

        private bool ContainsContent(string content)
        {
            if (string.IsNullOrEmpty(content)) return false;
            for (int i = 0; i < _pool.Count; i++)
            {
                if (_pool[i].Content == content) return true;
            }
            return false;
        }

        private bool IsWorkRecent(string work)
        {
            if (string.IsNullOrEmpty(work)) return false;
            return _recentWorkSet.Contains(work);
        }

        private void MarkShown(Poem p)
        {
            if (p == null || string.IsNullOrEmpty(p.Content)) return;
            if (_recentLineSet.Add(p.Content))
            {
                Push(_recentLines, _recentLineSet, p.Content, RecentLineCap);
            }
            if (!string.IsNullOrEmpty(p.From) && _recentWorkSet.Add(p.From))
            {
                Push(_recentWorks, _recentWorkSet, p.From, RecentWorkCap);
            }
        }

        private void Push(Queue<string> q, HashSet<string> set, string item, int cap)
        {
            q.Enqueue(item);
            while (q.Count > cap)
            {
                string old = q.Dequeue();
                set.Remove(old);
            }
        }

        public void SaveToHistory(Poem p)
        {
            if (p == null || string.IsNullOrEmpty(p.Content)) return;
            try
            {
                Dictionary<string, object> entry = new Dictionary<string, object>();
                entry["content"] = p.Content;
                entry["from"] = p.From ?? "";
                entry["from_who"] = p.FromWho ?? "";
                entry["at"] = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss");
                string line = _json.Serialize(entry);
                string dir = Path.GetDirectoryName(_historyPath);
                if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
                File.AppendAllText(_historyPath, line + Environment.NewLine, new UTF8Encoding(false));
                if (!ContainsContent(p.Content)) _pool.Add(p);
            }
            catch
            {
            }
        }

        private Poem ParseHistoryPoem(string line)
        {
            try
            {
                Dictionary<string, object> map = _json.Deserialize<Dictionary<string, object>>(line);
                if (map == null) return null;
                Poem p = new Poem();
                if (map.ContainsKey("content") && map["content"] != null)
                {
                    p.Content = map["content"].ToString();
                }
                if (string.IsNullOrEmpty(p.Content)) return null;
                p.From = GetString(map, "from");
                p.FromWho = GetString(map, "from_who");
                return p;
            }
            catch
            {
                return null;
            }
        }
    }
}
