using System;
using System.Windows;
using System.Windows.Controls;
using System.Collections.Generic;
using System.Windows.Media;

namespace LitePoem
{
    public class SettingsWindow : Window
    {
        private TextBox _interval;
        private TextBox _fontSize;
        private ComboBox _font;
        private CheckBox _network;
        private ComboBox _style;
        private CheckBox _autoStart;
        private Border _colorSwatch;
        private string _pickedColor;
        private AppSettings _settings;
        private Action<AppSettings> _onSave;

        public SettingsWindow(AppSettings settings, Action<AppSettings> onSave)
        {
            _settings = settings;
            _onSave = onSave;
            _pickedColor = settings.FontColor;

            this.Title = "桌面诗词 - 设置";
            this.Width = 400;
            this.Height = 440;
            this.ResizeMode = ResizeMode.NoResize;
            this.WindowStartupLocation = WindowStartupLocation.CenterScreen;
            this.Background = Brushes.White;

            StackPanel panel = new StackPanel();
            panel.Margin = new Thickness(18, 12, 18, 12);

            panel.Children.Add(MakeLabel("更新间隔（分钟）"));
            _interval = new TextBox();
            _interval.Text = settings.IntervalMinutes.ToString();
            panel.Children.Add(_interval);

            panel.Children.Add(MakeLabel("字体大小"));
            _fontSize = new TextBox();
            _fontSize.Text = settings.FontSize.ToString();
            panel.Children.Add(_fontSize);

            panel.Children.Add(MakeLabel("字体"));
            _font = BuildFontCombo(settings.FontFamilyName);
            panel.Children.Add(_font);

            panel.Children.Add(MakeLabel("联网获取"));
            _network = new CheckBox();
            _network.Content = "联网获取诗句（失败自动回退本地）";
            _network.IsChecked = settings.UseNetwork;
            panel.Children.Add(_network);

            panel.Children.Add(MakeLabel("背景样式"));
            _style = new ComboBox();
            _style.Items.Add("半透明圆角卡片");
            _style.Items.Add("纯白底");
            _style.Items.Add("无背景（仅文字）");
            _style.SelectedIndex = settings.BackgroundStyle;
            panel.Children.Add(_style);

            panel.Children.Add(MakeLabel("字体颜色"));
            StackPanel colorRow = new StackPanel();
            colorRow.Orientation = Orientation.Horizontal;
            colorRow.Margin = new Thickness(0, 0, 0, 0);
            Button colorBtn = new Button();
            colorBtn.Content = "点击选取…";
            colorBtn.Width = 100;
            colorBtn.Margin = new Thickness(0, 0, 12, 0);
            colorBtn.Click += delegate { PickColor(); };
            _colorSwatch = new Border();
            _colorSwatch.Width = 120;
            _colorSwatch.Height = 26;
            _colorSwatch.CornerRadius = new CornerRadius(4);
            _colorSwatch.BorderBrush = new SolidColorBrush(Color.FromRgb(0xBB, 0xBB, 0xBB));
            _colorSwatch.BorderThickness = new Thickness(1);
            colorRow.Children.Add(colorBtn);
            colorRow.Children.Add(_colorSwatch);
            panel.Children.Add(colorRow);
            UpdateColorSwatch();

            panel.Children.Add(MakeLabel("开机自启"));
            _autoStart = new CheckBox();
            _autoStart.Content = "登录 Windows 时自动运行";
            _autoStart.IsChecked = settings.AutoStart;
            panel.Children.Add(_autoStart);

            StackPanel buttons = new StackPanel();
            buttons.Orientation = Orientation.Horizontal;
            buttons.HorizontalAlignment = HorizontalAlignment.Right;
            buttons.Margin = new Thickness(0, 16, 0, 0);

            Button ok = new Button();
            ok.Content = "保存";
            ok.Width = 80;
            ok.Margin = new Thickness(0, 0, 8, 0);
            ok.Click += delegate { Save(); };

            Button cancel = new Button();
            cancel.Content = "取消";
            cancel.Width = 80;
            cancel.Click += delegate { Close(); };

            buttons.Children.Add(ok);
            buttons.Children.Add(cancel);
            panel.Children.Add(buttons);

            this.Content = panel;
        }

        private ComboBox BuildFontCombo(string current)
        {
            ComboBox cb = new ComboBox();
            List<string> names = new List<string>();
            try
            {
                foreach (FontFamily ff in Fonts.SystemFontFamilies)
                {
                    string n = ff.Source;
                    if (!string.IsNullOrEmpty(n) && !names.Contains(n)) names.Add(n);
                }
            }
            catch
            {
            }
            names.Sort();
            if (!string.IsNullOrEmpty(current) && !names.Contains(current)) names.Insert(0, current);
            foreach (string n in names) cb.Items.Add(n);
            if (!string.IsNullOrEmpty(current) && names.Contains(current)) cb.SelectedItem = current;
            else if (cb.Items.Count > 0) cb.SelectedIndex = 0;
            return cb;
        }

        private void PickColor()
        {
            System.Windows.Forms.ColorDialog dlg = new System.Windows.Forms.ColorDialog();
            try
            {
                dlg.Color = System.Drawing.ColorTranslator.FromHtml(_pickedColor);
            }
            catch
            {
                dlg.Color = System.Drawing.Color.White;
            }
            dlg.FullOpen = true;
            dlg.AnyColor = true;
            IntPtr owner = new System.Windows.Interop.WindowInteropHelper(this).Handle;
            if (dlg.ShowDialog(new Win32Window(owner)) == System.Windows.Forms.DialogResult.OK)
            {
                System.Drawing.Color c = dlg.Color;
                _pickedColor = "#" + c.R.ToString("X2") + c.G.ToString("X2") + c.B.ToString("X2");
                UpdateColorSwatch();
            }
        }

        private class Win32Window : System.Windows.Forms.IWin32Window
        {
            private IntPtr _h;
            public Win32Window(IntPtr h) { _h = h; }
            public IntPtr Handle { get { return _h; } }
        }

        private void UpdateColorSwatch()
        {
            try
            {
                System.Drawing.Color c = System.Drawing.ColorTranslator.FromHtml(_pickedColor);
                _colorSwatch.Background = new SolidColorBrush(Color.FromRgb(c.R, c.G, c.B));
                _colorSwatch.ToolTip = _pickedColor;
            }
            catch
            {
                _colorSwatch.Background = Brushes.White;
            }
        }

        private TextBlock MakeLabel(string text)
        {
            TextBlock t = new TextBlock();
            t.Text = text;
            t.Margin = new Thickness(0, 10, 0, 3);
            return t;
        }

        private void Save()
        {
            int interval = 10;
            if (!int.TryParse(_interval.Text, out interval)) interval = 10;
            if (interval < 1) interval = 1;

            double fontSize = 22;
            if (!double.TryParse(_fontSize.Text, out fontSize)) fontSize = 22;
            if (fontSize < 8) fontSize = 8;

            _settings.IntervalMinutes = interval;
            _settings.FontSize = fontSize;
            string fontName = _font.SelectedItem as string;
            if (!string.IsNullOrEmpty(fontName)) _settings.FontFamilyName = fontName;
            _settings.UseNetwork = _network.IsChecked == true;
            _settings.BackgroundStyle = _style.SelectedIndex < 0 ? 2 : _style.SelectedIndex;
            _settings.FontColor = _pickedColor;
            _settings.AutoStart = _autoStart.IsChecked == true;

            if (_onSave != null) _onSave(_settings);
            Close();
        }
    }
}
