from flask import Flask, make_response, request, jsonify, current_app
import json

import TableQA as tqa

app = Flask(__name__)
FLASK_RUN_PORT = 5000;

VIS_DICTIONARY_FILE_NAME = "./VisualAttributesDictionary.json"
VIS_BASE_DIR = "../data/vega-lite-example-gallery/runtime-data/"
WIKITABLEQUESTIONS_BASE_DIR = "../sempre/lib/data/WikiTableQuestions/"
BASE_DIR = "../"

@app.route("/query-vis-sempre", methods = ['GET'])
def query_vis_sempre():
    qa_system = tqa.TableQA(VIS_DICTIONARY_FILE_NAME, VIS_BASE_DIR)

    parsed_json = request.args
    session_id = parsed_json["sessionId"]
    question_id = parsed_json["questionId"]
    dataset_name = parsed_json["dataset"]
    spec_file_name = parsed_json["specFile"]
    runtime_file_name = parsed_json["runtimeFile"]

    qa_system.set_spec_handler_from_file(dataset_name, spec_file_name, runtime_file_name, BASE_DIR)
    query = parsed_json["query"]
    target_answer = parsed_json["answer"]

    vis_query, system_formula, system_answer = qa_system.answer_query(query, target_answer, "Sempre", True)

    result = {"sessionId": session_id, "questionId": question_id, "visQuery": vis_query, "systemAnswer": system_answer, "formula": system_formula}

    callback = request.args['callback']
    content = str(callback) + '(' + json.dumps(result) + ')'
    return current_app.response_class(content, mimetype='application/javascript')

if __name__ == '__main__':
    app.run(debug = True, port = FLASK_RUN_PORT)