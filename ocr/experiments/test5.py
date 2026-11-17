import cv2
import numpy as np
import json
import os
from paddleocr import PaddleOCR
from datetime import datetime
import pandas as pd
import re
from typing import List, Dict, Tuple

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
        return int(np.median(center_indices) + 50)  # 向右偏移 50 像素
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
    """执行 OCR 并直接保存 JSON（模仿 test.py 的 ocr.predict 和 res.save_to_json）"""
    try:
        results = ocr.predict(image_path)
        if not results:
            print(f"OCR 处理失败 ({image_path}): 无结果返回")
            with open(os.path.join('split_ocr_results', 'error_log.txt'), 'a', encoding='utf-8') as f:
                f.write(f"[{datetime.now()}] OCR错误: 无结果返回\n")
            return None

        text_count = 0
        for res in results:
            res.print()
            text_count += 1
        print(f"OCR 结果 ({image_path}): {text_count} 条文本")

        for res in results:
            res.save_to_json(json_path)
            break
        return json_path
    except Exception as e:
        print(f"OCR 或 JSON 保存失败 ({image_path}): {str(e)}")
        with open(os.path.join('split_ocr_results', 'error_log.txt'), 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now()}] OCR或JSON保存错误: {str(e)}\n")
        return None


def parse_ocr_json(json_path: str, basic_info: Dict[str, str] = None, test_results: List[Dict[str, str]] = None) -> \
Tuple[Dict[str, str], List[Dict[str, str]]]:
    """解析 OCR JSON 文件（基于 test0.py，优化表格解析和基本信息提取）"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"无法读取 JSON 文件 ({json_path}): {str(e)}")
        return basic_info or {}, test_results or []

    texts = [t.strip() for t in data.get('rec_texts', []) if t.strip()]
    print(f"JSON 文件 ({json_path}) 提取文本: {texts}")

    if basic_info is None:
        basic_info = {}
    if test_results is None:
        test_results = []

    correction_rules = {
        '百分车': '百分比',
        '拉': '粒',
        '暗碱性': '嗜碱性',
        r'\*': '',  # 去除多余的 * 字符
        'E0%': 'EO%',
        'M0%': 'MO%',
        '2/L': 'g/L',
        '£1': 'fL',
        'tL': 'fL',
        'PD鄂': 'PDW',
        'NRBCX': 'NRBC%',
        'MRBC#': 'NRBC#'
    }

    # 表头检测：优先连续表头
    table_start_idx = -1
    header_keywords = ["项目", "item", "结果", "result", "参考值", "参考范围", "reference", "单位", "unit"]
    for i in range(len(texts) - 3):
        if (texts[i].lower() in ["项目", "item"] and
                texts[i + 1].lower() in ["结果", "result"] and
                texts[i + 2].lower() in ["参考值", "参考范围", "reference"] and
                texts[i + 3].lower() in ["单位", "unit"]):
            table_start_idx = i
            print(f"检测到连续表头 ({json_path}): {texts[i:i + 4]}")
            break

    # 收集基本信息
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

    # 解析检测结果
    if table_start_idx != -1:
        i = table_start_idx + 4  # 跳过表头
        while i < len(texts):
            if re.match(r'^\d+$', texts[i]):  # 纯数字编号
                i += 1
                if i >= len(texts):
                    print(f"表格解析终止 ({json_path}): 缺少 project")
                    break
                project = texts[i].strip()
            elif re.match(r'^\d+', texts[i]):  # 编号+项目
                project = re.sub(r'^\d+', '', texts[i]).strip()
            else:
                project = texts[i].strip()

            for error, correct in correction_rules.items():
                project = project.replace(error, correct)

            print(f"解析表格行 ({json_path}): project={project}")

            i += 1
            if i >= len(texts):
                print(f"表格解析终止 ({json_path}): 缺少 result")
                break
            result = texts[i].strip()
            print(f"  result={result}")

            i += 1
            if i >= len(texts):
                print(f"表格解析终止 ({json_path}): 缺少 reference")
                break
            reference = texts[i].strip()
            print(f"  reference={reference}")

            i += 1
            if i >= len(texts):
                print(f"表格解析终止 ({json_path}): 缺少 unit")
                break
            unit = texts[i].strip()
            for error, correct in correction_rules.items():
                unit = unit.replace(error, correct)
            print(f"  unit={unit}")

            if any(keyword in project.lower() for keyword in ["日期", "注", "方法", "检验者", "审核者", "健康"]):
                if "日期" in project and project not in basic_info:
                    basic_info[project] = result
                print(f"跳过非表格数据 ({json_path}): {project}")
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


def generate_txt(basic_info: Dict[str, str], test_results: List[Dict[str, str]], txt_path: str):
    """生成 TXT 文件"""
    try:
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write("### Patient Basic Information\n")
            f.write("| Key | Value |\n")
            f.write("|-----|-------|\n")
            for key, value in basic_info.items():
                f.write(f"| {key} | {value} |\n")
            f.write("\n### Test Results Table\n")
            f.write("| Item | Result | Reference Range | Unit |\n")
            f.write("|------|--------|-----------------|------|\n")
            for res in test_results:
                f.write(f"| {res['Item']} | {res['Result']} | {res['Reference Range']} | {res['Unit']} |\n")
    except Exception as e:
        print(f"生成 TXT 文件失败 ({txt_path}): {str(e)}")


def generate_xlsx(basic_info: Dict[str, str], test_results: List[Dict[str, str]], xlsx_path: str):
    """生成 XLSX 文件"""
    try:
        import xlsxwriter
    except ImportError:
        raise ImportError("未安装 'xlsxwriter' 模块，请使用 'pip install xlsxwriter' 安装。")

    try:
        writer = pd.ExcelWriter(xlsx_path, engine='xlsxwriter')
        basic_df = pd.DataFrame(list(basic_info.items()), columns=['Key', 'Value'])
        basic_df.to_excel(writer, sheet_name='Basic Info', index=False)
        results_df = pd.DataFrame(test_results)
        results_df.to_excel(writer, sheet_name='Test Results', index=False)
        writer.close()
    except Exception as e:
        print(f"生成 XLSX 文件失败 ({xlsx_path}): {str(e)}")


def main(image_path: str, output_dir: str = 'split_ocr_results'):
    """主函数：处理医疗检查单图像，分割、OCR、解析并生成文件"""
    os.makedirs(output_dir, exist_ok=True)
    error_log = os.path.join(output_dir, 'error_log.txt')

    try:
        # Step 1: Split the image
        left_img_path, right_img_path = split_image(image_path, output_dir)
        print(f"图像分割完成: {left_img_path}, {right_img_path}")

        # Step 2: Perform OCR and save JSON
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = os.path.basename(image_path).split('.')[0]
        left_json_path = os.path.join(output_dir, f"{base_name}_left_{timestamp}_res.json")
        right_json_path = os.path.join(output_dir, f"{base_name}_right_{timestamp}_res.json")

        left_json_path = perform_ocr_and_save_json(left_img_path, left_json_path)
        right_json_path = perform_ocr_and_save_json(right_img_path, right_json_path)

        if not left_json_path or not right_json_path:
            raise Exception("JSON 文件生成失败，请检查错误信息")

        # Step 3: Parse JSON and merge
        basic_info, test_results = parse_ocr_json(left_json_path)
        basic_info, test_results = parse_ocr_json(right_json_path, basic_info, test_results)

        # Debug: Check parsed results
        print(f"合并后基本信息条目: {len(basic_info)}")
        print(f"合并后检测结果条目: {len(test_results)}")

        if not test_results:
            print("警告: 未提取到检测结果，可能表格未正确识别")

        # Step 4: Generate output files
        txt_path = os.path.join(output_dir, f"{base_name}_merged_{timestamp}.txt")
        xlsx_path = os.path.join(output_dir, f"{base_name}_merged_{timestamp}.xlsx")

        generate_txt(basic_info, test_results, txt_path)
        generate_xlsx(basic_info, test_results, xlsx_path)

        print(f"处理完成！输出文件位于: {output_dir}")
        print(f"左半部分图片: {left_img_path}")
        print(f"右半部分图片: {right_img_path}")
        print(f"左半部分 JSON: {left_json_path}")
        print(f"右半部分 JSON: {right_json_path}")
        print(f"合并 TXT: {txt_path}")
        print(f"合并 XLSX: {xlsx_path}")

    except Exception as e:
        print(f"处理失败: {str(e)}")
        with open(error_log, 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now()}] 处理错误: {str(e)}\n")


if __name__ == "__main__":
    input_image = "D:/qtttt/Ocrregonized/res/4.png"
    main(input_image)