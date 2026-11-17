#ifndef LOGINWINDOW_H
#define LOGINWINDOW_H

#include <QDialog>
#include <QLineEdit>
#include <QPushButton>
#include <QLabel>

class LoginWindow : public QDialog
{
    Q_OBJECT

public:
    explicit LoginWindow(QWidget *parent = nullptr);
    ~LoginWindow();

private slots:
    void onLoginClicked();
    void onCancelClicked();
    void onHelpClicked();

protected:
    void resizeEvent(QResizeEvent *event) override;

private:
    QLineEdit *m_usernameEdit;  // 用户名输入框
    QLineEdit *m_passwordEdit;  // 密码输入框
    QPushButton *m_loginBtn;    // 登录按钮
    QPushButton *m_cancelBtn;   // 取消按钮
    QPushButton *m_helpBtn;     // 帮助按钮
    QLabel *m_errorLabel;       // 错误提示标签
    QLabel *m_backgroundLabel;
    QWidget *mainWidget;// 背景图标签

    bool validateLogin(const QString &username, const QString &password);
    // 设置背景图的方法
    void setBackgroundImage();
};

#endif // LOGINWINDOW_H

