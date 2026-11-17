// document.cpp
#include "document.h"
#include <QFile>
#include <QJsonDocument>
#include <QJsonArray>
#include <QDebug>

Document::Document() : m_image(new ImageHandler()) {}

Document::~Document() {
    delete m_image;
}

void Document::setImage(ImageHandler* image) {
    delete m_image;
    m_image = image;
}

ImageHandler* Document::getImage() const {
    return m_image;
}

void Document::setBasicInfo(const QMap<QString, QString>& info) {
    m_basicInfo = info;
}

QMap<QString, QString> Document::getBasicInfo() const {
    return m_basicInfo;
}

void Document::setTestResults(const QList<QMap<QString, QString>>& results) {
    m_testResults = results;
}

QList<QMap<QString, QString>> Document::getTestResults() const {
    return m_testResults;
}

bool Document::loadFromJson(const QString& filePath) {
    QFile file(filePath);
    if (!file.open(QIODevice::ReadOnly)) {
        qDebug() << "无法打开JSON文件:" << filePath;
        return false;
    }
    QByteArray data = file.readAll();
    QJsonDocument doc = QJsonDocument::fromJson(data);
    if (doc.isNull()) {
        qDebug() << "JSON解析失败";
        return false;
    }
    QJsonObject obj = doc.object();
    m_image->setPath(obj["imagePath"].toString());

    QJsonObject basicObj = obj["basicInfo"].toObject();
    for (auto it = basicObj.constBegin(); it != basicObj.constEnd(); ++it) {
        m_basicInfo[it.key()] = it.value().toString();
    }

    QJsonArray resultsArray = obj["testResults"].toArray();
    m_testResults.clear();
    for (const QJsonValue& val : resultsArray) {
        QJsonObject resObj = val.toObject();
        QMap<QString, QString> res;
        res["Item"] = resObj["Item"].toString();
        res["Result"] = resObj["Result"].toString();
        res["Reference Range"] = resObj["Reference Range"].toString();
        res["Unit"] = resObj["Unit"].toString();
        m_testResults.append(res);
    }
    return true;
}

bool Document::saveToJson(const QString& filePath) const {
    QJsonObject obj;
    obj["imagePath"] = m_image->getPath();

    QJsonObject basicObj;
    for (auto it = m_basicInfo.constBegin(); it != m_basicInfo.constEnd(); ++it) {
        basicObj[it.key()] = it.value();
    }
    obj["basicInfo"] = basicObj;

    QJsonArray resultsArray;
    for (const auto& res : m_testResults) {
        QJsonObject resObj;
        resObj["Item"] = res["Item"];
        resObj["Result"] = res["Result"];
        resObj["Reference Range"] = res["Reference Range"];
        resObj["Unit"] = res["Unit"];
        resultsArray.append(resObj);
    }
    obj["testResults"] = resultsArray;

    QJsonDocument doc(obj);
    QFile file(filePath);
    if (!file.open(QIODevice::WriteOnly)) {
        qDebug() << "无法写入JSON文件:" << filePath;
        return false;
    }
    file.write(doc.toJson());
    return true;
}
