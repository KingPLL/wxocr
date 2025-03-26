import wcocr
import os
import uuid
import base64
from flask import Flask, request, Response
import json
from pdf2image import convert_from_bytes
import tempfile
import threading  # 导入线程模块

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
wcocr.init("/app/wx/opt/wechat/wxocr", "/app/wx/opt/wechat")

# 异步删除文件函数
def async_remove(file_path):
    try:
        os.remove(file_path)
    except Exception as e:
        app.logger.error(f"删除文件失败: {file_path}, 错误: {str(e)}")

@app.route('/ocr', methods=['POST'])
def ocr():
    try:
        data = request.json
        if not data or 'key' not in data or 'value' not in data:
            return Response(
                json.dumps({'error': '无效的请求格式，预期格式: {"key": "pdf/img", "value": "base64"}'}, ensure_ascii=False),
                mimetype='application/json',
                status=400
            )

        file_type = data['key'].lower()
        file_data = data['value']

        if not file_data:
            return Response(
                json.dumps({'error': '未提供文件数据'}, ensure_ascii=False),
                mimetype='application/json',
                status=400
            )

        try:
            file_bytes = base64.b64decode(file_data)

            if file_type == 'pdf':
                images = convert_from_bytes(file_bytes)
                results = []

                for i, image in enumerate(images):
                    with tempfile.NamedTemporaryFile(suffix=f"_{i}.png", delete=False) as temp_image:
                        image.save(temp_image.name, 'PNG')
                        ocr_result = wcocr.ocr(temp_image.name)
                        results.append(ocr_result)
                    # 异步删除文件
                    threading.Thread(target=async_remove, args=(temp_image.name,)).start()

                return Response(
                    json.dumps({'result': results}, ensure_ascii=False),
                    mimetype='application/json'
                )

            elif file_type == 'img':
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_image:
                    temp_image.write(file_bytes)
                    temp_image.flush()
                    ocr_result = wcocr.ocr(temp_image.name)
                # 异步删除文件
                threading.Thread(target=async_remove, args=(temp_image.name,)).start()
                return Response(
                    json.dumps({'result': [ocr_result]}, ensure_ascii=False),
                    mimetype='application/json'
                )

            else:
                return Response(
                    json.dumps({'error': '不支持的文件类型，请使用pdf或img'}, ensure_ascii=False),
                    mimetype='application/json',
                    status=400
                )

        except Exception as e:
            return Response(
                json.dumps({'error': f'文件处理错误: {str(e)}'}, ensure_ascii=False),
                mimetype='application/json',
                status=500
            )

    except Exception as e:
        return Response(
            json.dumps({'error': f'服务器内部错误: {str(e)}'}, ensure_ascii=False),
            mimetype='application/json',
            status=500
        )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
