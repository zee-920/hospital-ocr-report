import cv2
import numpy as np
import json
import os
from paddleocr import PaddleOCR
from datetime import datetime


class MedicalReportSplitter:
    """医疗化验单分割与OCR验证系统 - 修复版本"""

    def __init__(self):
        # 初始化OCR引擎
        self.ocr = PaddleOCR(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            text_detection_model_name="PP-OCRv5_mobile_det",
            text_recognition_model_name="PP-OCRv5_mobile_rec",
            text_detection_model_dir="D:/qtttt/Ocrregonized/PP-OCRv5_mobile_det_infer",
            text_recognition_model_dir="D:/qtttt/Ocrregonized/PP-OCRv5_mobile_rec_infer"
        )

        # 创建输出目录
        self.output_dir = "split_ocr_results"
        os.makedirs(self.output_dir, exist_ok=True)

        # 创建错误日志
        self.error_log = os.path.join(self.output_dir, "error_log.txt")

    def find_split_line(self, img):
        """智能检测分割线位置"""
        # 转换为灰度图
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 二值化处理
        _, binary = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)

        # 方法1: 垂直投影法
        projection = np.sum(binary, axis=0)
        min_val = np.min(projection)
        min_indices = np.where(projection == min_val)[0]

        # 筛选中间区域的空白列
        width = img.shape[1]
        center_indices = [x for x in min_indices if width // 4 < x < 3 * width // 4]

        if center_indices:
            return int(np.median(center_indices))

        # 方法2: 边缘检测法
        edges = cv2.Canny(binary, 50, 150)
        lines = cv2.HoughLinesP(
            edges, 1, np.pi / 180, threshold=100,
            minLineLength=100, maxLineGap=10
        )

        if lines is not None:
            vertical_lines = []
            for line in lines:
                x1, y1, x2, y2 = line[0]
                if abs(x1 - x2) < 5:  # 近似垂直线
                    vertical_lines.append((x1 + x2) // 2)

            if vertical_lines:
                center_lines = [x for x in vertical_lines if width // 3 < x < 2 * width // 3]
                if center_lines:
                    return int(np.mean(center_lines))

        # 默认中间分割
        return width // 2

    def split_image(self, image_path):
        """分割图像并保存结果"""
        # 读取图像
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"无法读取图像: {image_path}")

        # 检测分割线
        split_point = self.find_split_line(img)

        # 分割图像
        left_img = img[:, :split_point]
        right_img = img[:, split_point:]

        # 添加分割线标记
        marked_img = img.copy()
        cv2.line(marked_img, (split_point, 0), (split_point, img.shape[0]), (0, 0, 255), 2)

        # 保存结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = os.path.basename(image_path).split('.')[0]

        # 原始图像带分割线
        marked_path = os.path.join(self.output_dir, f"{base_name}_marked_{timestamp}.jpg")
        cv2.imwrite(marked_path, marked_img)

        # 左半部分
        left_path = os.path.join(self.output_dir, f"{base_name}_left_{timestamp}.jpg")
        cv2.imwrite(left_path, left_img)

        # 右半部分
        right_path = os.path.join(self.output_dir, f"{base_name}_right_{timestamp}.jpg")
        cv2.imwrite(right_path, right_img)

        return {
            "marked_image": marked_path,
            "left_image": left_path,
            "right_image": right_path,
            "split_point": split_point
        }

    def safe_ocr(self, image_path):
        """安全的OCR处理"""
        try:
            return self.ocr.ocr(image_path)
        except Exception as e:
            # 记录错误
            with open(self.error_log, "a") as f:
                f.write(f"[{datetime.now()}] OCR错误: {str(e)}\n")
            return None

    def process_ocr_results(self, ocr_results):
        """处理OCR结果并提取文本和置信度 - 修复版本"""
        processed = []

        # 检查结果是否为空
        if ocr_results is None:
            return processed

        # 遍历所有识别结果
        for result in ocr_results:
            # 检查结果是否有效
            if result is None:
                continue

            for line in result:
                # 跳过空行
                if not line:
                    continue

                try:
                    # 提取坐标点
                    points = line[0]

                    # 提取文本信息
                    text_info = line[1]

                    # 处理不同格式的文本信息
                    if isinstance(text_info, tuple):
                        # 格式: (文本, 置信度)
                        text = text_info[0]
                        confidence = text_info[1] if len(text_info) > 1 else 1.0
                    elif isinstance(text_info, str):
                        # 格式: 文本
                        text = text_info
                        confidence = 1.0
                    elif isinstance(text_info, list) and len(text_info) >= 2:
                        # 格式: [文本, 置信度]
                        text = text_info[0]
                        confidence = text_info[1]
                    else:
                        # 未知格式，跳过
                        continue

                    # 添加到结果列表
                    processed.append({
                        "points": points.tolist() if isinstance(points, np.ndarray) else points,
                        "text": text,
                        "confidence": confidence
                    })

                except Exception as e:
                    # 记录错误但继续处理
                    with open(self.error_log, "a") as f:
                        f.write(f"[{datetime.now()}] 处理OCR结果错误: {str(e)}\n")
                    continue

        return processed

    def ocr_to_json(self, image_path, output_json):
        """执行OCR并将结果保存为JSON - 修复版本"""
        # 执行OCR
        ocr_results = self.safe_ocr(image_path)

        # 处理OCR结果
        ocr_data = self.process_ocr_results(ocr_results)

        # 保存为JSON
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(ocr_data, f, ensure_ascii=False, indent=2)

        return ocr_data

    def process_report(self, image_path):
        """处理医疗化验单并生成验证报告 - 修复版本"""
        try:
            # 分割图像
            split_info = self.split_image(image_path)

            # 对左右部分分别进行OCR
            left_json = os.path.join(self.output_dir, "left_ocr.json")
            right_json = os.path.join(self.output_dir, "right_ocr.json")

            left_data = self.ocr_to_json(split_info["left_image"], left_json)
            right_data = self.ocr_to_json(split_info["right_image"], right_json)

            # 生成验证报告
            report = {
                "original_image": image_path,
                "split_info": split_info,
                "left_ocr_results": left_json,
                "right_ocr_results": right_json,
                "statistics": {
                    "left_text_count": len(left_data),
                    "right_text_count": len(right_data),
                    "total_text_count": len(left_data) + len(right_data)
                }
            }

            # 保存报告
            report_path = os.path.join(self.output_dir, "validation_report.json")
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

            return report_path

        except Exception as e:
            # 记录错误
            with open(self.error_log, "a") as f:
                f.write(f"[{datetime.now()}] 处理报告错误: {str(e)}\n")
            return None


# 使用示例
if __name__ == "__main__":
    # 输入图像路径
    input_image = "D:/qtttt/Ocrregonized/res/R.jpg"

    # 创建分割验证系统
    splitter = MedicalReportSplitter()

    # 处理医疗化验单
    report_path = splitter.process_report(input_image)

    if report_path:
        print(f"处理完成！验证报告已保存至: {report_path}")
        print(f"所有输出文件位于: {splitter.output_dir}")
    else:
        print("处理失败，请查看错误日志:", splitter.error_log)