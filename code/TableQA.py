import re
import csv
import requests
import CoreNLPLayer as cnlplayer
import SpecHandler as shandler
import VisualAttributeHandler as vahandler

def parse_sempre_answer(sempre_answer):
    if sempre_answer[:5] != "(list":
        raise RuntimeError("Unknown sempre answer format: " + sempre_answer)
    sempre_answer = sempre_answer[5 : len(sempre_answer) - 1]
    list_elems_raw = sempre_answer.split(") (")
    list_elems_raw[0] = list_elems_raw[0][2:]
    list_elems_raw[-1] = list_elems_raw[-1][:-1]
    list_elems = []
    for elem in list_elems_raw:
        first_space_idx = elem.find(" ")
        elem_type = elem[:first_space_idx]
        elem_content = elem[first_space_idx + 1:]
        if elem_type == "date":
            year, month, day = elem_content.split(" ")
            if month == "-1" and day == "-1":
                elem_content = year
            elif day == "-1":
                elem_content = year + " " + MONTHS_OF_THE_YEAR[month]
            elif year == "-1" and day == "-1":
                elem_content = MONTHS_OF_THE_YEAR[month]
            elif year == "-1":
                elem_content = MONTHS_OF_THE_YEAR[month] + " " + day
            else:
                elem_content = MONTHS_OF_THE_YEAR[month] + " " + day + ", " + year
        elif elem_content[-1] == '"':
            content_begin_idx = elem_content.find('"')
            elem_content = elem_content[content_begin_idx + 1 : -1]
        else:
            last_space_idx = elem_content.rfind(" ")
            if last_space_idx > -1:
                elem_content = elem_content[last_space_idx + 1:]

        list_elems.append(elem_content)
    return ",".join(list_elems)

class SempreQuery:
    def __init__(self, query_id, query, table_file_name, correct_answer):
        self.query_id = query_id
        self.query = query
        self.table_file_name = table_file_name
        self.correct_answer = correct_answer
        self.system_answer = None
        self.system_function_block = None
        self.is_correct = None

    def __str__(self):
        if self.system_answer == None:
            system_answer_str = "None"
        else:
            system_answer_str = self.system_answer

        if self.is_correct:
            is_correct_str = "O"
        else:
            is_correct_str = "X"

        return self.query_id + "\t" + self.query + "\t" + str(self.correct_answer) + "\t" + str(system_answer_str) + "\t" + is_correct_str

    @classmethod
    def from_list(cls, data_list):
        query_id, query, table_file_name, correct_answer = data_list
        return cls(query_id, query, table_file_name, correct_answer)

class TableQA:
    SEMPRE_SESSION_IDS = {}
    def __init__(self, vis_dictionary_file_name, table_base_dir = None):
        self.qparser = cnlplayer.QueryParser()
        self.table_base_dir = table_base_dir
        self.table = None
        self.table_file_name = None
        self.visual_attribute_handler = vahandler.VisualAttributeHandler(vis_dictionary_file_name)

    def change_table_base_dir(self, table_base_dir = None):
        self.table_base_dir = table_base_dir

    def set_table(self, table):
        self.table = dtable.DataTable.from_table(table)

    def set_table_from_file(self, file_name):
        self.table_file_name = file_name
        if self.table_base_dir != None:
            file_name = self.table_base_dir + file_name
        self.table = dtable.DataTable.from_file(file_name)

    def set_spec_handler(self, spec_handler):
        self.visual_attribute_handler.set_spec_handler(spec_handler)
        self.table = self.visual_attribute_handler.spec_handler.runtime_dtable

    def set_spec_handler_from_file(self, dataset_name, spec_file_name, runtime_file_name, base_directory = None):
        self.visual_attribute_handler.set_spec_handler_from_file(dataset_name, spec_file_name, runtime_file_name, base_directory)
        self.table = self.visual_attribute_handler.spec_handler.runtime_dtable
        self.table_file_name = "data/" + dataset_name + "/runtime-data/" + runtime_file_name

    def answer_query(self, query, target_answer, core_system = "Rule", handle_visual = False):
        if self.table == None:
            raise RuntimeError("The context table for the query has not been set")

        if handle_visual:
            if self.visual_attribute_handler.spec_handler == None:
                raise RuntimeError("The spec for the query has not been set")
            meta_answer = self.visual_attribute_handler.attempt_meta_answer(query)
            if meta_answer != None:
                answer, formula = meta_answer
                return query, formula, answer
            input_query = self.visual_attribute_handler.convert_query(query)
        else:
            input_query = query

        if core_system == "Sempre":
            if self.table_file_name == None:
                raise RuntimeError("The table file location has not been specified")
            if self.table_file_name in self.SEMPRE_SESSION_IDS:
                sempre_session_id = self.SEMPRE_SESSION_IDS[self.table_file_name]
            else:
                table_set_response = requests.get("http://localhost:8400/sempre", params = {"q": "(context (graph tables.TableKnowledgeGraph " + self.table_file_name + "/" + "))", "format": "json"})
                sempre_session_id = table_set_response.json()["sessionId"]
            sempre_qa_response = requests.get("http://localhost:8400/sempre", params = {"q": input_query, "format": "json", "sessionId": sempre_session_id})
            answer = sempre_qa_response.json()["answer"]
            parsed_answer = parse_sempre_answer(answer["value"])
            return input_query, answer["formula"], parsed_answer
        else:
            raise RuntimeError("Unhandled core system: " + str(core_system))