#include "mainwindow.h"
#include "loginwindow.h"
#include <QApplication>

int main(int argc, char *argv[])
{
    QApplication a(argc, argv);

    // 设置全局字体，确保中文显示正常
    QFont font("SimHei", 10);
    a.setFont(font);

    // 先显示登录窗口
    LoginWindow loginWindow;
    // 如果登录成功（用户点击登录且验证通过）
    if (loginWindow.exec() == QDialog::Accepted) {
        // 实例化并显示主窗口
        MainWindow mainWindow;
        mainWindow.show();
        // 进入应用程序主循环
        return a.exec();
    } else {
        // 登录失败或取消登录，直接退出程序
        return 0;
    }
}
