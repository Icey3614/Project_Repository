using System;
using System.Drawing;
using System.Drawing.Drawing2D;

namespace LitePoem
{
    public class TrayIcon : IDisposable
    {
        private System.Windows.Forms.NotifyIcon _ni;
        private TrayMenuWindow _menu;
        private Action _openSettings;
        private Action _exit;
        private bool _disposed;

        public TrayIcon(Action switchPoem, Action openSettings, Action exit)
        {
            _openSettings = openSettings;
            _exit = exit;

            _ni = new System.Windows.Forms.NotifyIcon();
            _ni.Icon = BuildIcon();
            _ni.Text = "桌面诗词";
            _ni.Visible = true;
            _ni.MouseUp += delegate(object sender, System.Windows.Forms.MouseEventArgs e)
            {
                if (e.Button == System.Windows.Forms.MouseButtons.Left)
                {
                    if (switchPoem != null) switchPoem();
                }
                else if (e.Button == System.Windows.Forms.MouseButtons.Right)
                {
                    ShowMenu();
                }
            };
        }

        private void ShowMenu()
        {
            if (_menu != null && _menu.IsVisible)
            {
                _menu.Close();
                _menu = null;
            }
            _menu = new TrayMenuWindow(_openSettings, _exit);
            _menu.Show();
            // 延迟到本轮输入处理完后再激活，确保能可靠拿到前台焦点，从而在点击其它位置时触发 Deactivated 自动关闭
            _menu.Dispatcher.BeginInvoke(new Action(delegate { _menu.Activate(); }), System.Windows.Threading.DispatcherPriority.Input);
        }

        public void SetTooltip(string text)
        {
            if (_ni != null && _ni.Text != text) _ni.Text = text;
        }

        private Icon BuildIcon()
        {
            Bitmap bmp = new Bitmap(32, 32);
            using (Graphics g = Graphics.FromImage(bmp))
            {
                g.SmoothingMode = SmoothingMode.AntiAlias;
                g.Clear(Color.Transparent);
                using (GraphicsPath path = RoundedRect(new RectangleF(1, 1, 30, 30), 8))
                using (SolidBrush seal = new SolidBrush(Color.FromArgb(220, 150, 40, 40)))
                {
                    g.FillPath(seal, path);
                }
                using (Font f = new Font("KaiTi", 22, System.Drawing.FontStyle.Bold, GraphicsUnit.Pixel))
                using (SolidBrush white = new SolidBrush(Color.White))
                using (StringFormat sf = new StringFormat())
                {
                    sf.Alignment = StringAlignment.Center;
                    sf.LineAlignment = StringAlignment.Center;
                    g.DrawString("诗", f, white, new RectangleF(0, 0, 32, 32), sf);
                }
            }
            IntPtr h = bmp.GetHicon();
            Icon icon = (Icon)Icon.FromHandle(h).Clone();
            bmp.Dispose();
            return icon;
        }

        private static GraphicsPath RoundedRect(RectangleF r, float radius)
        {
            GraphicsPath p = new GraphicsPath();
            float d = radius * 2;
            p.AddArc(r.X, r.Y, d, d, 180, 90);
            p.AddArc(r.Right - d, r.Y, d, d, 270, 90);
            p.AddArc(r.Right - d, r.Bottom - d, d, d, 0, 90);
            p.AddArc(r.X, r.Bottom - d, d, d, 90, 90);
            p.CloseFigure();
            return p;
        }

        public void Dispose()
        {
            if (_disposed) return;
            _disposed = true;
            if (_menu != null)
            {
                _menu.Close();
                _menu = null;
            }
            if (_ni != null)
            {
                _ni.Visible = false;
                _ni.Dispose();
                _ni = null;
            }
        }
    }
}
