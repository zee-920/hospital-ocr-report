// imagehandler.h
#ifndef IMAGEHANDLER_H
#define IMAGEHANDLER_H

#include <QString>
#include <QPixmap>

class ImageHandler {
public:
    ImageHandler(const QString& path = "");
    ~ImageHandler();

    void setPath(const QString& path);
    QString getPath() const;
    QPixmap getPixmap() const;

private:
    QString m_path;
    QPixmap m_pixmap;
};

#endif // IMAGEHANDLER_H
