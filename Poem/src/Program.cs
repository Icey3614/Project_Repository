using System;
using System.Threading;
using System.Windows;
using System.Windows.Threading;

namespace LitePoem
{
    public static class Program
    {
        [STAThread]
        public static void Main()
        {
            bool createdNew;
            Mutex mutex = new Mutex(true, "LitePoem_SingleInstance_2019_Mutex", out createdNew);
            if (!createdNew)
            {
                return;
            }

            try
            {
                Application app = new Application();
                app.ShutdownMode = ShutdownMode.OnExplicitShutdown;
                app.DispatcherUnhandledException += delegate(object s, DispatcherUnhandledExceptionEventArgs e)
                {
                    e.Handled = true;
                };

                AppRoot root = new AppRoot(app);
                root.Start();

                app.Run();
            }
            finally
            {
                try { mutex.ReleaseMutex(); }
                catch { }
            }
        }
    }
}
