from flask import Flask, request, send_file, jsonify
from handwriting_synthesis import Hand
import tempfile
import os

app = Flask(__name__)
hand = Hand()


@app.route('/handwrite', methods=['GET'])
def handwrite():
    text = request.args.get('text')
    if not text:
        return jsonify({'error': 'text parameter required'}), 400

    lines = text.split('\n')

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

    try:
        hand.write(
            filename=tmp_filename,
            lines=lines,
            biases=biases,
            styles=styles
        )
        return send_file(tmp_filename, mimetype='image/svg+xml')
    finally:
        if os.path.exists(tmp_filename):
            os.remove(tmp_filename)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

