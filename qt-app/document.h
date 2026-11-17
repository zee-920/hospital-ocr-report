// document.h
#ifndef DOCUMENT_H
#define DOCUMENT_H

#include "imagehandler.h"
#include <QMap>
#include <QList>
#include <QJsonObject>

class Document {
public:
    Document();
    ~Document();

    void setImage(ImageHandler* image);
    ImageHandler* getImage() const;

    void setBasicInfo(const QMap<QString, QString>& info);
    QMap<QString, QString> getBasicInfo() const;

    void setTestResults(const QList<QMap<QString, QString>>& results);
    QList<QMap<QString, QString>> getTestResults() const;

    bool loadFromJson(const QString& filePath);
    bool saveToJson(const QString& filePath) const;

private:
    ImageHandler* m_image;
    QMap<QString, QString> m_basicInfo;
    QList<QMap<QString, QString>> m_testResults; // 每个map: "Item", "Result", "Reference Range", "Unit"
};

#endif // DOCUMENT_H
