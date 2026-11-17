import json
import re
import numpy as np
import os
from collections import OrderedDict
import csv
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("medical_report_parser.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MedicalReportParser")


class MedicalReportParser:
    def __init__(self, json_data):
        """
        初始化医疗报告解析器
        :param json_data: OCR生成的JSON数据
        """
        self.json_data = json_data
        self.patient_info = OrderedDict()
        self.test_items = []
        self.metadata = OrderedDict()

        # 医疗术语校正字典
        self.correction_map = {
            "结里": "结果",
            "百分军": "百分比",
            "拉细胞": "粒细胞",
            "健唐": "健康",
            "法": "浓度",
            "车": "率",
            "D{": "g/L",
            "EOS#": "嗜酸性粒细胞计数",
            "BAS#": "嗜碱性粒细胞计数",
            "MON#": "单核细胞计数",
            "LYM#": "淋巴细胞计数",
            "NEU#": "中性粒细胞计数",
            "浓": "浓度",
            "压积": "压积",
            "分布宽度": "分布宽度",
            "Ret": "网织红细胞计数",
            "BG": "血型",
            "RBC": "红细胞",
            "HGB": "血红蛋白",
            "HCT": "红细胞压积",
            "MCV": "红细胞平均体积",
            "MCH": "平均血红蛋白量",
            "MCHC": "平均血红蛋白浓度",
            "RDW-SD": "红细胞分布宽度SD",
            "RDW-CV": "红细胞分布宽度CV",
            "WBC": "白细胞",
            "NEU%": "中性粒百分比",
            "LYM%": "淋巴细胞百分比",
            "MON%": "单核细胞百分比",
            "EOS%": "嗜酸性粒百分比",
            "BAS%": "嗜碱性粒百分比",
            "PLT": "血小板",
            "PCT": "血小板压积",
            "MPV": "平均血小板体积",
            "PDW": "血小板分布宽度",
            "P-LCR": "大型血小板比率",
            "RET%": "网织红细胞百分"
        }

    def correct_text(self, text):
        """
        校正OCR识别错误
        :param text: 原始文本
        :return: 校正后的文本
        """
        if not text:
            return ""

        # 首先尝试匹配整个文本
        if text in self.correction_map:
            return self.correction_map[text]

        # 尝试匹配部分文本
        for wrong, correct in self.correction_map.items():
            if wrong in text:
                text = text.replace(wrong, correct)

        # 替换常见错误字符
        replacements = {
            "↑": "↑",
            "↓": "↓",
            "．": ".",
            "，": ",",
            "：": ":",
            "；": ";",
            "（": "(",
            "）": ")",
            "【": "[",
            "】": "]",
            "！": "!",
            "？": "?",
            "＠": "@",
            "＃": "#",
            "＄": "$",
            "％": "%",
            "＆": "&",
            "＊": "*",
            "＋": "+",
            "－": "-",
            "／": "/",
            "＜": "<",
            "＞": ">",
            "＝": "=",
            "～": "~",
            "＾": "^",
            "＿": "_",
            "｛": "{",
            "｝": "}",
            "｜": "|",
            "＼": "\\"
        }

        for wrong_char, correct_char in replacements.items():
            text = text.replace(wrong_char, correct_char)

        return text.strip()

    def extract_patient_info(self):
        """
        提取患者基本信息
        """
        texts = [self.correct_text(t) for t in self.json_data.get("rec_texts", [])]
        text_str = " ".join(texts)

        logger.info(f"提取患者信息文本: {text_str[:200]}...")

        # 使用正则表达式提取关键信息
        patterns = OrderedDict([
            ("姓名", r"姓名[：:]\s*([^\s]+)"),
            ("性别", r"性别[：:]\s*([男女])"),
            ("年龄", r"年龄[：:]\s*(\d+岁?)"),
            ("病历号", r"病历号[：:]\s*(\S+)"),
            ("科室", r"科室[：:]\s*([^\s]+)"),
            ("床号", r"床号[：:]\s*(\S+)"),
            ("费别", r"费别[：:]\s*([^\s]+)"),
            ("标本类型", r"标本类型[：:]\s*([^\s]+)"),
            ("送检医生", r"送检医生[：:]\s*([^\s]+)"),
            ("临床诊断", r"临床诊断[：:]\s*([^\)]+)"),
        ])

        for field, pattern in patterns.items():
            match = re.search(pattern, text_str)
            if match:
                self.patient_info[field] = match.group(1).strip()
                logger.debug(f"提取到患者信息: {field} = {self.patient_info[field]}")

        # 特殊处理年龄字段
        if "年龄" not in self.patient_info:
            age_match = re.search(r"年龄\s*(\d+)\s*岁", text_str)
            if age_match:
                self.patient_info["年龄"] = f"{age_match.group(1)}岁"
                logger.debug(f"提取到患者年龄: {self.patient_info['年龄']}")

    def extract_metadata(self):
        """
        提取报告元数据
        """
        texts = [self.correct_text(t) for t in self.json_data.get("rec_texts", [])]
        text_str = " ".join(texts)

        logger.info(f"提取报告元数据文本: {text_str[:200]}...")

        # 提取日期信息
        date_patterns = {
            "报告时间": r"报告时间[：:]\s*(\d{4}-\d{1,2}-\d{1,2}\s*\d{1,2}:\d{2}:\d{2})",
            "接收时间": r"接收时间[：:]\s*(\d{4}-\d{1,2}-\d{1,2}\s*\d{1,2}:\d{2}:\d{2})",
        }

        for field, pattern in date_patterns.items():
            match = re.search(pattern, text_str)
            if match:
                self.metadata[field] = match.group(1)
                logger.debug(f"提取到报告时间: {field} = {self.metadata[field]}")

        # 提取其他元数据
        other_patterns = {
            "检验者": r"检验者[：:]\s*([^\s]+)",
            "审核者": r"审核者[：:]\s*([^\s]+)",
            "检测仪器": r"检测仪器[：:]\s*([^\s]+)",
            "备注": r"备注[：:]\s*([^\)]+)"
        }

        for field, pattern in other_patterns.items():
            match = re.search(pattern, text_str)
            if match:
                self.metadata[field] = match.group(1).strip()
                logger.debug(f"提取到报告元数据: {field} = {self.metadata[field]}")

    def parse_table_data(self):
        """
        解析表格数据
        """
        texts = [self.correct_text(t) for t in self.json_data.get("rec_texts", [])]
        boxes = self.json_data.get("rec_boxes", [])

        if not texts or not boxes:
            logger.warning("缺少文本或坐标数据，无法解析表格")
            return

        logger.info(f"开始解析表格数据，共 {len(texts)} 项")

        # 查找表格开始位置
        table_start = None
        for i, text in enumerate(texts):
            if any(keyword in text for keyword in ["序代号", "项目名称", "结果", "参考范围", "RBC", "WBC", "HGB"]):
                table_start = i
                logger.debug(f"找到表格起始位置: {i} - {text}")
                break

        if table_start is None:
            logger.warning("未找到表格起始位置")
            return

        # 查找表格结束位置
        table_end = None
        for i in range(table_start, len(texts)):
            if any(keyword in texts[i] for keyword in ["报告时间", "检验者", "审核者", "接收时间", "检测仪器"]):
                table_end = i
                logger.debug(f"找到表格结束位置: {i} - {texts[i]}")
                break

        if table_end is None:
            table_end = len(texts)
            logger.debug(f"未找到表格结束位置，使用文本末尾: {table_end}")

        # 提取表格内容
        table_texts = texts[table_start:table_end]
        table_boxes = boxes[table_start:table_end]

        logger.info(f"表格区域: {table_start}-{table_end}, 共 {len(table_texts)} 项")

        # 按行分组
        rows = {}
        for i, (text, box) in enumerate(zip(table_texts, table_boxes)):
            if not box or len(box) < 8:
                continue

            try:
                # 计算行中心Y坐标
                y_center = (box[1] + box[3] + box[5] + box[7]) / 4

                if y_center not in rows:
                    rows[y_center] = []
                rows[y_center].append((text, box, i))
            except Exception as e:
                logger.error(f"处理坐标时出错: {e}, box={box}")

        if not rows:
            logger.warning("未找到有效的行数据")
            return

        logger.info(f"识别到 {len(rows)} 行数据")

        # 处理每一行
        for y_center in sorted(rows.keys()):
            row_items = rows[y_center]
            # 按X坐标排序
            row_items.sort(key=lambda x: x[1][0])

            # 跳过表头行
            if any("项目名称" in item[0] or "参考范围" in item[0] for item in row_items):
                logger.debug(f"跳过表头行: {[item[0] for item in row_items]}")
                continue

            logger.debug(f"处理行数据: {[item[0] for item in row_items]}")

            # 分割左右列
            if len(row_items) < 2:
                # 单列处理
                left_items = row_items
                right_items = []
            else:
                # 计算中间点
                x_coords = [item[1][0] for item in row_items]
                mid_x = np.median(x_coords)

                left_items = [item for item in row_items if item[1][0] < mid_x]
                right_items = [item for item in row_items if item[1][0] >= mid_x]

            # 解析左列项目
            if left_items:
                left_texts = [item[0] for item in left_items]
                left_item = self.parse_table_item(left_texts)
                if left_item:
                    self.test_items.append(left_item)
                    logger.debug(f"添加左列项目: {left_item}")

            # 解析右列项目
            if right_items:
                right_texts = [item[0] for item in right_items]
                right_item = self.parse_table_item(right_texts)
                if right_item:
                    self.test_items.append(right_item)
                    logger.debug(f"添加右列项目: {right_item}")

    def parse_table_item(self, texts):
        """
        解析表格中的单个项目
        """
        if not texts:
            return None

        item = {}

        # 1. 提取序号
        for i, text in enumerate(texts):
            if re.match(r'^\d+$', text):
                item['序号'] = text
                texts = texts[i + 1:]
                break

        # 2. 提取项目名称（可能包含英文缩写和中文名称）
        name_parts = []
        for i, text in enumerate(texts):
            if re.match(r'^[A-Za-z#%]+$', text) or re.search(r'[\u4e00-\u9fa5]', text):
                name_parts.append(text)
            else:
                break

        if name_parts:
            item['项目名称'] = ' '.join(name_parts)
            texts = texts[len(name_parts):]

        # 3. 提取结果值
        for i, text in enumerate(texts):
            if re.match(r'^[\d\.]+$', text) or ('↑' in text or '↓' in text):
                item['结果'] = text
                texts = texts[i + 1:]
                break

        # 4. 提取参考范围和单位
        if texts:
            ref_text = ' '.join(texts)
            # 分离单位和参考范围
            if re.search(r'[a-zA-Z/%]', ref_text):
                # 尝试分离单位和参考范围
                parts = re.split(r'(\d+\.?\d*\-+\d+\.?\d*)', ref_text)
                if len(parts) >= 3:
                    item['参考范围'] = parts[1]
                    item['单位'] = parts[2].strip()
                else:
                    item['参考范围'] = ref_text
            else:
                item['参考范围'] = ref_text

        return item if '项目名称' in item else None

    def mark_abnormal_values(self):
        """
        标记异常检查结果
        """
        logger.info("标记异常检查结果")
        abnormal_count = 0

        for item in self.test_items:
            if "结果" in item and "参考范围" in item:
                try:
                    # 提取数值结果（去除箭头符号）
                    result_value = re.sub(r'[↑↓]', '', item["结果"])
                    result_num = float(result_value)

                    # 解析参考范围
                    ref_range = item["参考范围"]
                    ref_range = ref_range.replace(" ", "").replace("，", ",").replace("、", ",")

                    # 处理不同分隔符
                    if "--" in ref_range:
                        parts = ref_range.split("--")
                    elif "-" in ref_range:
                        parts = ref_range.split("-")
                    elif "~" in ref_range:
                        parts = ref_range.split("~")
                    else:
                        continue

                    if len(parts) >= 2:
                        low = float(parts[0])
                        high = float(parts[1])

                        if result_num < low:
                            item["状态"] = "↓偏低"
                            abnormal_count += 1
                        elif result_num > high:
                            item["状态"] = "↑偏高"
                            abnormal_count += 1
                except (ValueError, IndexError):
                    # 无法解析数值时跳过
                    pass

        logger.info(f"标记了 {abnormal_count} 个异常结果")

    def parse(self):
        """
        执行解析流程
        :return: 结构化数据字典
        """
        logger.info("开始解析医疗报告")
        start_time = datetime.now()

        try:
            self.extract_patient_info()
            self.extract_metadata()
            self.parse_table_data()
            self.mark_abnormal_values()

            result = {
                "patient_info": dict(self.patient_info),
                "metadata": dict(self.metadata),
                "test_items": self.test_items
            }

            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"解析完成，耗时 {duration:.2f} 秒")
            logger.info(f"提取患者信息: {len(self.patient_info)} 项")
            logger.info(f"提取报告元数据: {len(self.metadata)} 项")
            logger.info(f"提取检查项目: {len(self.test_items)} 项")

            return result
        except Exception as e:
            logger.error(f"解析过程中发生错误: {str(e)}")
            return {
                "error": str(e),
                "patient_info": dict(self.patient_info),
                "metadata": dict(self.metadata),
                "test_items": self.test_items
            }

    def format_output(self, data):
        """
        格式化输出结果
        :param data: 结构化数据
        :return: 格式化字符串
        """
        output = []

        # 患者信息
        output.append("=" * 80)
        output.append("患者信息")
        output.append("=" * 80)
        for field, value in data["patient_info"].items():
            output.append(f"{field:8}: {value}")

        # 报告元数据
        if data["metadata"]:
            output.append("\n" + "=" * 80)
            output.append("报告信息")
            output.append("=" * 80)
            for field, value in data["metadata"].items():
                output.append(f"{field:8}: {value}")

        # 检查项目
        output.append("\n" + "=" * 80)
        output.append("检查项目")
        output.append("=" * 80)

        # 表头
        headers = ["序号", "项目名称", "结果", "参考范围", "单位", "状态"]
        header_line = f"{headers[0]:<6}{headers[1]:<25}{headers[2]:<10}{headers[3]:<20}{headers[4]:<10}{headers[5]:<8}"
        output.append(header_line)
        output.append("-" * len(header_line.expandtabs()))

        # 表格内容
        for item in data["test_items"]:
            # 获取各项值，如果不存在则使用空字符串
            item_no = item.get("序号", "")
            name = item.get("项目名称", "")
            result = item.get("结果", "")
            ref_range = item.get("参考范围", "")
            unit = item.get("单位", "")
            status = item.get("状态", "")

            row = f"{item_no:<6}{name:<25}{result:<10}{ref_range:<20}{unit:<10}{status:<8}"
            output.append(row)

        return "\n".join(output)

    def export_to_csv(self, data, filename="medical_report.csv"):
        """
        导出为CSV格式
        :param data: 结构化数据
        :param filename: 输出文件名
        :return: 生成的文件路径
        """
        try:
            csv_content = "类别,字段,值\n"

            # 患者信息
            csv_content += "患者信息,,\n"
            for field, value in data["patient_info"].items():
                csv_content += f"患者信息,{field},{value}\n"

            # 报告元数据
            if data["metadata"]:
                csv_content += "报告信息,,\n"
                for field, value in data["metadata"].items():
                    csv_content += f"报告信息,{field},{value}\n"

            # 检查项目
            csv_content += "检查项目,,\n"
            csv_content += "序号,项目名称,结果,参考范围,单位,状态\n"

            for item in data["test_items"]:
                row = [
                    item.get("序号", ""),
                    item.get("项目名称", ""),
                    item.get("结果", ""),
                    item.get("参考范围", ""),
                    item.get("unit", ""),
                    item.get("状态", "")
                ]
                csv_content += ",".join(f'"{value}"' for value in row) + "\n"

            with open(filename, "w", encoding="utf-8-sig") as f:
                f.write(csv_content)

            logger.info(f"CSV报告已生成: {filename}")
            return os.path.abspath(filename)
        except Exception as e:
            logger.error(f"导出CSV时出错: {str(e)}")
            return None


def process_medical_report(json_file_path):
    """
    处理医疗报告JSON文件
    :param json_file_path: JSON文件路径
    :return: 处理结果字典
    """
    # 检查文件是否存在
    if not os.path.exists(json_file_path):
        logger.error(f"文件不存在: {json_file_path}")
        return {"error": f"文件不存在: {json_file_path}"}

    try:
        # 读取JSON文件
        with open(json_file_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)

        logger.info(f"成功读取JSON文件: {json_file_path}")

        # 创建解析器
        parser = MedicalReportParser(json_data)

        # 执行解析
        structured_data = parser.parse()

        # 格式化输出
        formatted_output = parser.format_output(structured_data)

        # 导出为CSV
        base_name = os.path.splitext(os.path.basename(json_file_path))[0]
        csv_file = parser.export_to_csv(structured_data, f"{base_name}.csv")

        # 保存文本报告
        txt_file = f"{base_name}.txt"
        with open(txt_file, "w", encoding="utf-8") as f:
            f.write(formatted_output)
        logger.info(f"文本报告已保存: {txt_file}")

        return {
            "structured_data": structured_data,
            "formatted_output": formatted_output,
            "csv_file": csv_file,
            "txt_file": os.path.abspath(txt_file),
            "status": "success"
        }
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析错误: {str(e)}")
        return {"error": f"JSON解析错误: {str(e)}"}
    except Exception as e:
        logger.error(f"处理过程中发生错误: {str(e)}")
        return {"error": f"处理过程中发生错误: {str(e)}"}


# 使用示例
if __name__ == "__main__":
    # 输入JSON文件路径
    json_file_path = "./output/R_res.json"  # 替换为实际文件路径

    # 处理医疗报告
    result = process_medical_report(json_file_path)

    if "error" in result:
        print(f"处理失败: {result['error']}")
    else:
        print("=" * 80)
        print("医疗报告解析结果")
        print("=" * 80)
        print(f"结构化数据已生成，包含 {len(result['structured_data']['test_items'])} 个检查项目")
        print(f"文本报告已保存至: {result['txt_file']}")
        print(f"CSV报告已保存至: {result['csv_file']}")

        # 打印部分格式化输出
        print("\n部分报告内容预览:")
        print(result['formatted_output'][:1000] + "...")