using System;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Effects;

namespace LitePoem
{
    // 用独立窗口做托盘右键菜单：激活后点击其它任意位置会失焦(Deactivated)自动关闭，类似 QQ。
    public class TrayMenuWindow : Window
    {
        public TrayMenuWindow(Action openSettings, Action exit)
        {
            this.Title = "桌面诗词";
            this.WindowStyle = WindowStyle.None;
            this.ResizeMode = ResizeMode.NoResize;
            this.ShowInTaskbar = false;
            this.Topmost = true;
            this.AllowsTransparency = true;
            this.Background = Brushes.Transparent;
            this.SizeToContent = SizeToContent.WidthAndHeight;
            this.ShowActivated = true;
            this.Deactivated += delegate { Close(); };
            this.Loaded += delegate { Position(); };
            this.Content = BuildContent(openSettings, exit);
        }

        private UIElement BuildContent(Action openSettings, Action exit)
        {
            Border border = new Border();
            border.Background = new SolidColorBrush(Color.FromRgb(0xF7, 0xF7, 0xF7));
            border.BorderBrush = new SolidColorBrush(Color.FromRgb(0xD8, 0xD8, 0xD8));
            border.BorderThickness = new Thickness(1);
            border.CornerRadius = new CornerRadius(8);
            border.Padding = new Thickness(6, 5, 6, 6);
            border.SnapsToDevicePixels = true;
            border.Effect = new DropShadowEffect
            {
                Color = Colors.Black,
                BlurRadius = 8,
                ShadowDepth = 2,
                Direction = 270,
                Opacity = 0.2
            };

            StackPanel stack = new StackPanel();
            stack.Margin = new Thickness(2);

            TextBlock title = new TextBlock();
            title.Text = "桌面诗词";
            title.FontFamily = new FontFamily("Microsoft YaHei");
            title.FontSize = 11;
            title.FontWeight = FontWeights.Bold;
            title.Foreground = new SolidColorBrush(Color.FromRgb(0x99, 0x99, 0x99));
            title.Margin = new Thickness(10, 5, 10, 3);
            stack.Children.Add(title);

            stack.Children.Add(MakeItem(this, "打开设置", openSettings));
            stack.Children.Add(MakeItem(this, "退出", exit));

            border.Child = stack;
            return border;
        }

        private static Button MakeItem(TrayMenuWindow w, string text, Action action)
        {
            Button b = new Button();
            b.Content = text;
            b.FontFamily = new FontFamily("Microsoft YaHei");
            b.FontSize = 12;
            b.Padding = new Thickness(10, 6, 10, 6);
            b.Margin = new Thickness(2, 1, 2, 1);
            b.MinWidth = 120;
            b.HorizontalContentAlignment = HorizontalAlignment.Left;
            b.Background = Brushes.Transparent;
            b.BorderThickness = new Thickness(0);
            b.Foreground = new SolidColorBrush(Color.FromRgb(0x33, 0x33, 0x33));
            b.Cursor = Cursors.Hand;
            b.Click += delegate
            {
                w.Close();
                if (action != null) action();
            };
            return b;
        }

        private void Position()
        {
            Rect wa = SystemParameters.WorkArea;
            double w = double.IsNaN(ActualWidth) ? 140 : ActualWidth;
            double h = double.IsNaN(ActualHeight) ? 80 : ActualHeight;
            this.Left = wa.Right - w - 6;
            this.Top = wa.Bottom - h - 8;
        }
    }
}
