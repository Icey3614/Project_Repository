using System;
using System.Threading;
using System.Windows;
using System.Windows.Threading;

namespace LitePoem
{
    public class AppRoot
    {
        private Application _app;
        private AppSettings _settings;
        private PoemService _service;
        private MainWindow _win;
        private TrayIcon _tray;
        private DispatcherTimer _timer;
        private string _settingsPath;
        private string _historyPath;
        private bool _busy;

        public AppRoot(Application app)
        {
            _app = app;
        }

        public void Start()
        {
            _settingsPath = PathUtil.GetWritableFile("settings.json");
            _historyPath = PathUtil.GetWritableFile("poem_history.jsonl");
            _settings = AppSettings.Load(_settingsPath);
            try
            {
                if (new System.IO.FileInfo(_settingsPath).Length == 0) _settings.Save(_settingsPath);
            }
            catch { }

            _service = new PoemService(_historyPath);
            _service.LoadLocal();

            _win = new MainWindow(_settings);
            _win.SwitchRequested += delegate { TriggerPick(); };

            _tray = new TrayIcon(new Action(TriggerPick), new Action(OpenSettings), new Action(Exit));

            AutoStartManager.Apply(_settings.AutoStart);
            StartTimer();
            ShowPoem(_service.PickPoemLocal(""));
            TriggerPick();
        }

        private void TriggerPick()
        {
            if (_busy) return;
            _busy = true;

            string current = _win.CurrentContent;
            if (!_settings.UseNetwork)
            {
                ShowPoem(_service.PickPoemLocal(current));
                return;
            }

            ThreadPool.QueueUserWorkItem(delegate
            {
                Poem poem = _service.PickPoem(current);
                _win.Dispatcher.BeginInvoke(new Action(delegate { ShowPoem(poem); }));
            });
        }

        private void ShowPoem(Poem poem)
        {
            if (poem == null) poem = _service.PickPoemLocal("");
            _service.SaveToHistory(poem);
            _win.SetPoem(poem.Content);
            if (!_win.IsVisible) _win.Show();
            _tray.SetTooltip("桌面诗词：" + poem.Content);
            _busy = false;
        }

        private void StartTimer()
        {
            if (_timer != null)
            {
                _timer.Stop();
                _timer.Tick -= OnTimerTick;
                _timer = null;
            }
            double minutes = _settings.IntervalMinutes > 0 ? _settings.IntervalMinutes : 10;
            _timer = new DispatcherTimer();
            _timer.Interval = TimeSpan.FromMinutes(minutes);
            _timer.Tick += OnTimerTick;
            _timer.Start();
        }

        private void OnTimerTick(object sender, EventArgs e)
        {
            TriggerPick();
        }

        private void OpenSettings()
        {
            SettingsWindow sw = new SettingsWindow(_settings, new Action<AppSettings>(OnSettingsSaved));
            sw.Owner = null;
            sw.ShowInTaskbar = true;
            sw.Topmost = false;
            sw.ShowDialog();
        }

        private void OnSettingsSaved(AppSettings settings)
        {
            _win.ApplySettings(settings);
            AutoStartManager.Apply(settings.AutoStart);
            _settings.Save(_settingsPath);
            StartTimer();
            TriggerPick();
        }

        private void Exit()
        {
            if (_timer != null)
            {
                _timer.Stop();
                _timer.Tick -= OnTimerTick;
                _timer = null;
            }
            if (_tray != null) _tray.Dispose();
            if (_win != null) _win.Close();
            _app.Shutdown();
        }
    }
}
