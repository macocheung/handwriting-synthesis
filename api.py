from flask import Flask, request, send_file, jsonify
from handwriting_synthesis import Hand
import tempfile
import os
import zipfile
import cairosvg

app = Flask(__name__)
hand = Hand()


@app.route('/handwrite', methods=['GET'])
def handwrite():
    text = request.args.get('text')
    if not text:
        return jsonify({'error': 'text parameter required'}), 400

    lines = text.split('\n')

    fmt = request.args.get('format', 'svg').lower()
    if fmt not in ('svg', 'png'):
        return jsonify({'error': 'format must be svg or png'}), 400

    style = request.args.get('style')
    bias = request.args.get('bias')

    styles = None
    biases = None

    if style is not None:
        try:
            style_index = int(style)
            styles = [style_index for _ in lines]
        except ValueError:
            return jsonify({'error': 'style must be an integer'}), 400

    if bias is not None:
        try:
            bias_value = float(bias)
            biases = [bias_value for _ in lines]
        except ValueError:
            return jsonify({'error': 'bias must be a float'}), 400

    with tempfile.NamedTemporaryFile(suffix='.svg', delete=False) as tmp:
        tmp_filename = tmp.name
    if fmt == 'png':
        png_tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        png_filename = png_tmp.name
        png_tmp.close()

    try:
        hand.write(
            filename=tmp_filename,
            lines=lines,
            biases=biases,
            styles=styles
        )
        if fmt == 'png':
            cairosvg.svg2png(url=tmp_filename, write_to=png_filename)
            return send_file(png_filename, mimetype='image/png')
        else:
            return send_file(tmp_filename, mimetype='image/svg+xml')
    finally:
        if os.path.exists(tmp_filename):
            os.remove(tmp_filename)
        if fmt == 'png' and os.path.exists(png_filename):
            os.remove(png_filename)


@app.route('/handwrite_batch', methods=['POST'])
def handwrite_batch():
    data = request.get_json()
    if not data or 'texts' not in data:
        return jsonify({'error': 'texts parameter required'}), 400

    texts = data['texts']
    if not isinstance(texts, list) or len(texts) == 0:
        return jsonify({'error': 'texts must be a non-empty list'}), 400

    fmt = data.get('format', 'svg').lower()
    if fmt not in ('svg', 'png'):
        return jsonify({'error': 'format must be svg or png'}), 400

    style_param = data.get('styles')
    bias_param = data.get('biases')

    style_list = None
    bias_list = None

    if style_param is not None:
        try:
            if isinstance(style_param, list):
                if len(style_param) != len(texts):
                    return jsonify({'error': 'styles length must match texts'}), 400
                style_list = [int(s) for s in style_param]
            else:
                style_index = int(style_param)
                style_list = [style_index for _ in texts]
        except (ValueError, TypeError):
            return jsonify({'error': 'styles must be integers'}), 400

    if bias_param is not None:
        try:
            if isinstance(bias_param, list):
                if len(bias_param) != len(texts):
                    return jsonify({'error': 'biases length must match texts'}), 400
                bias_list = [float(b) for b in bias_param]
            else:
                bias_value = float(bias_param)
                bias_list = [bias_value for _ in texts]
        except (ValueError, TypeError):
            return jsonify({'error': 'biases must be floats'}), 400

    temp_dir = tempfile.mkdtemp()
    filenames = []
    try:
        for idx, text in enumerate(texts):
            lines = text.split('\n')
            styles = [style_list[idx] for _ in lines] if style_list is not None else None
            biases = [bias_list[idx] for _ in lines] if bias_list is not None else None
            out_file = os.path.join(temp_dir, f'{idx}.svg')
            hand.write(
                filename=out_file,
                lines=lines,
                biases=biases,
                styles=styles
            )
            if fmt == 'png':
                png_file = os.path.join(temp_dir, f'{idx}.png')
                cairosvg.svg2png(url=out_file, write_to=png_file)
                filenames.append(png_file)
                os.remove(out_file)
            else:
                filenames.append(out_file)

        zip_filename = tempfile.NamedTemporaryFile(suffix='.zip', delete=False).name
        with zipfile.ZipFile(zip_filename, 'w') as zf:
            for f in filenames:
                zf.write(f, arcname=os.path.basename(f))

        return send_file(zip_filename, mimetype='application/zip', as_attachment=True, download_name='images.zip')
    finally:
        for f in filenames:
            if os.path.exists(f):
                os.remove(f)
        if os.path.exists(temp_dir):
            try:
                os.rmdir(temp_dir)
            except OSError:
                pass
        if 'zip_filename' in locals() and os.path.exists(zip_filename):
            os.remove(zip_filename)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

