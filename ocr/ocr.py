import cv2
import numpy as np
import json
import os
from paddleocr import PaddleOCR
from datetime import datetime
import pandas as pd
import re
from typing import List, Dict, Tuple
import sys
import traceback

# 初始化 OCR 引擎
try:
    ocr = PaddleOCR(
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        text_detection_model_name="PP-OCRv5_mobile_det",
        text_recognition_model_name="PP-OCRv5_mobile_rec",
        text_detection_model_dir="D:/qtttt/Ocrregonized/PP-OCRv5_mobile_det_infer",
        text_recognition_model_dir="D:/qtttt/Ocrregonized/PP-OCRv5_mobile_rec_infer"
    )
except Exception as e:
    raise Exception(f"初始化 PaddleOCR 失败: {str(e)}")

def find_split_line(img):
    """智能检测分割线位置，优先保留表格完整性"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)
    projection = np.sum(binary, axis=0)
    min_val = np.min(projection)
    min_indices = np.where(projection == min_val)[0]
    width = img.shape[1]
    center_indices = [x for x in min_indices if width // 4 < x < 3 * width // 4]
    if center_indices:
        return int(np.median(center_indices) + 50)
    edges = cv2.Canny(binary, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100, minLineLength=100, maxLineGap=10)
    if lines is not None:
        vertical_lines = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if abs(x1 - x2) < 5:
                vertical_lines.append((x1 + x2) // 2)
        center_lines = [x for x in vertical_lines if width // 3 < x < 2 * width // 3]
        if center_lines:
            return int(np.mean(center_lines))
    return width // 2

def split_image(image_path, output_dir):
    """分割图像并保存结果"""
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"无法读取图像: {image_path}")
    split_point = find_split_line(img)
    left_img = img[:, :split_point]
    right_img = img[:, split_point:]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = os.path.basename(image_path).split('.')[0]
    left_path = os.path.join(output_dir, f"{base_name}_left_{timestamp}.jpg")
    right_path = os.path.join(output_dir, f"{base_name}_right_{timestamp}.jpg")
    cv2.imwrite(left_path, left_img)
    cv2.imwrite(right_path, right_img)
    return left_path, right_path

def perform_ocr_and_save_json(image_path, json_path):
    """执行 OCR 并直接保存 JSON"""
    try:
        results = ocr.predict(image_path)
        if not results:
            with open(os.path.join('split_ocr_results', 'error_log.txt'), 'a', encoding='utf-8') as f:
                f.write(f"[{datetime.now()}] OCR错误: 无结果返回 ({image_path})\n")
            return None
        text_count = 0
        for res in results:
            text_count += 1
        with open(os.path.join('split_ocr_results', 'debug_log.txt'), 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now()}] OCR 结果 ({image_path}): {text_count} 条文本\n")
        for res in results:
            res.save_to_json(json_path)
            break
        return json_path
    except Exception as e:
        with open(os.path.join('split_ocr_results', 'error_log.txt'), 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now()}] OCR或JSON保存错误 ({image_path}): {str(e)}\n")
        return None

def parse_ocr_json(json_path: str, basic_info: Dict[str, str] = None, test_results: List[Dict[str, str]] = None) -> \
Tuple[Dict[str, str], List[Dict[str, str]]]:
    """解析 OCR JSON 文件"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        with open(os.path.join('split_ocr_results', 'error_log.txt'), 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now()}] 无法读取 JSON 文件 ({json_path}): {str(e)}\n")
        return basic_info or {}, test_results or []

    texts = [t.strip() for t in data.get('rec_texts', []) if t.strip()]
    # 将调试输出写入文件而非打印到控制台
    with open(os.path.join('split_ocr_results', 'debug_log.txt'), 'a', encoding='utf-8') as f:
        f.write(f"[{datetime.now()}] JSON 文件 ({json_path}) 提取文本: {texts}\n")

    if basic_info is None:
        basic_info = {}
    if test_results is None:
        test_results = []

    correction_rules = {
        '百分车': '百分比',
        '拉': '粒',
        '暗碱性': '嗜碱性',
        r'\*': '',
        'E0%': 'EO%',
        'M0%': 'MO%',
        '2/L': 'g/L',
        '£': 'fL',
        '\xa3': 'fL',
        'tL': 'fL',
        'PD鄂': 'PDW',
        'NRBCX': 'NRBC%',
        'MRBC#': 'NRBC#'
    }

    table_start_idx = -1
    header_keywords = ["项目", "item", "结果", "result", "参考值", "参考范围", "reference", "单位", "unit"]
    for i in range(len(texts) - 3):
        if (texts[i].lower() in ["项目", "item"] and
                texts[i + 1].lower() in ["结果", "result"] and
                texts[i + 2].lower() in ["参考值", "参考范围", "reference"] and
                texts[i + 3].lower() in ["单位", "unit"]):
            table_start_idx = i
            with open(os.path.join('split_ocr_results', 'debug_log.txt'), 'a', encoding='utf-8') as f:
                f.write(f"[{datetime.now()}] 检测到连续表头 ({json_path}): {texts[i:i + 4]}\n")
            break

    valid_basic_keys = ['接收时间', '医院', '条码号', '姓名', '性别', '病历号', '科别', '申请医生', '病区', '检验日期',
                        '报告日期', '样本编号', '床号', '采集时间', '临床诊断', '年龄', '备注']
    units = ['g/L', '%', 'fL', 'pg', '$10^9/L', '10^9/L', '10^12/L']
    i = 0
    while i < len(texts):
        text = texts[i]
        if text.endswith('：') or text.endswith(':'):
            key = text[:-1].strip()
            if (re.match(r'^-?\d+$', key) or
                    key in ["结果", "参考值", "单位"] or
                    key in units or
                    re.match(r'.*\(.*\).*', key)):
                i += 1
                continue
            i += 1
            if i < len(texts):
                value = texts[i].strip()
                for error, correct in correction_rules.items():
                    value = value.replace(error, correct)
                if key in valid_basic_keys and key not in basic_info:
                    basic_info[key] = value
                i += 1
                continue
        else:
            if ("医院" in text or re.match(r'^[A-Za-z\s]+$', text)) and len(text) > 2 and '医院' not in basic_info:
                basic_info['医院'] = text
        i += 1

    if '年龄' not in basic_info:
        basic_info['年龄'] = '*'
    if '备注' not in basic_info:
        basic_info['备注'] = '*'

    if table_start_idx != -1:
        i = table_start_idx + 4
        while i < len(texts):
            if re.match(r'^\d+$', texts[i]):
                i += 1
                if i >= len(texts):
                    with open(os.path.join('split_ocr_results', 'debug_log.txt'), 'a', encoding='utf-8') as f:
                        f.write(f"[{datetime.now()}] 表格解析终止 ({json_path}): 缺少 project\n")
                    break
                project = texts[i].strip()
            elif re.match(r'^\d+', texts[i]):
                project = re.sub(r'^\d+', '', texts[i]).strip()
            else:
                project = texts[i].strip()

            for error, correct in correction_rules.items():
                project = project.replace(error, correct)

            with open(os.path.join('split_ocr_results', 'debug_log.txt'), 'a', encoding='utf-8') as f:
                f.write(f"[{datetime.now()}] 解析表格行 ({json_path}): project={project}\n")

            i += 1
            if i >= len(texts):
                with open(os.path.join('split_ocr_results', 'debug_log.txt'), 'a', encoding='utf-8') as f:
                    f.write(f"[{datetime.now()}] 表格解析终止 ({json_path}): 缺少 result\n")
                break
            result = texts[i].strip()
            with open(os.path.join('split_ocr_results', 'debug_log.txt'), 'a', encoding='utf-8') as f:
                f.write(f"[{datetime.now()}]   result={result}\n")

            i += 1
            if i >= len(texts):
                with open(os.path.join('split_ocr_results', 'debug_log.txt'), 'a', encoding='utf-8') as f:
                    f.write(f"[{datetime.now()}] 表格解析终止 ({json_path}): 缺少 reference\n")
                break
            reference = texts[i].strip()
            with open(os.path.join('split_ocr_results', 'debug_log.txt'), 'a', encoding='utf-8') as f:
                f.write(f"[{datetime.now()}]   reference={reference}\n")

            i += 1
            if i >= len(texts):
                with open(os.path.join('split_ocr_results', 'debug_log.txt'), 'a', encoding='utf-8') as f:
                    f.write(f"[{datetime.now()}] 表格解析终止 ({json_path}): 缺少 unit\n")
                break
            unit = texts[i].strip()
            for error, correct in correction_rules.items():
                unit = unit.replace(error, correct)
            with open(os.path.join('split_ocr_results', 'debug_log.txt'), 'a', encoding='utf-8') as f:
                f.write(f"[{datetime.now()}]   unit={unit}\n")

            if any(keyword in project.lower() for keyword in ["日期", "注", "方法", "检验者", "审核者", "健康"]):
                if "日期" in project and project not in basic_info:
                    basic_info[project] = result
                with open(os.path.join('split_ocr_results', 'debug_log.txt'), 'a', encoding='utf-8') as f:
                    f.write(f"[{datetime.now()}] 跳过非表格数据 ({json_path}): {project}\n")
                i += 1
                continue

            test_results.append({
                'Item': project,
                'Result': result,
                'Reference Range': reference,
                'Unit': unit
            })
            i += 1

    valid_results = []
    for res in test_results:
        if (re.match(r'.*\(.*\).*', res['Item']) or len(res['Item']) > 5) and res['Item'] not in basic_info and res[
            'Item'] not in units:
            valid_results.append(res)
        elif res['Item'] not in basic_info and res['Item'] not in units:
            basic_info[res['Item']] = res['Result']
    test_results[:] = valid_results

    return basic_info, test_results

def generate_csv(basic_info: Dict[str, str], test_results: List[Dict[str, str]], csv_path: str):
    """生成 CSV 文件，确保使用 UTF-8 编码并处理特殊字符"""
    try:
        def sanitize(text: str) -> str:
            replacements = {
                '£': 'fL',
                '\xa3': 'fL',
                '\u201c': '"',
                '\u201d': '"',
                '\u2018': "'",
                '\u2019': "'",
            }
            for old, new in replacements.items():
                text = text.replace(old, new)
            text = ''.join(c for c in text if ord(c) < 0x10000)
            return text

        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            f.write("### Patient Basic Information\n")
            f.write("Key,Value\n")
            for key, value in basic_info.items():
                f.write(f"{sanitize(key)},{sanitize(value)}\n")
            f.write("\n### Test Results Table\n")
            f.write("Item,Result,Reference Range,Unit\n")
            for res in test_results:
                f.write(f"{sanitize(res['Item'])},{sanitize(res['Result'])},{sanitize(res['Reference Range'])},{sanitize(res['Unit'])}\n")
        return True
    except Exception as e:
        with open(os.path.join('split_ocr_results', 'error_log.txt'), 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now()}] 生成 CSV 文件失败 ({csv_path}): {str(e)}\n")
        return False

def main(image_path: str, output_dir: str = 'split_ocr_results'):
    """主函数：处理医疗检查单图像，分割、OCR、解析并生成文件"""
    os.makedirs(output_dir, exist_ok=True)
    error_log = os.path.join(output_dir, 'error_log.txt')
    debug_log = os.path.join(output_dir, 'debug_log.txt')
    csv_path = None

    try:
        # 使用绝对路径
        output_dir = os.path.abspath(output_dir)
        image_path = os.path.abspath(image_path)
        os.makedirs(output_dir, exist_ok=True)

        # 记录输入参数
        with open(debug_log, 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now()}] 处理图像: {image_path}, 输出目录: {output_dir}\n")

        left_img_path, right_img_path = split_image(image_path, output_dir)
        with open(debug_log, 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now()}] 图像分割完成: {left_img_path}, {right_img_path}\n")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = os.path.basename(image_path).split('.')[0]
        left_json_path = os.path.join(output_dir, f"{base_name}_left_{timestamp}_res.json")
        right_json_path = os.path.join(output_dir, f"{base_name}_right_{timestamp}_res.json")

        left_json_path = perform_ocr_and_save_json(left_img_path, left_json_path)
        right_json_path = perform_ocr_and_save_json(right_img_path, right_json_path)

        if not left_json_path or not right_json_path:
            raise Exception("JSON 文件生成失败，请检查错误信息")

        basic_info, test_results = parse_ocr_json(left_json_path)
        basic_info, test_results = parse_ocr_json(right_json_path, basic_info, test_results)

        with open(debug_log, 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now()}] 合并后基本信息条目: {len(basic_info)}\n")
            f.write(f"[{datetime.now()}] 合并后检测结果条目: {len(test_results)}\n")

        if not test_results:
            with open(debug_log, 'a', encoding='utf-8') as f:
                f.write(f"[{datetime.now()}] 警告: 未提取到检测结果，可能表格未正确识别\n")

        csv_path = os.path.join(output_dir, f"{base_name}_merged_{timestamp}.csv")
        if not generate_csv(basic_info, test_results, csv_path):
            raise Exception("CSV 文件生成失败")

        with open(debug_log, 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now()}] 处理完成！输出文件位于: {output_dir}\n")
            f.write(f"[{datetime.now()}] 左半部分图片: {left_img_path}\n")
            f.write(f"[{datetime.now()}] 右半部分图片: {right_img_path}\n")
            f.write(f"[{datetime.now()}] 左半部分 JSON: {left_json_path}\n")
            f.write(f"[{datetime.now()}] 右半部分 JSON: {right_json_path}\n")
            f.write(f"[{datetime.now()}] CSV_PATH: {csv_path}\n")

        # 输出绝对路径到 stdout
        print(f"CSV_PATH:{os.path.abspath(csv_path)}")

    except Exception as e:
        with open(error_log, 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now()}] 处理错误: {str(e)}\n")
            f.write(f"[{datetime.now()}] 完整错误信息:\n{traceback.format_exc()}\n")
        if csv_path:
            print(f"CSV_PATH:{os.path.abspath(csv_path)}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        input_image = "D:/qtttt/Ocrregonized/res/90.jpg"
        main(input_image)
    else:
        image_path = sys.argv[1]
        output_dir = sys.argv[2] if len(sys.argv) > 2 else 'split_ocr_results'
        main(image_path, output_dir)