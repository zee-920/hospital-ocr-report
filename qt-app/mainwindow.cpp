// mainwindow.cpp
#include "mainwindow.h"
#include <QFileDialog>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QDebug>
#include <QTextStream>
#include <QMessageBox>
#include <QHeaderView>
#include <QMenuBar>
#include <QProgressDialog>
#include <QApplication>
#include <QTimer>
#include <QProgressBar>

MainWindow::MainWindow(QWidget *parent) : QMainWindow(parent), m_currentDoc(new Document()),
    m_pythonCaller(new PythonCaller("D:/qtttt/Ocrregonized/ocr/.venv/Scripts/python.exe")) {
    setupUi();
}

MainWindow::~MainWindow() {
    delete m_currentDoc;
    delete m_pythonCaller;
    qDeleteAll(m_history);
}

void MainWindow::setupUi() {
    // 设置窗口标题和基本样式
    setWindowTitle("医疗图像分析系统");
    setMinimumSize(1024, 768);

    QString backgroundStyle =
        "QMainWindow {"
        "   background-image: url(:/2.png);"
        "   background-repeat: no-repeat;"
        "   background-position: center center;"
        "   background-attachment: fixed;"
        "}";
    setStyleSheet(backgroundStyle);

    m_splitter = new QSplitter(Qt::Horizontal, this);
    setCentralWidget(m_splitter);

    // 左侧：图像显示区域
    m_imageLabel = new QLabel();
    m_imageLabel->setAlignment(Qt::AlignCenter);
    m_imageLabel->setScaledContents(true);
    // 给图像显示区域添加白色背景和边框，确保不透明
    m_imageLabel->setStyleSheet("background-color: white; border: 1px solid #d0d7e3; border-radius: 4px;");
    m_splitter->addWidget(m_imageLabel);

    // 右侧：表单和表格
    m_rightWidget = new QWidget();
    // 右侧区域背景色 - 白色并添加轻微透明度，与背景图形成层次感
    m_rightWidget->setStyleSheet("background-color: rgba(255, 255, 255, 0.92); border-radius: 6px;");
    QVBoxLayout* rightLayout = new QVBoxLayout(m_rightWidget);
    rightLayout->setContentsMargins(15, 15, 15, 15);
    rightLayout->setSpacing(12);

    // 基本信息标题
    QLabel* basicLabel = new QLabel("基本信息");
    // 标题样式 - 深蓝色，加粗
    basicLabel->setStyleSheet("color: #165DFF; font-weight: bold; font-size: 18px;");
    rightLayout->addWidget(basicLabel);

    // 表单布局
    m_formLayout = new QFormLayout();
    m_formLayout->setRowWrapPolicy(QFormLayout::DontWrapRows);
    m_formLayout->setLabelAlignment(Qt::AlignRight | Qt::AlignVCenter);
    m_formLayout->setSpacing(10);
    rightLayout->addLayout(m_formLayout);

    // 测试结果标题
    QLabel* resultsLabel = new QLabel("检测结果");
    resultsLabel->setStyleSheet("color: #165DFF; font-weight: bold; font-size: 18px;");
    rightLayout->addWidget(resultsLabel);

    // 结果表格
    m_resultsTable = new QTableWidget();
    m_resultsTable->setColumnCount(4);
    m_resultsTable->setHorizontalHeaderLabels({"项目", "结果", "参考范围", "单位"});
    m_resultsTable->horizontalHeader()->setSectionResizeMode(QHeaderView::Stretch);
    m_resultsTable->setEditTriggers(QAbstractItemView::AllEditTriggers);
    // 表格样式 - 浅蓝色表头，细边框
    m_resultsTable->setStyleSheet(
        "QTableWidget {border: 1px solid #d0d7e3; border-radius: 4px; background-color: white;}"
        "QHeaderView::section {background-color: #e8f3ff; color: #165DFF; border: 1px solid #d0d7e3; padding: 5px;}"
        "QTableWidget::item {padding: 5px; border-bottom: 1px solid #f0f0f0;}"
        "QTableWidget::item:selected {background-color: #dceaff; color: #000;}"
    );
    rightLayout->addWidget(m_resultsTable);

    // 按钮区域
    QHBoxLayout* btnLayout = new QHBoxLayout();
    btnLayout->setSpacing(10);

    // 按钮样式 - 采用医院常用的蓝色系
    QString btnStyle =
        "QPushButton {"
        "   background-color: #165DFF;"
        "   color: white;"
        "   border-radius: 4px;"
        "   padding: 6px 12px;"
        "   font-size: 15px;"
        "}"
        "QPushButton:hover {"
        "   background-color: #0E4CD1;"
        "}"
        "QPushButton:pressed {"
        "   background-color: #0A3CA0;"
        "}"
        "QPushButton:disabled {"
        "   background-color: #a0b7e0;"
        "   color: #f0f0f0;"
        "}";

    QPushButton* loadImageBtn = new QPushButton("加载图像");
    m_recognizeBtn = new QPushButton("识别");
    m_exportBtn = new QPushButton("导出");
    m_saveBtn = new QPushButton("保存");
    m_loadBtn = new QPushButton("加载项目");

    // 应用按钮样式
    loadImageBtn->setStyleSheet(btnStyle);
    m_recognizeBtn->setStyleSheet(btnStyle);
    m_exportBtn->setStyleSheet(btnStyle);
    m_saveBtn->setStyleSheet(btnStyle);
    m_loadBtn->setStyleSheet(btnStyle);

    btnLayout->addWidget(loadImageBtn);
    btnLayout->addWidget(m_recognizeBtn);
    btnLayout->addWidget(m_exportBtn);
    btnLayout->addWidget(m_saveBtn);
    btnLayout->addWidget(m_loadBtn);
    rightLayout->addLayout(btnLayout);

    m_splitter->addWidget(m_rightWidget);

    // 连接信号槽
    connect(loadImageBtn, &QPushButton::clicked, this, &MainWindow::onLoadImage);
    connect(m_recognizeBtn, &QPushButton::clicked, this, &MainWindow::onRecognize);
    connect(m_exportBtn, &QPushButton::clicked, this, &MainWindow::onExport);
    connect(m_saveBtn, &QPushButton::clicked, this, &MainWindow::onSave);
    connect(m_loadBtn, &QPushButton::clicked, this, &MainWindow::onLoadProject);

    // 表格编辑信号：更新m_currentDoc
    connect(m_resultsTable, &QTableWidget::itemChanged, [this](QTableWidgetItem* item) {
        if (item) {
            int row = item->row();
            int col = item->column();
            if (row < m_currentDoc->getTestResults().size()) {
                QString key;
                switch (col) {
                case 0: key = "Item"; break;
                case 1: key = "Result"; break;
                case 2: key = "Reference Range"; break;
                case 3: key = "Unit"; break;
                default: return;
                }
                m_currentDoc->getTestResults()[row][key] = item->text();
            }
        }
    });

    m_splitter->setStretchFactor(0, 1);
    m_splitter->setStretchFactor(1, 1);

    QMenuBar* menuBar = this->menuBar();

        // 添加文件菜单
        QMenu* fileMenu = menuBar->addMenu("文件");

        // 添加打开文件动作
        QAction* openAction = new QAction("打开图像", this);
        connect(openAction, &QAction::triggered, this, &MainWindow::onLoadImage);
        fileMenu->addAction(openAction);

        // 添加保存动作
        QAction* saveAction = new QAction("保存项目", this);
        connect(saveAction, &QAction::triggered, this, &MainWindow::onSave);
        fileMenu->addAction(saveAction);

        // 添加导出动作
        QAction* exportAction = new QAction("导出数据", this);
        connect(exportAction, &QAction::triggered, this, &MainWindow::onExport);
        fileMenu->addAction(exportAction);

        fileMenu->addSeparator();

        // 添加退出动作
        QAction* exitAction = new QAction("退出", this);
        connect(exitAction, &QAction::triggered, this, &QMainWindow::close);
        fileMenu->addAction(exitAction);

        // 添加历史记录菜单
        m_historyMenu = menuBar->addMenu("历史记录");
        m_clearHistoryAction = new QAction("清除历史记录", this);
        connect(m_clearHistoryAction, &QAction::triggered, [this]() {
            qDeleteAll(m_history);
            m_history.clear();
            updateHistoryMenu();
        });

        // 初始更新历史记录菜单
        updateHistoryMenu();
}


void MainWindow::onLoadImage() {
    QString path = QFileDialog::getOpenFileName(this, "选择图像", "", "Images (*.jpg *.png)");
    if (!path.isEmpty()) {
        m_currentDoc->getImage()->setPath(path);
        m_imageLabel->setPixmap(m_currentDoc->getImage()->getPixmap());
    }
}

void MainWindow::onRecognize() {
    if (m_currentDoc->getImage()->getPath().isEmpty()) {
        QMessageBox::warning(this, "错误", "请先加载图像");
        return;
    }

    // 显示识别中提示
    QMessageBox processingMsg(this);
    processingMsg.setWindowTitle("...");
    processingMsg.setText("OCR正在识别中...");
    processingMsg.setStandardButtons(0);
    processingMsg.setFixedSize(500, 150);
    processingMsg.setStyleSheet(
        "QLabel{font-size: 16px; padding: 20px;}"
        "QMessageBox{background-color: white; border-radius: 6px;}"
    );
    processingMsg.setWindowModality(Qt::WindowModal);
    processingMsg.show();

    // 确保提示框显示
    QApplication::processEvents();
    QString csvPath;
    bool success = m_pythonCaller->callOcr(m_currentDoc->getImage()->getPath(), csvPath);

    // 关闭提示框
    processingMsg.close();

    if (success) {
        parseCsv(csvPath);
        displayData();
        m_history.append(new Document(*m_currentDoc));
    } else {
        QMessageBox::warning(this, "错误", "OCR识别失败");
    }
}

void MainWindow::parseCsv(const QString& csvPath) {
    QFile file(csvPath);
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        qDebug() << "无法打开CSV:" << csvPath;
        return;
    }
    QTextStream in(&file);
    in.setCodec("UTF-8");
    QString line;
    bool inBasic = false;
    bool inResults = false;
    QMap<QString, QString> basicInfo;
    QList<QMap<QString, QString>> testResults;

    while (!in.atEnd()) {
        line = in.readLine().trimmed();
        if (line.isEmpty()) continue; // 跳过空行

        if (line == "### Patient Basic Information") {
            inBasic = true;
            inResults = false;
            line = in.readLine().trimmed(); // 跳过 Key,Value
            if (line != "Key,Value") {
                qDebug() << "意外的基本信息标题:" << line;
            }
            continue;
        } else if (line == "### Test Results Table") {
            inBasic = false;
            inResults = true;
            line = in.readLine().trimmed(); // 跳过 Item,Result,Reference Range,Unit
            if (line != "Item,Result,Reference Range,Unit") {
                qDebug() << "意外的测试结果标题:" << line;
            }
            continue;
        }

        if (inBasic && !line.isEmpty()) {
            QStringList parts = line.split(',', QString::KeepEmptyParts);
            if (parts.size() >= 2) {
                QString key = parts[0].trimmed();
                QString value = parts.mid(1).join(",").trimmed();
                basicInfo[key] = value;
            }
        } else if (inResults && !line.isEmpty()) {
            QStringList parts = line.split(',', QString::KeepEmptyParts);
            if (parts.size() >= 4) {
                QMap<QString, QString> res;
                res["Item"] = parts[0].trimmed();
                res["Result"] = parts[1].trimmed();
                res["Reference Range"] = parts[2].trimmed();
                res["Unit"] = parts.mid(3).join(",").trimmed();
                testResults.append(res);
            }
        }
    }
    m_currentDoc->setBasicInfo(basicInfo);
    m_currentDoc->setTestResults(testResults);
}

void MainWindow::displayData() {
    clearForm();

    // 基本信息：使用QFormLayout + QLineEdit
    for (auto it = m_currentDoc->getBasicInfo().constBegin(); it != m_currentDoc->getBasicInfo().constEnd(); ++it) {
        QLineEdit* edit = new QLineEdit(it.value());
        m_formLayout->addRow(it.key(), edit);
        connect(edit, &QLineEdit::textChanged, [this, key = it.key()](const QString& text) {
            m_currentDoc->getBasicInfo()[key] = text;
        });
    }

    // 测试结果：使用QTableWidget，可编辑
    m_resultsTable->setRowCount(m_currentDoc->getTestResults().size());
    int row = 0;
    for (const auto& res : m_currentDoc->getTestResults()) {
        m_resultsTable->setItem(row, 0, new QTableWidgetItem(res["Item"]));
        m_resultsTable->setItem(row, 1, new QTableWidgetItem(res["Result"]));
        m_resultsTable->setItem(row, 2, new QTableWidgetItem(res["Reference Range"]));
        m_resultsTable->setItem(row, 3, new QTableWidgetItem(res["Unit"]));
        ++row;
    }
}

void MainWindow::clearForm() {
    while (m_formLayout->rowCount() > 0) {
        m_formLayout->removeRow(0);
    }
    m_resultsTable->clearContents();
    m_resultsTable->setRowCount(0);
}

void MainWindow::onExport() {
    QString path = QFileDialog::getSaveFileName(this, "导出数据", "", "JSON (*.json);;CSV (*.csv)");
    if (path.isEmpty()) return;

    if (path.endsWith(".json")) {
        m_currentDoc->saveToJson(path);
    } else if (path.endsWith(".csv")) {
        QFile file(path);
        if (file.open(QIODevice::WriteOnly | QIODevice::Text)) {
            QTextStream out(&file);
            out << "### Patient Basic Information\n";
            out << "Key,Value\n";
            for (auto it = m_currentDoc->getBasicInfo().constBegin(); it != m_currentDoc->getBasicInfo().constEnd(); ++it) {
                out << it.key() << "," << it.value() << "\n";
            }
            out << "\n### Test Results Table\n";
            out << "Item,Result,Reference Range,Unit\n";
            for (const auto& res : m_currentDoc->getTestResults()) {
                out << res["Item"] << "," << res["Result"] << "," << res["Reference Range"] << "," << res["Unit"] << "\n";
            }
        }
    }
}

void MainWindow::onSave() {
    QString path = QFileDialog::getSaveFileName(this, "保存项目", "", "JSON (*.json)");
    if (!path.isEmpty()) {
        m_currentDoc->saveToJson(path);
    }
}

void MainWindow::onLoadProject() {
    QString path = QFileDialog::getOpenFileName(this, "加载项目", "", "JSON (*.json)");
    if (!path.isEmpty()) {
        Document* newDoc = new Document();
        if (newDoc->loadFromJson(path)) {
            delete m_currentDoc;
            m_currentDoc = newDoc;
            m_imageLabel->setPixmap(m_currentDoc->getImage()->getPixmap());
            displayData();
            m_history.append(new Document(*m_currentDoc)); // 添加历史
            updateHistoryMenu();
        } else {
            delete newDoc;
        }
    }
}

void MainWindow::updateHistoryMenu() {
    // 清除现有历史记录菜单项（保留清除动作）
    QList<QAction*> actions = m_historyMenu->actions();
    foreach (QAction* action, actions) {
        if (action != m_clearHistoryAction) {
            m_historyMenu->removeAction(action);
            delete action;
        }
    }

    // 如果有历史记录，添加分隔符和历史项
    if (!m_history.isEmpty()) {
        m_historyMenu->addSeparator();

        // 倒序显示历史记录（最新的在前面）
        for (int i = m_history.size() - 1; i >= 0; --i) {
            Document* doc = m_history[i];
            QString imagePath = doc->getImage()->getPath();
            QString displayText = imagePath.isEmpty() ?
                QString("历史记录 %1").arg(i + 1) :
                QFileInfo(imagePath).fileName();

            QAction* action = new QAction(displayText, this);
            action->setData(i); // 存储索引，用于识别点击的是哪个历史项
            connect(action, &QAction::triggered, this, &MainWindow::onHistoryItemTriggered);
            m_historyMenu->addAction(action);
        }

        m_historyMenu->addSeparator();
    }

    // 添加清除历史记录动作
    m_historyMenu->addAction(m_clearHistoryAction);
    m_clearHistoryAction->setEnabled(!m_history.isEmpty());
}

void MainWindow::onHistoryItemTriggered() {
    QAction* action = qobject_cast<QAction*>(sender());
    if (!action) return;

    int index = action->data().toInt();
    if (index >= 0 && index < m_history.size()) {
        // 保存当前文档到历史记录
        m_history.append(new Document(*m_currentDoc));

        // 加载选中的历史文档
        delete m_currentDoc;
        m_currentDoc = new Document(*m_history[index]);

        // 更新界面显示
        m_imageLabel->setPixmap(m_currentDoc->getImage()->getPixmap());
        displayData();

        // 更新历史菜单
        updateHistoryMenu();
    }
}
