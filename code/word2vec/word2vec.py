from flask import Flask, make_response, request, jsonify
import json
import gensim

# Key parameters
app = Flask(__name__)
FLASK_RUN_PORT = 5005
model_path = "./model/GoogleNews-vectors-negative300.bin"
model = None

@app.route("/", methods=['POST'])
def compute_similarity():
    parsed_json = json.loads(request.form['stringifiedData'])
    word1 = parsed_json['word1']
    word2 = parsed_json['word2']
    try:
        similarity = model.similarity(word1, word2)
    except Exception:
        similarity = 0.0
    finally:
        result = {"similarity": str(similarity)}
        if "thresh" in parsed_json:
            thresh = parsed_json['thresh']
            if similarity > thresh:
                result['passedThresh'] = 1
            else:
                result['passedThresh'] = 0
        resp = jsonify(result)
        resp.headers['Content-Type'] = "application/json"
        resp.headers['Access-Control-Allow-Origin'] = "*"
        return resp

def load_model():
    global model
    print("Loading pre-trained model... (This will take a few minutes)")
    model = gensim.models.KeyedVectors.load_word2vec_format(model_path, binary=True)
    print("Done loading!")

if __name__ == '__main__':
    load_model()
    app.run(debug = True, port = FLASK_RUN_PORT)