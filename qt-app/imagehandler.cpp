// imagehandler.cpp
#include "imagehandler.h"

ImageHandler::ImageHandler(const QString& path) : m_path(path) {
    if (!path.isEmpty()) {
        m_pixmap.load(path);
    }
}

ImageHandler::~ImageHandler() {}

void ImageHandler::setPath(const QString& path) {
    m_path = path;
    m_pixmap.load(path);
}

QString ImageHandler::getPath() const {
    return m_path;
}

QPixmap ImageHandler::getPixmap() const {
    return m_pixmap;
}
