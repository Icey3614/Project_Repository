using System;
using System.Globalization;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Interop;
using System.Windows.Media;
using System.Windows.Media.Effects;

namespace LitePoem
{
    public class MainWindow : Window
    {
        private const int GWL_EXSTYLE = -20;
        private const int WS_EX_TOOLWINDOW = 0x00000080;
        private const uint SWP_NOSIZE = 0x0001;
        private const uint SWP_NOMOVE = 0x0002;
        private const uint SWP_NOACTIVATE = 0x0010;
        private const int WM_WINDOWPOSCHANGING = 0x0046;
        private static readonly IntPtr HWND_BOTTOM = new IntPtr(1);

        private Border _card;
        private TextBlock _text;
        private AppSettings _settings;
        private HwndSource _source;

        public event EventHandler SwitchRequested;

        [DllImport("user32.dll")]
        private static extern int GetWindowLong(IntPtr hWnd, int nIndex);

        [DllImport("user32.dll")]
        private static extern int SetWindowLong(IntPtr hWnd, int nIndex, int dwNewLong);

        [DllImport("user32.dll")]
        private static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter,
            int X, int Y, int cx, int cy, uint uFlags);

        [StructLayout(LayoutKind.Sequential)]
        private struct WINDOWPOS
        {
            public IntPtr hwnd;
            public IntPtr hwndInsertAfter;
            public int x;
            public int y;
            public int cx;
            public int cy;
            public uint flags;
        }

        public MainWindow(AppSettings settings)
        {
            _settings = settings;

            this.Title = "桌面诗词";
            this.WindowStyle = WindowStyle.None;
            this.ResizeMode = ResizeMode.NoResize;
            this.ShowInTaskbar = false;
            this.Topmost = false;
            this.AllowsTransparency = true;
            this.Background = Brushes.Transparent;
            this.SizeToContent = SizeToContent.WidthAndHeight;
            this.ShowActivated = false;

            _text = new TextBlock();
            _text.TextWrapping = TextWrapping.Wrap;
            _text.MaxWidth = 320;
            _text.Margin = new Thickness(14, 12, 14, 12);
            _text.TextAlignment = TextAlignment.Center;

            _card = new Border();
            _card.Child = _text;
            this.Content = _card;

            ApplyStyle();
            this.SourceInitialized += OnSourceInitialized;
            this.SizeChanged += OnSizeChanged;
            this.MouseRightButtonUp += OnRightClick;
        }

        public string CurrentContent
        {
            get { return _text.Text; }
        }

        private void OnSourceInitialized(object sender, EventArgs e)
        {
            IntPtr hwnd = new WindowInteropHelper(this).Handle;
            int exStyle = GetWindowLong(hwnd, GWL_EXSTYLE);
            SetWindowLong(hwnd, GWL_EXSTYLE, exStyle | WS_EX_TOOLWINDOW);

            _source = HwndSource.FromHwnd(hwnd);
            if (_source != null) _source.AddHook(WndProc);

            PositionWindow();
            SetWindowPos(hwnd, HWND_BOTTOM, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE);
        }

        private IntPtr WndProc(IntPtr hwnd, int msg, IntPtr wParam, IntPtr lParam, ref bool handled)
        {
            if (msg == WM_WINDOWPOSCHANGING)
            {
                WINDOWPOS pos = (WINDOWPOS)Marshal.PtrToStructure(lParam, typeof(WINDOWPOS));
                pos.hwndInsertAfter = HWND_BOTTOM;
                Marshal.StructureToPtr(pos, lParam, false);
            }
            return IntPtr.Zero;
        }

        private void OnSizeChanged(object sender, SizeChangedEventArgs e)
        {
            PositionWindow();
        }

        private void OnRightClick(object sender, MouseButtonEventArgs e)
        {
            if (SwitchRequested != null)
            {
                SwitchRequested(this, EventArgs.Empty);
            }
            e.Handled = true;
        }

        public void ApplyStyle()
        {
            int style = _settings.BackgroundStyle;
            double radius = _settings.CornerRadius;
            Color textColor = ColorFromHex(_settings.FontColor, Colors.White);
            SolidColorBrush textBrush = new SolidColorBrush(textColor);
            _text.Foreground = textBrush;

            if (style == 0)
            {
                _card.Background = new SolidColorBrush(Color.FromArgb(238, 255, 255, 255));
                _card.BorderBrush = new SolidColorBrush(Color.FromArgb(120, 90, 90, 90));
                _card.BorderThickness = new Thickness(1);
                _card.CornerRadius = new CornerRadius(radius);
                _card.Effect = MakeShadow(Colors.Black, 12, 2, 0.22);
            }
            else if (style == 1)
            {
                _card.Background = Brushes.White;
                _card.BorderBrush = null;
                _card.BorderThickness = new Thickness(0);
                _card.CornerRadius = new CornerRadius(radius);
                _card.Effect = null;
            }
            else
            {
                _card.Background = Brushes.Transparent;
                _card.BorderBrush = null;
                _card.BorderThickness = new Thickness(0);
                _card.CornerRadius = new CornerRadius(0);
                Color shadowColor = Readability(textColor) ? Colors.Black : Colors.White;
                _card.Effect = MakeShadow(shadowColor, 0, 1, 0.85);
            }

            _text.FontFamily = new FontFamily(_settings.FontFamilyName);
            _text.FontSize = _settings.FontSize;
        }

        private static DropShadowEffect MakeShadow(Color color, double blur, double depth, double opacity)
        {
            DropShadowEffect shadow = new DropShadowEffect();
            shadow.Color = color;
            shadow.BlurRadius = blur;
            shadow.ShadowDepth = depth;
            shadow.Direction = 270;
            shadow.Opacity = opacity;
            return shadow;
        }

        private static bool Readability(Color c)
        {
            double l = 0.299 * c.R + 0.587 * c.G + 0.114 * c.B;
            return l > 140;
        }

        private static Color ColorFromHex(string hex, Color fallback)
        {
            try
            {
                if (string.IsNullOrEmpty(hex)) return fallback;
                string s = hex.Trim();
                if (s.StartsWith("#")) s = s.Substring(1);
                if (s.Length == 6)
                {
                    int r = int.Parse(s.Substring(0, 2), NumberStyles.HexNumber);
                    int g = int.Parse(s.Substring(2, 2), NumberStyles.HexNumber);
                    int b = int.Parse(s.Substring(4, 2), NumberStyles.HexNumber);
                    return Color.FromRgb((byte)r, (byte)g, (byte)b);
                }
            }
            catch
            {
            }
            return fallback;
        }

        public void SetPoem(string content)
        {
            _text.Text = FormatPoem(content);
        }

        private static string FormatPoem(string content)
        {
            if (string.IsNullOrEmpty(content)) return content;
            string[] seps = new string[] { "，", "。", "、", "；", "！", "？", ",", ";", "!" };
            for (int i = 0; i < seps.Length; i++)
            {
                int idx = content.IndexOf(seps[i]);
                if (idx >= 0)
                {
                    return content.Substring(0, idx + 1) + "\n" + content.Substring(idx + 1);
                }
            }
            return content;
        }

        public void ApplySettings(AppSettings settings)
        {
            _settings = settings;
            ApplyStyle();
        }

        private void PositionWindow()
        {
            Rect wa = SystemParameters.WorkArea;
            double w = double.IsNaN(ActualWidth) ? 120 : ActualWidth;
            double h = double.IsNaN(ActualHeight) ? 40 : ActualHeight;
            if (w <= 0) w = 120;
            if (h <= 0) h = 40;
            this.Left = wa.Right - w - 5;
            this.Top = wa.Top + 8;
        }
    }
}
