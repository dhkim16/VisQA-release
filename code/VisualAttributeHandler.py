import json
import re

import xcolors
import SpecHandler as shandler
import CoreNLPLayer as cnlplayer
import word2vecLayer as w2vlayer

class VisualAttributeHandler:
    def __init__(self, vis_dictionary_file_name):
        self.qparser = cnlplayer.QueryParser()
        with open(vis_dictionary_file_name) as vis_dictionary_file:
            self.vis_dictionary = json.load(vis_dictionary_file)
        self.spec_handler = None
        self.xcolors = xcolors.XColor()

    def set_spec_handler(self, spec_handler):
        self.spec_handler = spec_handler

    def set_spec_handler_from_file(self, dataset_name, spec_file_name, runtime_file_name, base_directory = None):
        self.set_spec_handler(shandler.SpecHandler.from_file(dataset_name, spec_file_name, runtime_file_name, base_directory))

    def attempt_meta_answer(self, query):
        query = query.lower()
        for vis_attr in self.spec_handler.vis2data:
            if self.spec_handler.vis2data[vis_attr].lower() in query:
                return None
            for row in self.spec_handler.runtime_dtable.rows:
                if row.raw_value(self.spec_handler.vis2data[vis_attr]) != None and row.raw_value(self.spec_handler.vis2data[vis_attr]).lower() in query:
                    return None
        if self.spec_handler.color2data["field"] != None:
            for color in self.spec_handler.color2data["mapping"]:
                if self.spec_handler.color2data["mapping"][color].lower() in query:
                    return None
        for word in query.split():
            if word == "most" or word == "more" or word == "less" or word == "least" or word[-3:] == "est" or word[-2:] == "er":
                return None
        if "x axis" in query or "x-axis" in query or "horizontal axis" in query:
            # Question about x-axis
            if "xLocation" in self.spec_handler.vis2data:
                answer = self.spec_handler.vis2data["xLocation"]
            elif "width" in self.spec_handler.vis2data:
                answer = self.spec_handler.vis2data["width"]
            else:
                answer = "x-axis"
            return (answer, "meta[x-axis]")
        if "y axis" in query or "y-axis" in query or "vertical axis" in query:
            # Question about y-axis
            print(self.spec_handler.vis2data)
            if "yLocation" in self.spec_handler.vis2data:
                answer = self.spec_handler.vis2data["yLocation"]
            elif "height" in self.spec_handler.vis2data:
                answer = self.spec_handler.vis2data["height"]
            else:
                answer = "y-axis"
            return (answer, "meta[y-axis]")
        for word in query.split():
            if word in self.xcolors.x_colors:
                # Handle colors
                target_rgb = self.xcolors.get_rgb(word)
                best_sqdist = 2000000
                best_color = None
                for color in self.spec_handler.color2data["mapping"]:
                    test_rgb = xcolors.RGBColor.from_hex(color)
                    sqdist = xcolors.RGBColor.weighted_sqdist(test_rgb, target_rgb)
                    if best_sqdist > sqdist:
                        best_sqdist = sqdist
                        best_color = color
                answer = self.spec_handler.color2data["mapping"][best_color]
                return (answer, "meta[color:" + word + "->" + best_color + "]")
        return None

    def convert_query(self, query):
        if self.spec_handler == None:
            raise RuntimeError("The spec handler for the query has not been set")
        dependency_parse_tree = self.qparser.dependency_parse(query)
        dependency_parse_tree_nodes = dependency_parse_tree.nodes
        vis_list = self.search_visual_mark(dependency_parse_tree_nodes)
        vis_list = self.search_colors_second_pass(dependency_parse_tree_nodes, vis_list)
        converted_data_list = self.map_vis2data(vis_list)
        natural_language_question = self.to_natural_language(dependency_parse_tree_nodes, converted_data_list)
        print(natural_language_question)
        return natural_language_question

    def search_colors_second_pass(self, dependency_parse_tree_nodes, vis_list):
        if self.spec_handler.color2data["field"] == None:
            return vis_list

        for token_idx in range(len(dependency_parse_tree_nodes)):
            if token_idx in vis_list:
                continue
            curr_token = dependency_parse_tree_nodes[token_idx]
            print("PROC_TOK", curr_token)
            if curr_token["lemma"] in self.xcolors.x_colors and len(self.spec_handler.color2data["mapping"]) > 0:
                target_rgb = self.xcolors.get_rgb(curr_token["lemma"])
                best_sqdist = 2000000
                best_color = None
                for color in self.spec_handler.color2data["mapping"]:
                    test_rgb = xcolors.RGBColor.from_hex(color)
                    sqdist = xcolors.RGBColor.weighted_sqdist(test_rgb, target_rgb)
                    if best_sqdist > sqdist:
                        best_sqdist = sqdist
                        best_color = color
                vis_list[token_idx] = ("color", best_color)
        return vis_list

    def search_visual_mark(self, dependency_parse_tree_nodes):
        vis_list = {}
        for token_idx in range(len(dependency_parse_tree_nodes)):
            for mark in self.spec_handler.marks.keys():
                if dependency_parse_tree_nodes[token_idx]["lemma"] in self.vis_dictionary[mark]["mark"]:
                    vis_list[token_idx] = ("mark", None)

                    handled_token_idxs = []
                    token_idxs_to_handle = [token_idx]
                    while len(token_idxs_to_handle) > 0:
                        curr_token_idx = token_idxs_to_handle.pop()
                        curr_token = dependency_parse_tree_nodes[curr_token_idx]
                        best_similarity = -1.0
                        for vis_function in self.vis_dictionary[mark].keys():
                            if vis_function == "mark":
                                continue
                            for vis_attribute in self.vis_dictionary[mark][vis_function].keys():
                                if not vis_attribute in self.spec_handler.vis2data:
                                    continue
                                curr_best_similarity = w2vlayer.get_best_similarity_in(curr_token["lemma"], self.vis_dictionary[mark][vis_function][vis_attribute])
                                if curr_best_similarity > 0.75 and curr_best_similarity > best_similarity:
                                    vis_list[curr_token_idx] = (vis_function, vis_attribute)
                                    best_similarity = curr_best_similarity
                        if curr_token["lemma"] in self.xcolors.x_colors and len(self.spec_handler.color2data["mapping"]) > 0:
                            target_rgb = self.xcolors.get_rgb(curr_token["lemma"])
                            best_sqdist = 2000000
                            best_color = None
                            for color in self.spec_handler.color2data["mapping"]:
                                test_rgb = xcolors.RGBColor.from_hex(color)
                                sqdist = xcolors.RGBColor.weighted_sqdist(test_rgb, target_rgb)
                                if best_sqdist > sqdist:
                                    best_sqdist = sqdist
                                    best_color = color
                            vis_list[curr_token_idx] = ("color", best_color)

                        # Add parent if it meets the criteria
                        if curr_token["rel"] in ["acl", "acl:relcl", "amod", "compound", "conj", "dep", "nmod", "nmod:of", "nmod:poss", "nsubj", "dobj"]:
                            parent_token_idx = curr_token["head"]
                            if not parent_token_idx in handled_token_idxs:
                                token_idxs_to_handle.append(parent_token_idx)

                        # Add children meeting the criteria
                        for hit_relation in ["acl", "acl:relcl", "amod", "compound", "conj", "dep", "nmod", "nmod:of", "nmod:poss", "nsubj", "dobj"]:
                            if hit_relation in curr_token["deps"]:
                                for hit_child_idx in curr_token["deps"][hit_relation]:
                                    if not hit_child_idx in handled_token_idxs:
                                        token_idxs_to_handle.append(hit_child_idx)



                        handled_token_idxs.append(curr_token_idx)

        return vis_list

    def map_vis2data(self, vis_list):
        converted_data_list = {}
        for token_idx in vis_list:
            vis_token_vis_info = vis_list[token_idx]
            if vis_token_vis_info[0] == "mark":
                converted_data_list[token_idx] = vis_token_vis_info
                continue
            elif vis_token_vis_info[0] == "color":
                converted_data_list[token_idx] = ("filter", self.spec_handler.color2data["mapping"][vis_token_vis_info[1]])
                continue    
            converted_data_list[token_idx] = (vis_token_vis_info[0], self.spec_handler.vis2data[vis_token_vis_info[1]])
        return converted_data_list

    def to_natural_language(self, dependency_parse_tree_nodes, converted_data_list):
        word_list = []
        for token_idx in range(1, len(dependency_parse_tree_nodes)):
            if token_idx in converted_data_list:
                vis_token_converted_info = converted_data_list[token_idx]
                if vis_token_converted_info[0] == "mark":
                    word_list.append("data")
                elif vis_token_converted_info[0] == "filter":
                    word_list.append(vis_token_converted_info[1])
                elif vis_token_converted_info[0] == "minimum":
                    word_list.append("least" + " " + vis_token_converted_info[1])
                elif vis_token_converted_info[0] == "maximum":
                    word_list.append("most" + " " + vis_token_converted_info[1])
                elif vis_token_converted_info[0] == "comparison_more":
                    word_list.append("more" + " " + vis_token_converted_info[1])
                elif vis_token_converted_info[0] == "comparison_less":
                    word_list.append("less" + " " + vis_token_converted_info[1])
                else:
                    word_list.append(vis_token_converted_info[1] + " " + vis_token_converted_info[0])
            else:
                word_list.append(dependency_parse_tree_nodes[token_idx]["word"])
        return " ".join(word_list)


