#include "loginwindow.h"
#include <QMessageBox>
#include <QTextEdit>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QFormLayout>
#include <QPixmap>
#include <QResizeEvent>

LoginWindow::LoginWindow(QWidget *parent) : QDialog(parent)
{
    setWindowTitle("医疗图像分析系统 - 登录");
    setFixedSize(500, 400);

    m_backgroundLabel = new QLabel(this);
    m_backgroundLabel->setObjectName("backgroundLabel");
    m_backgroundLabel->setScaledContents(true);  // 自适应大小
    m_backgroundLabel->lower();  // 置于最底层

    // 初始化背景图
    setBackgroundImage();

    // 创建主布局容器（用于覆盖在背景图上）
    mainWidget = new QWidget(this);  // 这里去掉了QWidget*声明，直接赋值给成员变量
    mainWidget->setStyleSheet("background-color: rgba(255, 255, 255, 0.85); border-radius: 8px;");
    mainWidget->setFixedSize(360, 260);

    // 创建主布局
    QVBoxLayout *mainLayout = new QVBoxLayout(mainWidget);
    mainLayout->setContentsMargins(50, 30, 50, 30);
    mainLayout->setSpacing(20);

    // 顶部区域：标题 + 帮助按钮
    QHBoxLayout *topLayout = new QHBoxLayout();

    // 添加标题
    QLabel *titleLabel = new QLabel("医疗图像分析系统");
    titleLabel->setStyleSheet("font-size: 24px; font-weight: bold; color: #165DFF;");
    topLayout->addWidget(titleLabel);

    // 添加帮助按钮（右上角）
    m_helpBtn = new QPushButton("帮助");
    m_helpBtn->setStyleSheet(
        "QPushButton {"
        "   background-color: transparent;"
        "   color: #165DFF;"
        "   border: none;"
        "   text-decoration: underline;"
        "   font-size: 15px;"
        "}"
        "QPushButton:hover {"
        "   color: #0E4CD1;"
        "}"
    );
    topLayout->addWidget(m_helpBtn);
    topLayout->setAlignment(m_helpBtn, Qt::AlignRight | Qt::AlignTop);

    mainLayout->addLayout(topLayout);

    // 创建表单布局用于输入区域
    QFormLayout *inputLayout = new QFormLayout();
    inputLayout->setRowWrapPolicy(QFormLayout::DontWrapRows);
    inputLayout->setLabelAlignment(Qt::AlignRight | Qt::AlignVCenter);
    inputLayout->setFormAlignment(Qt::AlignLeft);
    inputLayout->setSpacing(15);
    inputLayout->setFieldGrowthPolicy(QFormLayout::ExpandingFieldsGrow);

    // 用户名输入区域
    QLabel *userLabel = new QLabel("用户名:");
    userLabel->setStyleSheet("font-size: 17px;");
    m_usernameEdit = new QLineEdit();
    m_usernameEdit->setPlaceholderText("请输入用户名");
    m_usernameEdit->setFixedSize(180, 32);
    m_usernameEdit->setStyleSheet("padding: 6px; border: 1px solid #d0d7e3; border-radius: 4px; background-color: white;");
    inputLayout->addRow(userLabel, m_usernameEdit);

    // 密码输入区域
    QLabel *pwdLabel = new QLabel("密码:");
    pwdLabel->setStyleSheet("font-size: 17px;");
    m_passwordEdit = new QLineEdit();
    m_passwordEdit->setEchoMode(QLineEdit::Password);
    m_passwordEdit->setPlaceholderText("请输入密码");
    m_passwordEdit->setFixedSize(180, 32);
    m_passwordEdit->setStyleSheet("padding: 6px; border: 1px solid #d0d7e3; border-radius: 4px; background-color: white;");
    inputLayout->addRow(pwdLabel, m_passwordEdit);

    mainLayout->addLayout(inputLayout);

    // 错误提示标签
    m_errorLabel = new QLabel();
    m_errorLabel->setStyleSheet("color: #ff4d4f; font-size: 12px;");
    m_errorLabel->setAlignment(Qt::AlignCenter);
    mainLayout->addWidget(m_errorLabel);

    // 按钮区域
    QHBoxLayout *btnLayout = new QHBoxLayout();
    btnLayout->setSpacing(15);
    btnLayout->setAlignment(Qt::AlignCenter);

    // 登录按钮样式
    QString btnStyle =
        "QPushButton {"
        "   background-color: #165DFF;"
        "   color: white;"
        "   border-radius: 4px;"
        "   padding: 6px 12px;"
        "   font-size: 17px;"
        "}"
        "QPushButton:hover {"
        "   background-color: #0E4CD1;"
        "}"
        "QPushButton:pressed {"
        "   background-color: #0A3CA0;"
        "}";

    m_loginBtn = new QPushButton("登录");
    m_loginBtn->setStyleSheet(btnStyle);
    m_cancelBtn = new QPushButton("取消");
    m_cancelBtn->setStyleSheet(btnStyle);

    btnLayout->addWidget(m_loginBtn);
    btnLayout->addWidget(m_cancelBtn);
    mainLayout->addLayout(btnLayout);

    // 连接信号槽
    connect(m_loginBtn, &QPushButton::clicked, this, &LoginWindow::onLoginClicked);
    connect(m_cancelBtn, &QPushButton::clicked, this, &LoginWindow::onCancelClicked);
    connect(m_helpBtn, &QPushButton::clicked, this, &LoginWindow::onHelpClicked);

    // 初始居中主窗口部件
    int x = (this->width() - mainWidget->width()) / 2;
    int y = (this->height() - mainWidget->height()) / 2;
    mainWidget->move(x, y);
}

LoginWindow::~LoginWindow()
{
}

void LoginWindow::setBackgroundImage()
{
    // 加载背景图
    QPixmap background(":/3.png");

    if (!background.isNull()) {
        m_backgroundLabel->setPixmap(background);
        // 调整背景图大小以适应窗口
        m_backgroundLabel->resize(this->size());
    } else {
        // 如果图片加载失败，使用默认的浅灰色背景
        QPalette palette = this->palette();
        palette.setColor(QPalette::Window, QColor(245, 247, 249));
        this->setPalette(palette);
    }
}

void LoginWindow::resizeEvent(QResizeEvent *event)
{
    QDialog::resizeEvent(event);
    // 窗口大小改变时调整背景图
    m_backgroundLabel->resize(this->size());

    // 调整主容器位置居中
    if (mainWidget) {
        int x = (this->width() - mainWidget->width()) / 2;
        int y = (this->height() - mainWidget->height()) / 2;
        mainWidget->move(x, y);
    }
}

// 其他函数实现保持不变...
void LoginWindow::onHelpClicked()
{
    QDialog helpDialog(this);
    helpDialog.setWindowTitle("登录帮助");
    helpDialog.setFixedSize(400, 300);

    QTextEdit *helpText = new QTextEdit();
    helpText->setReadOnly(true);
    helpText->setHtml(
        "<p><strong>登录帮助</strong></p>"
        "<p>1. 用户名：系统分配的账号</p>"
        "<p>2. 密码：初始密码为88888888</p>"
        "<p>3. 忘记密码请联系管理员</p>"
        "<p>4. 联系电话：01234567890</p>"
        "<p>5. 管理员账号：admin"
    );

    QVBoxLayout *layout = new QVBoxLayout(&helpDialog);
    layout->addWidget(helpText);

    helpDialog.exec();
}

void LoginWindow::onLoginClicked()
{
    QString username = m_usernameEdit->text().trimmed();
    QString password = m_passwordEdit->text().trimmed();

    if (validateLogin(username, password)) {
        m_errorLabel->setText("");
        accept();
    } else {
        m_errorLabel->setText("用户名或密码错误，请重新输入");
        m_passwordEdit->clear();
    }
}

void LoginWindow::onCancelClicked()
{
    reject();
}

bool LoginWindow::validateLogin(const QString &username, const QString &password)
{
    return (username == "admin" && password == "88888888");
}
