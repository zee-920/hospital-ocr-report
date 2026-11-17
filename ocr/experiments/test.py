from paddleocr import PaddleOCR

ocr = PaddleOCR(
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
    text_detection_model_name="PP-OCRv5_mobile_det",
    text_recognition_model_name="PP-OCRv5_mobile_rec",
    text_detection_model_dir="D:/qtttt/Ocrregonized/PP-OCRv5_mobile_det_infer",
    text_recognition_model_dir="D:/qtttt/Ocrregonized/PP-OCRv5_mobile_rec_infer"
)

result = ocr.predict("./split_ocr_results/90_right_20250909_232607.jpg")
for res in result:
    res.print()
    res.save_to_img("output")
    res.save_to_json("output")

"""from paddleocr import TableStructureRecognition
model = TableStructureRecognition(model_name="SLANet_plus", model_dir="D:/OCR/SLANet_plus_infer")  # 启用高性能推理
output = model.predict(input="90.jpg", batch_size=4)  # 支持批量处理
for res in output:
    res.save_to_json("./output/medical_data.json")  # 输出结构化JSON，便于后续处理
"""

correction_rules = {
    # 常见形近字/错别字矫正
    '白细包': '白细胞',
    '红细包': '红细胞',
    '血小扳': '血小板',
    '脂纺': '脂肪',
    '淋吧': '淋巴',
    '嗜硷性': '嗜碱性',
    # 英文/符号混淆矫正
    'WBCx': 'WBC#',
    'RBCx': 'RBC#',
    'PLTx': 'PLT#',
    'HGBt': 'HGB',
    'HCT%': 'HCT',
    'MCVf': 'MCVfL',
    # 特殊字符/冗余信息去除
    r'\*': '',
    r'\#': '',
    r'\?': '',
}