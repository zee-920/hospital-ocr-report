#ifndef PYTHONCALLER_H
#define PYTHONCALLER_H

#include <QProcess>
#include <QString>

class PythonCaller {
public:
    PythonCaller(const QString& pythonPath = "");
    ~PythonCaller();

    bool callOcr(const QString& imagePath, QString& csvPath);

private:
    QString m_pythonPath;
};

#endif // PYTHONCALLER_H
