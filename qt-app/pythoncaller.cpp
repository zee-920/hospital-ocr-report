#include "pythoncaller.h"
#include <QDebug>
#include <QFileInfo>
#include <QMessageBox>
#include <QFile>
#include <QTextStream>
#include <QDir>
#include <QCoreApplication>

PythonCaller::PythonCaller(const QString& pythonPath) {
    m_pythonPath = pythonPath.isEmpty() ? "python" : pythonPath;

    QFileInfo pythonFile(m_pythonPath);
    if (!pythonFile.exists() || !pythonFile.isExecutable()) {
        qDebug() << "Python可执行文件不可用:" << m_pythonPath;
        QMessageBox::critical(nullptr, "错误",
            QString("Python可执行文件未找到或不可执行: %1\n请确保指定正确的Python路径").arg(m_pythonPath));
    }
}

PythonCaller::~PythonCaller() {}

bool PythonCaller::callOcr(const QString& imagePath, QString& csvPath) {
    QProcess process;
    QStringList args;
    args << "D:/qtttt/Ocrregonized/ocr/ocr.py" << imagePath << "split_ocr_results";

    QFileInfo scriptFile("D:/qtttt/Ocrregonized/ocr/ocr.py");
    if (!scriptFile.exists()) {
        qDebug() << "ocr.py脚本未找到";
        QMessageBox::critical(nullptr, "错误", "未找到ocr.py脚本，请确保其位于项目目录下");
        return false;
    }

    // 设置工作目录为应用程序目录
    QString workingDir = QCoreApplication::applicationDirPath();
    process.setWorkingDirectory(workingDir);
    qDebug() << "Python工作目录:" << workingDir;

    // 设置环境变量以强制 UTF-8
    QProcessEnvironment env = QProcessEnvironment::systemEnvironment();
    env.insert("PYTHONUTF8", "1");
    process.setProcessEnvironment(env);

    // 保存Python输出到日志文件
    QDir().mkpath("debug_logs");
    QFile logFile("debug_logs/python_output.txt");
    if (!logFile.open(QIODevice::WriteOnly | QIODevice::Text)) {
        qDebug() << "无法创建调试日志文件: debug_logs/python_output.txt";
    }
    QTextStream logStream(&logFile);

    process.start(m_pythonPath, args);
    if (!process.waitForStarted()) {
        qDebug() << "无法启动Python进程:" << process.errorString();
        QMessageBox::critical(nullptr, "错误",
            QString("无法启动Python进程: %1\n请检查Python环境").arg(process.errorString()));
        logStream << "无法启动Python进程: " << process.errorString() << "\n";
        logFile.close();
        return false;
    }

    if (!process.waitForFinished(-1)) {
        qDebug() << "Python调用失败:" << process.errorString();
        QMessageBox::critical(nullptr, "错误",
            QString("Python脚本执行失败: %1").arg(process.errorString()));
        logStream << "Python调用失败: " << process.errorString() << "\n";
        logFile.close();
        return false;
    }

    QByteArray stdoutOutput = process.readAllStandardOutput();
    QByteArray stderrOutput = process.readAllStandardError();
    QString stdoutStr = QString::fromUtf8(stdoutOutput);
    QString stderrStr = QString::fromUtf8(stderrOutput);
    qDebug() << "Python stdout:" << stdoutStr;
    qDebug() << "Python stderr:" << stderrStr;
    logStream << "Python stdout:\n" << stdoutStr << "\n";
    logStream << "Python stderr:\n" << stderrStr << "\n";

    // 规范化路径
    for (const QString& line : stdoutStr.split('\n')) {
        if (line.startsWith("CSV_PATH:")) {
            csvPath = QDir::cleanPath(line.mid(9).trimmed());
            break;
        }
    }

    if (csvPath.isEmpty()) {
        qDebug() << "未能解析CSV路径，检查Python脚本输出";
        QMessageBox::warning(nullptr, "警告",
            QString("OCR脚本未返回有效的CSV文件路径\nStderr: %1\n请检查debug_logs/python_output.txt和split_ocr_results/error_log.txt").arg(stderrStr));
        logStream << "未能解析CSV路径\n";
        logFile.close();
        return false;
    }

    // 使用绝对路径检查文件
    QFileInfo csvFile(QDir(workingDir).absoluteFilePath(csvPath));
    if (!csvFile.exists()) {
        qDebug() << "CSV文件不存在:" << csvFile.absoluteFilePath();
        QMessageBox::warning(nullptr, "警告",
            QString("CSV文件未找到: %1\n请检查split_ocr_results目录和debug_logs/python_output.txt").arg(csvFile.absoluteFilePath()));
        logStream << "CSV文件不存在: " << csvFile.absoluteFilePath() << "\n";
        logFile.close();
        return false;
    }

    csvPath = csvFile.absoluteFilePath(); // 返回绝对路径
    logStream << "成功解析CSV路径: " << csvPath << "\n";
    logFile.close();
    return true;
}
