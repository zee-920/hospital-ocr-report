#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <QMainWindow>
#include <QLabel>
#include <QFormLayout>
#include <QLineEdit>
#include <QPushButton>
#include <QTableWidget>
#include <QSplitter>
#include <QMenu>
#include <QAction>
#include "document.h"
#include "pythoncaller.h"

class MainWindow : public QMainWindow {
    Q_OBJECT

public:
    MainWindow(QWidget *parent = nullptr);
    ~MainWindow();

private slots:
    void onLoadImage();
    void onRecognize();
    void onExport();
    void onSave();
    void onLoadProject();
    void onHistoryItemTriggered(); // 历史记录菜单项点击事件

private:
    void setupUi();
    void displayData();
    void parseCsv(const QString& csvPath);
    void clearForm();
    void updateHistoryMenu(); // 更新历史记录菜单

    QLabel* m_imageLabel;
    QFormLayout* m_formLayout;
    QWidget* m_rightWidget;
    QTableWidget* m_resultsTable;
    QPushButton* m_recognizeBtn;
    QPushButton* m_exportBtn;
    QPushButton* m_saveBtn;
    QPushButton* m_loadBtn;

    Document* m_currentDoc;
    PythonCaller* m_pythonCaller;
    QList<Document*> m_history;
    QSplitter* m_splitter;

    // 菜单相关成员
    QMenu* m_historyMenu;
    QAction* m_clearHistoryAction;
};

#endif // MAINWINDOW_H
